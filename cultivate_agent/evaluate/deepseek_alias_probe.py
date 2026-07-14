"""Bounded, resumable DeepSeek capability probe for ontology alias mapping."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

import yaml


PROMPT_VERSION = "alias-map-pointer-v2-recall"
RELATIONS = {"alias", "ambiguous", "distinct", "unknown"}


@dataclass(frozen=True)
class AliasGold:
    alias_id: str
    surface: str
    canonical: str
    category: str


@dataclass(frozen=True)
class AliasProbeResult:
    aliases: int
    requests_expected: int
    requests_valid: int
    repeat_recalls: tuple[float, ...]
    canonical_consistency: float
    total_tokens: int
    issues: tuple[str, ...]
    mismatches: tuple[str, ...]

    @property
    def gate_pass(self) -> bool:
        return (
            not self.issues
            and self.requests_valid == self.requests_expected
            and bool(self.repeat_recalls)
            and min(self.repeat_recalls) >= 0.95
            and self.canonical_consistency >= 0.95
        )


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_alias_gold(ontology_dir: Path, *, max_aliases: Optional[int] = None) -> list[AliasGold]:
    """Build deterministic, category-balanced gold from unique ontology aliases."""
    grouped: dict[str, list[tuple[str, str]]] = {}
    surface_targets: dict[str, set[str]] = {}
    raw_rows: list[tuple[str, str, str]] = []
    for path in sorted(ontology_dir.glob("*.yaml")):
        category = path.stem
        entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for entry in entries:
            canonical = str(entry.get("canonical") or "").strip()
            for alias in entry.get("aliases") or []:
                surface = str(alias).strip()
                if not canonical or not surface or surface.casefold() == canonical.casefold():
                    continue
                raw_rows.append((category, canonical, surface))
                surface_targets.setdefault(surface.casefold(), set()).add(canonical)
    for category, canonical, surface in raw_rows:
        if len(surface_targets[surface.casefold()]) == 1:
            grouped.setdefault(category, []).append((canonical, surface))
    for rows in grouped.values():
        rows.sort(key=lambda row: (row[0].casefold(), row[1].casefold()))

    selected: list[tuple[str, str, str]] = []
    categories = sorted(grouped)
    index = 0
    while categories and (max_aliases is None or len(selected) < max_aliases):
        remaining = []
        for category in categories:
            rows = grouped[category]
            if index < len(rows):
                canonical, surface = rows[index]
                selected.append((category, canonical, surface))
                if max_aliases is not None and len(selected) >= max_aliases:
                    break
            if index + 1 < len(rows):
                remaining.append(category)
        categories = remaining
        index += 1
    return [
        AliasGold(f"A{number:03d}", surface, canonical, category)
        for number, (category, canonical, surface) in enumerate(selected, start=1)
    ]


def build_prompt(batch: Sequence[AliasGold], allowed_canonicals: Sequence[str]) -> str:
    input_payload = {
        "allowed_canonicals": list(allowed_canonicals),
        "surface_forms": [
            {"id": item.alias_id, "surface": item.surface} for item in batch
        ],
    }
    return (
        "Map each supplied culture-medium surface form to one allowed canonical name. "
        "This is candidate mapping, not a scientific decision. Return JSON only with the "
        "shape {\"mappings\":[{\"id\":str,\"canonical\":str,\"relation\":str}]}. "
        "Use each input id exactly once and no other keys. canonical must be one literal "
        "allowed name or UNKNOWN. relation must be alias, ambiguous, distinct, or unknown. "
        "This is a high-recall candidate-generation task: when an abbreviation, spelling "
        "variant, formulation-family name, or base/full formulation relationship makes one "
        "canonical plausible, return that candidate for later review. Use UNKNOWN only when "
        "no allowed canonical is plausibly related. Precision is checked downstream. "
        "Do not invent aliases, explanations, confidence scores, or numeric values.\nINPUT_JSON:\n"
        + json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
    )


def validate_mapping_response(
    response_text: str,
    batch: Sequence[AliasGold],
    allowed_canonicals: set[str],
) -> tuple[dict[str, str], list[str]]:
    issues: list[str] = []
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return {}, [f"invalid JSON: {exc}"]
    if set(payload) != {"mappings"} or not isinstance(payload.get("mappings"), list):
        return {}, ["response must contain only a mappings list"]
    expected_ids = {item.alias_id for item in batch}
    mappings: dict[str, str] = {}
    for index, row in enumerate(payload["mappings"]):
        if not isinstance(row, dict) or set(row) != {"id", "canonical", "relation"}:
            issues.append(f"mapping {index} has invalid keys")
            continue
        alias_id = row["id"]
        canonical = row["canonical"]
        relation = row["relation"]
        if alias_id not in expected_ids:
            issues.append(f"unexpected alias id {alias_id!r}")
            continue
        if alias_id in mappings:
            issues.append(f"duplicate alias id {alias_id}")
            continue
        if canonical != "UNKNOWN" and canonical not in allowed_canonicals:
            issues.append(f"{alias_id}: canonical is outside allowed vocabulary")
            continue
        if relation not in RELATIONS:
            issues.append(f"{alias_id}: invalid relation {relation!r}")
            continue
        mappings[alias_id] = canonical
    missing = expected_ids - set(mappings)
    if missing:
        issues.append(f"missing {len(missing)} alias id(s)")
    return mappings, issues


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def run_alias_probe(
    gold: Sequence[AliasGold],
    *,
    checkpoint_dir: Path,
    model: str,
    repeats: int,
    batch_size: int,
    max_requests: int,
    max_total_tokens: int,
    max_output_tokens: int,
    caller: Callable[[str, int], tuple[str, dict[str, int]]],
) -> AliasProbeResult:
    """Run or resume a bounded probe; caller receives prompt and max output tokens."""
    if not gold:
        raise ValueError("alias gold is empty")
    if repeats <= 0 or batch_size <= 0:
        raise ValueError("repeats and batch_size must be positive")
    batches = [list(gold[index:index + batch_size]) for index in range(0, len(gold), batch_size)]
    expected_requests = repeats * len(batches)
    if expected_requests > max_requests:
        raise ValueError(
            f"probe requires {expected_requests} requests, above hard cap {max_requests}"
        )
    if expected_requests * max_output_tokens > max_total_tokens:
        raise ValueError("maximum possible completion tokens exceed hard total-token cap")
    allowed = sorted({item.canonical for item in gold})
    input_hash = _sha256_json({
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "gold": [item.__dict__ for item in gold],
        "allowed": allowed,
        "repeats": repeats,
        "batch_size": batch_size,
    })

    all_outputs: dict[int, dict[str, str]] = {repeat: {} for repeat in range(repeats)}
    issues: list[str] = []
    valid_requests = 0
    total_tokens = 0
    for repeat in range(repeats):
        for batch_index, batch in enumerate(batches):
            checkpoint = checkpoint_dir / f"{input_hash[:12]}_r{repeat + 1}_b{batch_index + 1}.json"
            prompt = build_prompt(batch, allowed)
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text(encoding="utf-8"))
                if record.get("input_hash") != input_hash:
                    raise ValueError(f"checkpoint input hash mismatch: {checkpoint}")
            else:
                response_text, usage = caller(prompt, max_output_tokens)
                record = {
                    "format_version": 1,
                    "prompt_version": PROMPT_VERSION,
                    "model": model,
                    "temperature": 0,
                    "thinking": "disabled",
                    "input_hash": input_hash,
                    "repeat": repeat + 1,
                    "batch": batch_index + 1,
                    "alias_ids": [item.alias_id for item in batch],
                    "response_text": response_text,
                    "usage": usage,
                }
                _atomic_json(checkpoint, record)
            usage = record.get("usage") or {}
            total_tokens += int(usage.get("total_tokens") or 0)
            if total_tokens > max_total_tokens:
                raise RuntimeError("hard total-token cap exceeded; probe stopped at checkpoint")
            mappings, response_issues = validate_mapping_response(
                str(record.get("response_text") or ""), batch, set(allowed)
            )
            if response_issues:
                issues.extend(
                    f"repeat {repeat + 1} batch {batch_index + 1}: {issue}"
                    for issue in response_issues
                )
            else:
                valid_requests += 1
                all_outputs[repeat].update(mappings)

    expected = {item.alias_id: item.canonical for item in gold}
    recalls = tuple(
        round(
            sum(outputs.get(alias_id) == canonical for alias_id, canonical in expected.items())
            / len(expected),
            4,
        )
        for outputs in all_outputs.values()
    )
    stable = sum(
        len({all_outputs[repeat].get(alias_id) for repeat in range(repeats)}) == 1
        for alias_id in expected
    ) / len(expected)
    by_id = {item.alias_id: item for item in gold}
    mismatches = []
    for alias_id, canonical in expected.items():
        predictions = tuple(all_outputs[repeat].get(alias_id, "MISSING") for repeat in range(repeats))
        if any(prediction != canonical for prediction in predictions):
            item = by_id[alias_id]
            mismatches.append(
                f"{alias_id} {item.surface!r}: expected {canonical!r}; repeats={predictions!r}"
            )
    return AliasProbeResult(
        aliases=len(gold),
        requests_expected=expected_requests,
        requests_valid=valid_requests,
        repeat_recalls=recalls,
        canonical_consistency=round(stable, 4),
        total_tokens=total_tokens,
        issues=tuple(issues),
        mismatches=tuple(mismatches),
    )


def report_markdown(result: AliasProbeResult, *, model: str, max_requests: int) -> str:
    status = "PASS_FOR_SHADOW_ALIAS_MAPPING" if result.gate_pass else "FAIL"
    lines = [
        "# DeepSeek Alias-Mapping Capability Probe",
        "",
        f"**Status: {status}**",
        "",
        f"- Model: `{model}` (non-thinking, temperature 0)",
        f"- Prompt/schema version: `{PROMPT_VERSION}`",
        f"- Ontology-derived alias gold: {result.aliases}",
        f"- Valid requests: {result.requests_valid}/{result.requests_expected}",
        f"- Hard request cap: {max_requests}",
        f"- Recall by repeat: {', '.join(f'{value:.3f}' for value in result.repeat_recalls)}",
        f"- Canonical run-to-run consistency: {result.canonical_consistency:.3f}",
        f"- Total API tokens reported: {result.total_tokens}",
        f"- Validation issues: {len(result.issues)}",
        "",
        "Passing authorizes only shadow alias-candidate mapping. Codex/Claude must still "
        "review every proposed ontology change; this report is not biological evidence.",
        "",
        "Official configuration references: [DeepSeek V4 models](https://api-docs.deepseek.com/quick_start/pricing), "
        "[thinking-mode toggle](https://api-docs.deepseek.com/guides/thinking_mode), and "
        "[JSON output](https://api-docs.deepseek.com/api/create-chat-completion).",
    ]
    if result.mismatches:
        lines.extend(["", "## Stable Or Intermittent Mismatches", ""])
        lines.extend(f"- `{mismatch}`" for mismatch in result.mismatches)
    if result.issues:
        lines.extend(["", "## Issues", ""] + [f"- {issue}" for issue in result.issues])
    return "\n".join(lines) + "\n"
