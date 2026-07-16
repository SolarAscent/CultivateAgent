"""Bounded DeepSeek probe for cross-paper metadata-linkage anomalies."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import statistics
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


PROMPT_VERSION = "metadata-linkage-pointer-v1"


@dataclass(frozen=True)
class MetadataCanaryItem:
    item_id: str
    title_record_id: str
    abstract_record_id: str
    title: str
    abstract: str
    expected_mismatch: bool

    @property
    def input_sha256(self) -> str:
        return _sha256_json({"title": self.title, "abstract": self.abstract})


@dataclass(frozen=True)
class MetadataProbeResult:
    items: int
    positives: int
    requests_expected: int
    requests_valid: int
    repeat_recalls: tuple[float, ...]
    repeat_precisions: tuple[float, ...]
    repeat_candidate_counts: tuple[int, ...]
    selection_consistency: float
    candidate_count_stddev: float
    total_tokens: int
    issues: tuple[str, ...]
    selections: tuple[tuple[str, ...], ...]
    input_hashes: tuple[tuple[str, str], ...]
    false_negative_ids: tuple[str, ...]
    false_positive_ids: tuple[str, ...]

    @property
    def gate_pass(self) -> bool:
        return (
            not self.issues
            and self.requests_valid == self.requests_expected
            and bool(self.repeat_recalls)
            and min(self.repeat_recalls) >= 0.95
            and min(self.repeat_precisions) >= 0.75
            and self.selection_consistency >= 0.95
        )


def _normalized_title(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _normalized_abstract(value: str) -> str:
    return " ".join(value.split())


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_metadata_canary(
    spec_path: Path,
    *,
    corpus_manifest_path: Path,
    zotero_csv_path: Path,
) -> list[MetadataCanaryItem]:
    """Resolve a pointer-only canary against canonical and Zotero metadata."""
    specs = _read_tsv(spec_path)
    required = {"item_id", "title_record_id", "abstract_record_id", "expected_mismatch"}
    if not specs or required - set(specs[0]):
        raise ValueError("metadata canary spec is missing required columns")
    item_ids = [row["item_id"] for row in specs]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("metadata canary spec contains duplicate item IDs")

    corpus_rows = _read_tsv(corpus_manifest_path)
    corpus = {row["record_id"]: row for row in corpus_rows}
    if len(corpus) != len(corpus_rows):
        raise ValueError("canonical corpus contains duplicate record IDs")

    with zotero_csv_path.open(encoding="utf-8-sig", newline="") as handle:
        zotero_rows = list(csv.DictReader(handle))
    zotero_by_doi: dict[str, list[dict[str, str]]] = {}
    for row in zotero_rows:
        doi = (row.get("DOI") or "").strip().lower()
        if doi:
            zotero_by_doi.setdefault(doi, []).append(row)

    resolved: dict[str, tuple[str, str]] = {}
    needed_ids = {
        row[key] for row in specs for key in ("title_record_id", "abstract_record_id")
    }
    for record_id in sorted(needed_ids):
        record = corpus.get(record_id)
        if record is None:
            raise ValueError(f"unknown corpus record {record_id}")
        doi = record.get("doi", "").strip().lower()
        candidates = zotero_by_doi.get(doi, [])
        title_matches = [
            row for row in candidates
            if _normalized_title(row.get("Title") or "") == _normalized_title(record["title"])
        ]
        abstracts = [
            (row.get("Abstract Note") or "").strip() for row in title_matches
            if (row.get("Abstract Note") or "").strip()
        ]
        if not abstracts:
            raise ValueError(
                f"{record_id} must resolve to a title-matched non-empty Zotero abstract"
            )
        max_length = max(len(_normalized_abstract(value)) for value in abstracts)
        longest = {
            _normalized_abstract(value) for value in abstracts
            if len(_normalized_abstract(value)) == max_length
        }
        # Duplicate Zotero exports can retain publisher and indexed variants.
        # Prefer the longest normalized abstract, then a stable lexical tie-break.
        resolved[record_id] = (record["title"], sorted(longest)[0])

    items: list[MetadataCanaryItem] = []
    for row in specs:
        expected = row["expected_mismatch"].strip().lower()
        if expected not in {"yes", "no"}:
            raise ValueError(f"invalid expected_mismatch for {row['item_id']}")
        title = resolved[row["title_record_id"]][0]
        abstract = resolved[row["abstract_record_id"]][1]
        logical_mismatch = row["title_record_id"] != row["abstract_record_id"]
        if logical_mismatch != (expected == "yes"):
            raise ValueError(f"inconsistent gold linkage for {row['item_id']}")
        items.append(MetadataCanaryItem(
            item_id=row["item_id"],
            title_record_id=row["title_record_id"],
            abstract_record_id=row["abstract_record_id"],
            title=title,
            abstract=abstract,
            expected_mismatch=logical_mismatch,
        ))
    return items


def build_prompt(batch: Sequence[MetadataCanaryItem]) -> str:
    payload = {
        "records": [
            {"id": item.item_id, "title": item.title, "abstract": item.abstract}
            for item in batch
        ]
    }
    return (
        "Find records whose abstract is semantically inconsistent with the supplied paper title, "
        "as can happen when metadata from two papers is cross-linked. All records concern closely "
        "related cultivated-meat or cell-culture research, so topic overlap alone is not enough: "
        "flag only a substantive mismatch in intervention, study question, cells, or claimed result. "
        "This is candidate localization, not metadata correction. Return JSON only with shape "
        "{\"candidates\":[{\"id\":str,\"fields\":[\"abstract\"]}]}. Include only suspected "
        "mismatches. Use only supplied IDs, exactly the literal field pointer abstract, no duplicate "
        "IDs, and no other keys. Do not return titles, abstracts, corrected text, explanations, "
        "confidence, DOI, year, or numeric values.\nINPUT_JSON:\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


def validate_response(response_text: str, batch: Sequence[MetadataCanaryItem]) -> tuple[set[str], list[str]]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return set(), [f"invalid JSON: {exc}"]
    if set(payload) != {"candidates"} or not isinstance(payload.get("candidates"), list):
        return set(), ["response must contain only a candidates list"]
    allowed_ids = {item.item_id for item in batch}
    selected: set[str] = set()
    issues: list[str] = []
    for index, row in enumerate(payload["candidates"]):
        if not isinstance(row, dict) or set(row) != {"id", "fields"}:
            issues.append(f"candidate {index} has invalid keys")
            continue
        item_id = row["id"]
        if item_id not in allowed_ids:
            issues.append(f"unexpected item id {item_id!r}")
            continue
        if item_id in selected:
            issues.append(f"duplicate item id {item_id}")
            continue
        if row["fields"] != ["abstract"]:
            issues.append(f"{item_id}: fields must be the abstract pointer only")
            continue
        selected.add(item_id)
    return selected, issues


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def _usage_record(usage: int | dict[str, int]) -> dict[str, int]:
    if isinstance(usage, dict):
        return {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": int(usage)}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def run_metadata_probe(
    items: Sequence[MetadataCanaryItem],
    *,
    checkpoint_dir: Path,
    model: str,
    repeats: int,
    batch_size: int,
    max_requests: int,
    max_total_tokens: int,
    max_output_tokens: int,
    caller: Callable[[str, int], tuple[str, int | dict[str, int]]],
) -> MetadataProbeResult:
    if repeats < 3:
        raise ValueError("metadata probe requires at least three repeats")
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    expected_requests = repeats * len(batches)
    if expected_requests > max_requests:
        raise ValueError(f"probe requires {expected_requests} requests, above hard cap {max_requests}")
    if expected_requests * max_output_tokens > max_total_tokens:
        raise ValueError("configured output budget exceeds hard total-token cap")

    gold = {item.item_id for item in items if item.expected_mismatch}
    all_selections: list[set[str]] = []
    issues: list[str] = []
    requests_valid = 0
    total_tokens = 0
    for repeat in range(repeats):
        repeat_selection: set[str] = set()
        for batch_index, batch in enumerate(batches):
            prompt = build_prompt(batch)
            input_hash = _sha256_json({
                "prompt": prompt, "prompt_version": PROMPT_VERSION, "model": model,
            })
            checkpoint = checkpoint_dir / f"{input_hash[:12]}_r{repeat + 1}_b{batch_index + 1}.json"
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text(encoding="utf-8"))
                if record.get("input_hash") != input_hash:
                    raise ValueError(f"checkpoint input hash mismatch: {checkpoint}")
            else:
                response_text, raw_usage = caller(prompt, max_output_tokens)
                usage = _usage_record(raw_usage)
                record = {
                    "input_hash": input_hash,
                    "model": model,
                    "prompt_version": PROMPT_VERSION,
                    "temperature": 0,
                    "thinking": "disabled",
                    "response": response_text,
                    "usage": usage,
                    "total_tokens": usage["total_tokens"],
                }
                _atomic_json(checkpoint, record)
            total_tokens += int(record.get("total_tokens") or 0)
            if total_tokens > max_total_tokens:
                raise RuntimeError("hard total-token cap exceeded; probe stopped at checkpoint")
            selected, response_issues = validate_response(record.get("response", ""), batch)
            if response_issues:
                issues.extend(
                    f"repeat {repeat + 1} batch {batch_index + 1}: {issue}"
                    for issue in response_issues
                )
            else:
                requests_valid += 1
                repeat_selection.update(selected)
        all_selections.append(repeat_selection)

    recalls: list[float] = []
    precisions: list[float] = []
    for selected in all_selections:
        true_positive = len(selected & gold)
        recalls.append(true_positive / len(gold) if gold else 1.0)
        precisions.append(true_positive / len(selected) if selected else (1.0 if not gold else 0.0))
    pairwise = [
        _jaccard(all_selections[i], all_selections[j])
        for i in range(len(all_selections)) for j in range(i + 1, len(all_selections))
    ]
    counts = [len(selected) for selected in all_selections]
    selected_union = set().union(*all_selections) if all_selections else set()
    selected_intersection = set.intersection(*all_selections) if all_selections else set()
    return MetadataProbeResult(
        items=len(items), positives=len(gold), requests_expected=expected_requests,
        requests_valid=requests_valid, repeat_recalls=tuple(recalls),
        repeat_precisions=tuple(precisions), repeat_candidate_counts=tuple(counts),
        selection_consistency=sum(pairwise) / len(pairwise) if pairwise else 1.0,
        candidate_count_stddev=statistics.pstdev(counts) if counts else 0.0,
        total_tokens=total_tokens, issues=tuple(issues),
        selections=tuple(tuple(sorted(selected)) for selected in all_selections),
        input_hashes=tuple((item.item_id, item.input_sha256) for item in items),
        false_negative_ids=tuple(sorted(gold - selected_intersection)),
        false_positive_ids=tuple(sorted(selected_union - gold)),
    )


def manifest_payload(
    result: MetadataProbeResult, *, model: str, prior_invalid_requests: int = 0
) -> dict[str, object]:
    return {
        "task": "cross-paper metadata-linkage anomaly pointer localization",
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "temperature": 0,
        "thinking": "disabled",
        "items": result.items,
        "positives": result.positives,
        "requests_expected": result.requests_expected,
        "requests_valid": result.requests_valid,
        "repeat_recalls": list(result.repeat_recalls),
        "repeat_precisions": list(result.repeat_precisions),
        "repeat_candidate_counts": list(result.repeat_candidate_counts),
        "selection_consistency": result.selection_consistency,
        "candidate_count_stddev": result.candidate_count_stddev,
        "total_tokens": result.total_tokens,
        "issues": list(result.issues),
        "gate_pass": result.gate_pass,
        "false_negative_ids": list(result.false_negative_ids),
        "false_positive_ids": list(result.false_positive_ids),
        "prior_invalid_requests": prior_invalid_requests,
        "prior_invalid_usage_unknown": prior_invalid_requests > 0,
        "input_hashes": dict(result.input_hashes),
        "selections": [list(selection) for selection in result.selections],
        "boundary": "candidate pointers only; no automatic metadata correction",
    }


def validate_manifest_payload(
    payload: dict[str, object], items: Sequence[MetadataCanaryItem]
) -> list[str]:
    expected_keys = {
        "task", "prompt_version", "model", "temperature", "thinking", "items",
        "positives", "requests_expected", "requests_valid", "repeat_recalls",
        "repeat_precisions", "repeat_candidate_counts", "selection_consistency",
        "candidate_count_stddev", "total_tokens", "issues", "gate_pass",
        "false_negative_ids", "false_positive_ids", "prior_invalid_requests",
        "prior_invalid_usage_unknown", "input_hashes", "selections", "boundary",
    }
    issues: list[str] = []
    if set(payload) != expected_keys:
        issues.append("manifest has invalid top-level keys")
        return issues
    expected_hashes = {item.item_id: item.input_sha256 for item in items}
    if payload["input_hashes"] != expected_hashes:
        issues.append("manifest input hashes do not match resolved source metadata")
    if payload["items"] != len(items):
        issues.append("manifest item count mismatch")
    gold = {item.item_id for item in items if item.expected_mismatch}
    if payload["positives"] != len(gold):
        issues.append("manifest positive count mismatch")

    raw_selections = payload.get("selections")
    if not isinstance(raw_selections, list) or len(raw_selections) < 3:
        issues.append("manifest must contain at least three repeat selections")
        return issues
    allowed_ids = set(expected_hashes)
    selections: list[set[str]] = []
    for index, raw in enumerate(raw_selections):
        if not isinstance(raw, list) or not all(isinstance(item_id, str) for item_id in raw):
            issues.append(f"selection {index + 1} is not an ID list")
            continue
        if len(raw) != len(set(raw)) or not set(raw) <= allowed_ids:
            issues.append(f"selection {index + 1} has duplicate or unknown IDs")
            continue
        selections.append(set(raw))
    if len(selections) != len(raw_selections):
        return issues

    recalls = [len(selected & gold) / len(gold) if gold else 1.0 for selected in selections]
    precisions = [
        len(selected & gold) / len(selected) if selected else (1.0 if not gold else 0.0)
        for selected in selections
    ]
    counts = [len(selected) for selected in selections]
    pairwise = [
        _jaccard(selections[i], selections[j])
        for i in range(len(selections)) for j in range(i + 1, len(selections))
    ]
    selected_union = set().union(*selections)
    selected_intersection = set.intersection(*selections)
    expected_values = {
        "repeat_recalls": recalls,
        "repeat_precisions": precisions,
        "repeat_candidate_counts": counts,
        "selection_consistency": sum(pairwise) / len(pairwise) if pairwise else 1.0,
        "candidate_count_stddev": statistics.pstdev(counts),
        "false_negative_ids": sorted(gold - selected_intersection),
        "false_positive_ids": sorted(selected_union - gold),
    }
    for key, expected in expected_values.items():
        if payload[key] != expected:
            issues.append(f"manifest {key} does not recompute from selections")
    recomputed_gate = (
        not payload["issues"]
        and payload["requests_valid"] == payload["requests_expected"]
        and min(recalls) >= 0.95
        and min(precisions) >= 0.75
        and expected_values["selection_consistency"] >= 0.95
    )
    if payload["gate_pass"] is not recomputed_gate:
        issues.append("manifest gate decision does not recompute")
    return issues


def report_markdown(
    result: MetadataProbeResult,
    *,
    model: str,
    max_requests: int,
    max_total_tokens: int,
    prior_invalid_requests: int = 0,
) -> str:
    decision = "PASS" if result.gate_pass else "FAIL"
    routing = (
        "Eligible only for a bounded metadata-QA shadow run; every candidate still requires "
        "deterministic or human confirmation."
        if result.gate_pass else
        "Do not delegate metadata-linkage screening to this model/prompt."
    )
    return "\n".join([
        "# DeepSeek Metadata-Linkage Capability Canary",
        "",
        f"Decision: **{decision}**",
        "",
        "## Fixed Protocol",
        "",
        f"- Model: `{model}` (thinking disabled, temperature 0)",
        f"- Frozen source-authentic items: {result.items} ({result.positives} cross-linked)",
        "- Repeats: 3; schema permits item/field pointers only",
        f"- Hard request cap: {max_requests}",
        f"- Hard total-token cap: {max_total_tokens}",
        "- Gate: minimum repeat recall >= 0.95, minimum repeat precision >= 0.75, "
        "selection Jaccard >= 0.95, and every response schema-valid",
        "",
        "## Result",
        "",
        f"- Valid requests: {result.requests_valid}/{result.requests_expected}",
        f"- Repeat recall: {', '.join(f'{v:.4f}' for v in result.repeat_recalls)}",
        f"- Repeat precision: {', '.join(f'{v:.4f}' for v in result.repeat_precisions)}",
        f"- Candidate counts: {list(result.repeat_candidate_counts)} "
        f"(population SD {result.candidate_count_stddev:.4f})",
        f"- Pairwise selection Jaccard: {result.selection_consistency:.4f}",
        f"- Reported tokens: {result.total_tokens}",
        f"- Schema/runtime issues: {len(result.issues)}",
        f"- False-negative pointers: {', '.join(result.false_negative_ids) or 'none'}",
        f"- False-positive pointers: {', '.join(result.false_positive_ids) or 'none'}",
        f"- Prior invalid implementation attempts: {prior_invalid_requests}; token usage unknown "
        "and excluded from the valid-run metrics",
        "",
        "## Routing Decision",
        "",
        routing,
        "DeepSeek is not authorized to return replacement titles, abstracts, DOI/year values, "
        "scientific inclusion decisions, or evidence judgments.",
        "",
    ])
