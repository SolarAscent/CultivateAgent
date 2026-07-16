"""Bounded DeepSeek probe for high-recall quantitative block localization."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse

from .quantitative_review import _sha256, _signals


PROMPT_VERSION = "quant-block-candidate-pointer-v1"
SILVER_RECORDS = {"R017", "R047"}
STAT_SIGNALS = {"explicit_dispersion", "named_dispersion_value", "sample_size", "sd", "sem"}
SHADOW_CONTEXT_SIGNALS = {"outcome", "medium", "figure_caption", "error_policy"}
SHADOW_SELECTOR_VERSION = "stat-context-block-v2"
DECOY_EXCLUDED_SIGNALS = STAT_SIGNALS | {
    "outcome", "medium", "figure_caption", "mean", "error_policy"
}


def deepseek_caller(model: str, timeout: int):
    """Create the shared fail-fast DeepSeek caller used by probe and shadow CLIs."""
    from openai import OpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY or OPENAI_API_KEY is required")
    if urlparse(base_url or "").hostname != "api.deepseek.com":
        raise RuntimeError("DeepSeek run requires base URL https://api.deepseek.com")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def call(prompt: str, max_output_tokens: int):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return strict JSON containing candidate IDs only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=max_output_tokens,
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
        )
        usage = response.usage
        return response.choices[0].message.content or "", {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }

    return call


@dataclass(frozen=True)
class LocatorItem:
    item_id: str
    snippet: str
    positive: bool
    record_id: str
    pdf_page: int
    block_index: int
    block_text_sha256: str


@dataclass(frozen=True)
class LocatorProbeResult:
    items: int
    positives: int
    requests_expected: int
    requests_valid: int
    repeat_recalls: tuple[float, ...]
    repeat_precisions: tuple[float, ...]
    selection_consistency: float
    total_tokens: int
    issues: tuple[str, ...]
    false_negative_ids: tuple[str, ...]
    false_positive_ids: tuple[str, ...]

    @property
    def gate_pass(self) -> bool:
        return (
            not self.issues
            and self.requests_valid == self.requests_expected
            and bool(self.repeat_recalls)
            and min(self.repeat_recalls) >= 0.95
            and self.selection_consistency >= 0.95
        )


@dataclass(frozen=True)
class ShadowLocalizationResult:
    items: tuple[LocatorItem, ...]
    selected_ids: tuple[str, ...]
    repeats: int
    requests_expected: int
    requests_valid: int
    selection_consistency: float
    total_tokens: int
    issues: tuple[str, ...]

    @property
    def gate_pass(self) -> bool:
        return (
            not self.issues
            and self.requests_valid == self.requests_expected
            and self.selection_consistency >= 0.95
        )


@dataclass(frozen=True)
class HeldOutLocatorEvaluation:
    silver_total: int
    prefilter_covered: int
    selected: int
    recall: float
    missed_ids: tuple[str, ...]

    @property
    def gate_pass(self) -> bool:
        return (
            self.silver_total > 0
            and self.prefilter_covered == self.silver_total
            and self.recall >= 0.95
        )


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_block(block: Sequence[object]) -> str:
    return " ".join(str(block[4]).split())


def load_locator_silver(
    manifest_path: Path,
    *,
    repo_root: Path,
    negatives_per_positive: int = 2,
    snippet_chars: int = 700,
    fitz_module=None,
) -> list[LocatorItem]:
    """Load hash-verified positives and deterministic unambiguous decoys."""
    if negatives_per_positive < 1 or snippet_chars < 100:
        raise ValueError("negatives_per_positive and snippet_chars are too small")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = [
        row for row in manifest.get("candidates", []) if row.get("record_id") in SILVER_RECORDS
    ]
    sources = {
        row["record_id"]: row
        for row in manifest.get("sources", [])
        if row.get("record_id") in SILVER_RECORDS
    }
    expected = {"R017": 4, "R047": 4}
    counts = {record_id: 0 for record_id in expected}
    for row in candidates:
        counts[str(row["record_id"])] += 1
    if counts != expected or set(sources) != SILVER_RECORDS:
        raise ValueError("silver manifest must contain four R017 and four R047 locators")

    raw_items: list[tuple[str, str, bool, int, int, str]] = []
    documents = {}
    try:
        for record_id, source in sources.items():
            path = repo_root / source["pdf_path"]
            if not path.is_file() or _sha256(path.read_bytes()) != source["pdf_sha256"]:
                raise ValueError(f"{record_id}: PDF missing or hash mismatch")
            documents[record_id] = fitz_module.open(path)

        positive_locations = {
            (str(row["record_id"]), int(row["pdf_page"]), int(row["block_index"]))
            for row in candidates
        }
        for row in candidates:
            record_id = str(row["record_id"])
            page_number = int(row["pdf_page"])
            block_index = int(row["block_index"])
            blocks = documents[record_id][page_number - 1].get_text("blocks", sort=True)
            if block_index >= len(blocks):
                raise ValueError(f"{row['candidate_id']}: block index no longer exists")
            text = _normalize_block(blocks[block_index])
            block_hash = _sha256(text.encode("utf-8"))
            if block_hash != row["block_text_sha256"]:
                raise ValueError(f"{row['candidate_id']}: block text hash mismatch")
            raw_items.append((record_id, text, True, page_number, block_index, block_hash))

        decoy_pool: dict[str, list[tuple[str, int, int, str]]] = {record_id: [] for record_id in sources}
        for record_id, document in documents.items():
            for page_index, page in enumerate(document):
                for block_index, block in enumerate(page.get_text("blocks", sort=True)):
                    location = (record_id, page_index + 1, block_index)
                    if location in positive_locations:
                        continue
                    text = _normalize_block(block)
                    if len(text) < 120 or set(_signals(text)) & DECOY_EXCLUDED_SIGNALS:
                        continue
                    block_hash = _sha256(text.encode("utf-8"))
                    decoy_pool[record_id].append((text, page_index + 1, block_index, block_hash))
            decoy_pool[record_id].sort(key=lambda row: row[3])

        for record_id, positive_count in expected.items():
            needed = positive_count * negatives_per_positive
            if len(decoy_pool[record_id]) < needed:
                raise ValueError(f"{record_id}: only {len(decoy_pool[record_id])} eligible decoys")
            for text, page_number, block_index, block_hash in decoy_pool[record_id][:needed]:
                raw_items.append((record_id, text, False, page_number, block_index, block_hash))
    finally:
        for document in documents.values():
            document.close()

    raw_items.sort(key=lambda row: hashlib.sha256(f"{row[0]}:{row[5]}".encode()).hexdigest())
    return [
        LocatorItem(
            item_id=f"L{index:03d}",
            snippet=text[:snippet_chars],
            positive=positive,
            record_id=record_id,
            pdf_page=page_number,
            block_index=block_index,
            block_text_sha256=block_hash,
        )
        for index, (record_id, text, positive, page_number, block_index, block_hash)
        in enumerate(raw_items, start=1)
    ]


def load_shadow_pool(
    manifest_path: Path,
    *,
    repo_root: Path,
    record_ids: Sequence[str],
    snippet_chars: int = 700,
    fitz_module=None,
) -> list[LocatorItem]:
    """Build a broad, hash-bound statistical block pool for shadow localization."""
    if not record_ids or snippet_chars < 100:
        raise ValueError("record_ids is empty or snippet_chars is too small")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    requested = set(record_ids)
    sources = {
        row["record_id"]: row for row in manifest.get("sources", [])
        if row.get("record_id") in requested
    }
    if set(sources) != requested:
        raise ValueError("one or more shadow records are absent from the source manifest")
    raw_items = []
    for record_id in sorted(requested):
        source = sources[record_id]
        path = repo_root / source["pdf_path"]
        if not path.is_file() or _sha256(path.read_bytes()) != source["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        document = fitz_module.open(path)
        try:
            for page_index, page in enumerate(document):
                for block_index, block in enumerate(page.get_text("blocks", sort=True)):
                    text = _normalize_block(block)
                    signals = set(_signals(text))
                    if (
                        len(text) < 80
                        or not signals & STAT_SIGNALS
                        or not signals & SHADOW_CONTEXT_SIGNALS
                    ):
                        continue
                    raw_items.append((record_id, text, page_index + 1, block_index,
                                      _sha256(text.encode("utf-8"))))
        finally:
            document.close()
    raw_items.sort(key=lambda row: (row[0], row[2], row[3]))
    return [
        LocatorItem(
            item_id=f"S{index:03d}", snippet=text[:snippet_chars], positive=False,
            record_id=record_id, pdf_page=page_number, block_index=block_index,
            block_text_sha256=block_hash,
        )
        for index, (record_id, text, page_number, block_index, block_hash)
        in enumerate(raw_items, start=1)
    ]


def build_prompt(batch: Sequence[LocatorItem]) -> str:
    payload = {"blocks": [{"id": item.item_id, "text": item.snippet} for item in batch]}
    return (
        "Select every text block that plausibly contains quantitative outcome evidence or "
        "statistical support for a cell-culture medium, donor, or intervention comparison. "
        "Include figure captions and methods/statistical statements that provide means, "
        "SD/SEM, sample size, error-bar policy, or explicit group comparisons. Optimize for "
        "recall; later deterministic and expert review will remove false positives. Return "
        "JSON only with exactly {\"candidate_ids\":[str]}. IDs must come from the input and "
        "must not repeat. Return no excerpts, numbers, explanations, confidence, or other keys.\n"
        "INPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


def validate_candidate_response(
    response_text: str, batch: Sequence[LocatorItem]
) -> tuple[set[str], list[str]]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return set(), [f"invalid JSON: {exc}"]
    if not isinstance(payload, dict) or set(payload) != {"candidate_ids"}:
        return set(), ["response must contain only candidate_ids"]
    values = payload["candidate_ids"]
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        return set(), ["candidate_ids must be a string list"]
    if len(values) != len(set(values)):
        return set(), ["candidate_ids contains duplicates"]
    allowed = {item.item_id for item in batch}
    unexpected = set(values) - allowed
    if unexpected:
        return set(), [f"unexpected candidate id(s): {sorted(unexpected)!r}"]
    return set(values), []


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def run_locator_probe(
    items: Sequence[LocatorItem],
    *,
    checkpoint_dir: Path,
    model: str,
    repeats: int,
    batch_size: int,
    max_requests: int,
    max_total_tokens: int,
    max_output_tokens: int,
    caller: Callable[[str, int], tuple[str, dict[str, int]]],
    prompt_builder: Callable[[Sequence[LocatorItem]], str] = build_prompt,
    prompt_version: str = PROMPT_VERSION,
    max_wall_seconds: float = 600,
) -> LocatorProbeResult:
    if not items or not any(item.positive for item in items):
        raise ValueError("locator silver is empty or has no positives")
    if repeats <= 0 or batch_size <= 0 or max_wall_seconds <= 0:
        raise ValueError("repeats, batch_size, and max_wall_seconds must be positive")
    batches = [list(items[index:index + batch_size]) for index in range(0, len(items), batch_size)]
    expected_requests = repeats * len(batches)
    if expected_requests > max_requests:
        raise ValueError(f"probe requires {expected_requests} requests, above hard cap {max_requests}")
    if expected_requests * max_output_tokens > max_total_tokens:
        raise ValueError("maximum possible completion tokens exceed hard total-token cap")
    input_hash = _sha256_json({
        "prompt_version": prompt_version,
        "model": model,
        "items": [
            {"id": item.item_id, "snippet_sha256": _sha256(item.snippet.encode()),
             "positive": item.positive, "block_sha256": item.block_text_sha256}
            for item in items
        ],
        "repeats": repeats,
        "batch_size": batch_size,
    })

    outputs: dict[int, set[str]] = {repeat: set() for repeat in range(repeats)}
    issues: list[str] = []
    valid_requests = 0
    total_tokens = 0
    started = time.monotonic()
    for repeat in range(repeats):
        for batch_index, batch in enumerate(batches):
            if time.monotonic() - started > max_wall_seconds:
                raise RuntimeError("hard wall-time cap exceeded; probe stopped before next request")
            checkpoint = checkpoint_dir / f"{input_hash[:12]}_r{repeat + 1}_b{batch_index + 1}.json"
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text(encoding="utf-8"))
                if record.get("input_hash") != input_hash:
                    raise ValueError(f"checkpoint input hash mismatch: {checkpoint}")
            else:
                response_text, usage = caller(prompt_builder(batch), max_output_tokens)
                record = {
                    "format_version": 1, "prompt_version": prompt_version, "model": model,
                    "temperature": 0, "thinking": "disabled", "input_hash": input_hash,
                    "repeat": repeat + 1, "batch": batch_index + 1,
                    "item_ids": [item.item_id for item in batch],
                    "response_text": response_text, "usage": usage,
                }
                _atomic_json(checkpoint, record)
            if time.monotonic() - started > max_wall_seconds:
                raise RuntimeError("hard wall-time cap exceeded; probe stopped at checkpoint")
            total_tokens += int((record.get("usage") or {}).get("total_tokens") or 0)
            if total_tokens > max_total_tokens:
                raise RuntimeError("hard total-token cap exceeded; probe stopped at checkpoint")
            selected, response_issues = validate_candidate_response(
                str(record.get("response_text") or ""), batch
            )
            if response_issues:
                issues.extend(
                    f"repeat {repeat + 1} batch {batch_index + 1}: {issue}"
                    for issue in response_issues
                )
            else:
                valid_requests += 1
                outputs[repeat].update(selected)

    positive_ids = {item.item_id for item in items if item.positive}
    negative_ids = {item.item_id for item in items if not item.positive}
    recalls = []
    precisions = []
    for selected in outputs.values():
        true_positives = len(selected & positive_ids)
        recalls.append(round(true_positives / len(positive_ids), 4))
        precisions.append(round(true_positives / len(selected), 4) if selected else 0.0)
    consistency = sum(
        len({item.item_id in outputs[repeat] for repeat in range(repeats)}) == 1
        for item in items
    ) / len(items)
    false_negatives = sorted(
        item_id for item_id in positive_ids
        if any(item_id not in outputs[repeat] for repeat in range(repeats))
    )
    false_positives = sorted(
        item_id for item_id in negative_ids
        if any(item_id in outputs[repeat] for repeat in range(repeats))
    )
    return LocatorProbeResult(
        items=len(items), positives=len(positive_ids), requests_expected=expected_requests,
        requests_valid=valid_requests, repeat_recalls=tuple(recalls),
        repeat_precisions=tuple(precisions), selection_consistency=round(consistency, 4),
        total_tokens=total_tokens, issues=tuple(issues),
        false_negative_ids=tuple(false_negatives), false_positive_ids=tuple(false_positives),
    )


def run_shadow_localization(
    items: Sequence[LocatorItem],
    *,
    checkpoint_dir: Path,
    model: str,
    repeats: int,
    batch_size: int,
    max_requests: int,
    max_total_tokens: int,
    max_output_tokens: int,
    caller: Callable[[str, int], tuple[str, dict[str, int]]],
) -> ShadowLocalizationResult:
    """Run repeated unlabeled localization and retain only unanimous pointers."""
    if not items or repeats < 2 or batch_size <= 0:
        raise ValueError("shadow items are empty or repeat/batch settings are invalid")
    batches = [list(items[index:index + batch_size]) for index in range(0, len(items), batch_size)]
    expected_requests = repeats * len(batches)
    if expected_requests > max_requests:
        raise ValueError(f"shadow run requires {expected_requests} requests, above cap {max_requests}")
    if expected_requests * max_output_tokens > max_total_tokens:
        raise ValueError("maximum possible completion tokens exceed hard total-token cap")
    input_hash = _sha256_json({
        "prompt_version": PROMPT_VERSION, "mode": "shadow", "model": model,
        "items": [{"id": item.item_id, "snippet_sha256": _sha256(item.snippet.encode()),
                   "block_sha256": item.block_text_sha256} for item in items],
        "repeats": repeats, "batch_size": batch_size,
    })
    outputs: dict[int, set[str]] = {repeat: set() for repeat in range(repeats)}
    issues: list[str] = []
    valid_requests = 0
    total_tokens = 0
    for repeat in range(repeats):
        for batch_index, batch in enumerate(batches):
            checkpoint = checkpoint_dir / f"{input_hash[:12]}_r{repeat + 1}_b{batch_index + 1}.json"
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text(encoding="utf-8"))
                if record.get("input_hash") != input_hash:
                    raise ValueError(f"checkpoint input hash mismatch: {checkpoint}")
            else:
                response_text, usage = caller(build_prompt(batch), max_output_tokens)
                record = {
                    "format_version": 1, "prompt_version": PROMPT_VERSION, "mode": "shadow",
                    "model": model, "temperature": 0, "thinking": "disabled",
                    "input_hash": input_hash, "repeat": repeat + 1, "batch": batch_index + 1,
                    "item_ids": [item.item_id for item in batch],
                    "response_text": response_text, "usage": usage,
                }
                _atomic_json(checkpoint, record)
            total_tokens += int((record.get("usage") or {}).get("total_tokens") or 0)
            if total_tokens > max_total_tokens:
                raise RuntimeError("hard total-token cap exceeded; shadow run stopped at checkpoint")
            selected, response_issues = validate_candidate_response(
                str(record.get("response_text") or ""), batch
            )
            if response_issues:
                issues.extend(
                    f"repeat {repeat + 1} batch {batch_index + 1}: {issue}"
                    for issue in response_issues
                )
            else:
                valid_requests += 1
                outputs[repeat].update(selected)
    consistency = sum(
        len({item.item_id in outputs[repeat] for repeat in range(repeats)}) == 1
        for item in items
    ) / len(items)
    unanimous = set.intersection(*(outputs[repeat] for repeat in range(repeats)))
    return ShadowLocalizationResult(
        items=tuple(items), selected_ids=tuple(sorted(unanimous)), repeats=repeats,
        requests_expected=expected_requests, requests_valid=valid_requests,
        selection_consistency=round(consistency, 4), total_tokens=total_tokens,
        issues=tuple(issues),
    )


def evaluate_shadow_against_gold(
    result: ShadowLocalizationResult, gold_manifest_path: Path
) -> HeldOutLocatorEvaluation:
    """Measure held-out recall without exposing labels to the model prompt."""
    records = {item.record_id for item in result.items}
    payload = json.loads(gold_manifest_path.read_text(encoding="utf-8"))
    silver = {
        (
            str(row["record_id"]), int(row["pdf_page"]), int(row["block_index"]),
            str(row["block_text_sha256"]),
        ): str(row["candidate_id"])
        for row in payload.get("candidates", [])
        if row.get("record_id") in records
    }
    if not silver:
        raise ValueError("held-out manifest has no locators for shadow records")
    pool = {
        (item.record_id, item.pdf_page, item.block_index, item.block_text_sha256): item.item_id
        for item in result.items
    }
    selected_ids = set(result.selected_ids)
    covered = set(silver) & set(pool)
    selected = {locator for locator in covered if pool[locator] in selected_ids}
    missed = tuple(sorted(silver[locator] for locator in set(silver) - selected))
    return HeldOutLocatorEvaluation(
        silver_total=len(silver), prefilter_covered=len(covered), selected=len(selected),
        recall=round(len(selected) / len(silver), 4), missed_ids=missed,
    )


def shadow_manifest(
    result: ShadowLocalizationResult,
    *,
    model: str,
    held_out: HeldOutLocatorEvaluation | None = None,
) -> dict[str, object]:
    deployment_pass = result.gate_pass and (held_out is None or held_out.gate_pass)
    selected = set(result.selected_ids) if deployment_pass else set()
    if not result.gate_pass:
        status = "failed_unstable_no_output"
    elif held_out is not None and not held_out.gate_pass:
        status = "failed_held_out_recall_no_output"
    else:
        status = "candidate_pointers_for_expert_review"
    return {
        "format_version": 1,
        "status": status,
        "deployment_gate_pass": deployment_pass,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "selector_version": SHADOW_SELECTOR_VERSION,
        "repeats": result.repeats,
        "selection_consistency": result.selection_consistency,
        "total_tokens": result.total_tokens,
        "input_items": len(result.items),
        "model_selected_items": len(result.selected_ids),
        "selected_items": len(selected),
        "held_out_evaluation": None if held_out is None else {
            "silver_total": held_out.silver_total,
            "prefilter_covered": held_out.prefilter_covered,
            "selected": held_out.selected,
            "recall": held_out.recall,
            "missed_ids": list(held_out.missed_ids),
            "gate_pass": held_out.gate_pass,
        },
        "candidates": [
            {
                "candidate_id": item.item_id, "record_id": item.record_id,
                "pdf_page": item.pdf_page, "block_index": item.block_index,
                "block_text_sha256": item.block_text_sha256,
            }
            for item in result.items if item.item_id in selected
        ],
        "limitations": [
            "DeepSeek selected candidate pointers only; no numeric values were emitted.",
            "Candidates are not biological evidence and cannot establish an evidence tier.",
            "Every retained pointer requires deterministic source revalidation and expert review.",
        ],
    }


def validate_shadow_manifest(payload: dict[str, object], items: Sequence[LocatorItem]) -> list[str]:
    """Deterministically validate that a shadow artifact contains pointers only."""
    issues: list[str] = []
    allowed_top = {
        "format_version", "status", "model", "prompt_version", "repeats",
        "selector_version",
        "selection_consistency", "total_tokens", "input_items", "model_selected_items",
        "selected_items", "deployment_gate_pass", "held_out_evaluation", "candidates",
        "limitations",
    }
    if set(payload) != allowed_top:
        issues.append("shadow manifest top-level schema mismatch")
    if payload.get("selector_version") != SHADOW_SELECTOR_VERSION:
        issues.append("shadow selector version mismatch")
    expected = {item.item_id: item for item in items}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return issues + ["shadow candidates must be a list"]
    seen = set()
    allowed_candidate = {
        "candidate_id", "record_id", "pdf_page", "block_index", "block_text_sha256"
    }
    for index, row in enumerate(candidates):
        if not isinstance(row, dict) or set(row) != allowed_candidate:
            issues.append(f"candidate {index} schema mismatch")
            continue
        item = expected.get(row.get("candidate_id"))
        if item is None:
            issues.append(f"candidate {index} has unknown id")
            continue
        if item.item_id in seen:
            issues.append(f"duplicate candidate {item.item_id}")
        seen.add(item.item_id)
        reference = {
            "candidate_id": item.item_id, "record_id": item.record_id,
            "pdf_page": item.pdf_page, "block_index": item.block_index,
            "block_text_sha256": item.block_text_sha256,
        }
        if row != reference:
            issues.append(f"candidate {item.item_id} pointer metadata mismatch")
    if payload.get("input_items") != len(items) or payload.get("selected_items") != len(candidates):
        issues.append("shadow manifest counts mismatch")
    held_out = payload.get("held_out_evaluation")
    held_out_keys = {
        "silver_total", "prefilter_covered", "selected", "recall", "missed_ids", "gate_pass"
    }
    if held_out is not None and (not isinstance(held_out, dict) or set(held_out) != held_out_keys):
        issues.append("held-out evaluation schema mismatch")
    if payload.get("deployment_gate_pass") is False and candidates:
        issues.append("failed deployment gate must suppress all candidate output")
    return issues


def report_markdown(
    result: LocatorProbeResult,
    *,
    model: str,
    max_requests: int,
    title: str = "DeepSeek Quantitative-Block Localization Probe",
    prompt_version: str = PROMPT_VERSION,
    precision_label: str = "Precision by repeat (reported, not gated)",
) -> str:
    status = "PASS_FOR_BOUNDED_SHADOW_LOCALIZATION" if result.gate_pass else "FAIL"
    lines = [
        f"# {title}", "", f"**Status: {status}**", "",
        f"- Model: `{model}` (non-thinking, temperature 0)",
        f"- Prompt/schema version: `{prompt_version}`",
        f"- Hash-verified silver items: {result.items} ({result.positives} positives)",
        f"- Valid requests: {result.requests_valid}/{result.requests_expected}",
        f"- Hard request cap: {max_requests}",
        f"- Recall by repeat: {', '.join(f'{value:.3f}' for value in result.repeat_recalls)}",
        f"- {precision_label}: "
        + ", ".join(f"{value:.3f}" for value in result.repeat_precisions),
        f"- Run-to-run selection consistency: {result.selection_consistency:.3f}",
        f"- Total API tokens reported: {result.total_tokens}",
        f"- Validation issues: {len(result.issues)}", "",
        "Passing authorizes only bounded shadow candidate localization. Silver positives are "
        "frozen deterministic locators, not adjudicated biological evidence; DeepSeek outputs "
        "cannot create evidence tiers or transcribe numeric values.",
    ]
    if result.false_negative_ids:
        lines.extend(["", "## False-Negative IDs", "", "- `" + "`, `".join(result.false_negative_ids) + "`"])
    if result.false_positive_ids:
        lines.extend(["", "## False-Positive IDs", "", "- `" + "`, `".join(result.false_positive_ids) + "`"])
    if result.issues:
        lines.extend(["", "## Issues", ""] + [f"- {issue}" for issue in result.issues])
    return "\n".join(lines) + "\n"
