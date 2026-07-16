"""Source-hash-bound page-candidate probe using existing locator gold."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .deepseek_locator_probe import LocatorItem, ShadowLocalizationResult
from ..ingest.oa_audit import normalize_doi
from .quantitative_review import _sha256, _signals


PROMPT_VERSION = "page-candidate-pointer-v1"
SIGNALS = {
    "explicit_dispersion", "named_dispersion_value", "sample_size", "sd", "sem",
    "outcome", "medium", "figure_caption", "mean", "error_policy",
}


@dataclass(frozen=True)
class PageShadowSource:
    record_id: str
    doi: str
    pdf_path: str
    pdf_sha256: str


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _page_excerpt(page, *, max_chars: int) -> str:
    blocks = [_normalized(str(block[4])) for block in page.get_text("blocks", sort=True)]
    blocks = [block for block in blocks if block]
    selected = [block for block in blocks if set(_signals(block)) & SIGNALS]
    if blocks:
        selected.insert(0, blocks[0])
    excerpt = "\n".join(dict.fromkeys(selected))
    return excerpt[:max_chars]


def load_page_silver(
    manifest_path: Path,
    *,
    repo_root: Path,
    negatives_per_positive: float = 1.0,
    max_excerpt_chars: int = 2400,
    fitz_module=None,
) -> list[LocatorItem]:
    """Aggregate existing block gold to pages and add deterministic unlabeled decoys."""
    if negatives_per_positive < 0 or max_excerpt_chars < 400:
        raise ValueError("invalid page-probe sampling settings")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = {str(row["record_id"]): row for row in manifest.get("sources", [])}
    positive_pages: dict[str, set[int]] = {record_id: set() for record_id in sources}
    for row in manifest.get("candidates", []):
        record_id = str(row["record_id"])
        if record_id not in sources:
            raise ValueError(f"candidate source is absent: {record_id}")
        positive_pages[record_id].add(int(row["pdf_page"]))
    if not sources or not all(positive_pages.values()):
        raise ValueError("page silver requires candidates for every source")

    raw: list[tuple[str, int, str, bool, str]] = []
    for record_id in sorted(sources):
        source = sources[record_id]
        path = repo_root / source["pdf_path"]
        if not path.is_file() or _sha256(path.read_bytes()) != source["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        document = fitz_module.open(path)
        try:
            pages = []
            for page_index, page in enumerate(document, start=1):
                excerpt = _page_excerpt(page, max_chars=max_excerpt_chars)
                if not excerpt:
                    continue
                digest = _sha256(excerpt.encode("utf-8"))
                pages.append((page_index, excerpt, digest))
            by_number = {page_number: (excerpt, digest) for page_number, excerpt, digest in pages}
            for page_number in sorted(positive_pages[record_id]):
                if page_number not in by_number:
                    raise ValueError(f"{record_id}: gold page {page_number} has no excerpt")
                excerpt, digest = by_number[page_number]
                raw.append((record_id, page_number, excerpt, True, digest))
            decoys = [row for row in pages if row[0] not in positive_pages[record_id]]
            decoys.sort(key=lambda row: hashlib.sha256(
                f"{record_id}:{row[0]}:{row[2]}".encode()
            ).hexdigest())
            needed = round(len(positive_pages[record_id]) * negatives_per_positive)
            if len(decoys) < needed:
                raise ValueError(f"{record_id}: insufficient decoy pages")
            for page_number, excerpt, digest in decoys[:needed]:
                raw.append((record_id, page_number, excerpt, False, digest))
        finally:
            document.close()
    raw.sort(key=lambda row: hashlib.sha256(f"{row[0]}:{row[1]}:{row[4]}".encode()).hexdigest())
    return [
        LocatorItem(
            item_id=f"P{index:03d}", snippet=excerpt, positive=positive,
            record_id=record_id, pdf_page=page_number, block_index=-1,
            block_text_sha256=digest,
        )
        for index, (record_id, page_number, excerpt, positive, digest)
        in enumerate(raw, start=1)
    ]


def load_page_shadow_pool(
    source_rows: Sequence[dict[str, str]],
    *,
    corpus_rows: Sequence[dict[str, str]],
    repo_root: Path,
    max_excerpt_chars: int = 2400,
    fitz_module=None,
) -> tuple[list[LocatorItem], tuple[PageShadowSource, ...]]:
    """Load all pages from explicitly hash-bound, canonical shadow sources."""
    if not source_rows or max_excerpt_chars < 400:
        raise ValueError("shadow source list is empty or excerpt bound is invalid")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    corpus = {row["record_id"]: row for row in corpus_rows}
    sources: list[PageShadowSource] = []
    raw: list[tuple[str, int, str, str]] = []
    seen: set[str] = set()
    for row in source_rows:
        required = {"record_id", "doi", "pdf_path", "pdf_sha256"}
        if set(row) != required:
            raise ValueError("page shadow source schema mismatch")
        record_id = row["record_id"]
        if record_id in seen:
            raise ValueError(f"duplicate shadow source: {record_id}")
        seen.add(record_id)
        canonical = corpus.get(record_id)
        if canonical is None or normalize_doi(canonical.get("doi", "")) != normalize_doi(row["doi"]):
            raise ValueError(f"{record_id}: canonical DOI mismatch")
        path = repo_root / row["pdf_path"]
        if not path.is_file() or _sha256(path.read_bytes()) != row["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        source = PageShadowSource(record_id, row["doi"], row["pdf_path"], row["pdf_sha256"])
        sources.append(source)
        document = fitz_module.open(path)
        try:
            for page_number, page in enumerate(document, start=1):
                excerpt = _page_excerpt(page, max_chars=max_excerpt_chars)
                if excerpt:
                    raw.append((record_id, page_number, excerpt, _sha256(excerpt.encode())))
        finally:
            document.close()
    raw.sort(key=lambda value: (value[0], value[1]))
    items = [
        LocatorItem(
            item_id=f"P{index:04d}", snippet=excerpt, positive=False,
            record_id=record_id, pdf_page=page_number, block_index=-1,
            block_text_sha256=excerpt_hash,
        )
        for index, (record_id, page_number, excerpt, excerpt_hash) in enumerate(raw, start=1)
    ]
    if not items:
        raise ValueError("shadow sources contain no readable pages")
    return items, tuple(sources)


def page_shadow_manifest(
    result: ShadowLocalizationResult,
    *,
    sources: Sequence[PageShadowSource],
    model: str,
) -> dict[str, object]:
    """Build an IDs-and-hashes-only artifact; unstable runs emit no candidates."""
    selected = set(result.selected_ids) if result.gate_pass else set()
    input_chars = sum(len(item.snippet) for item in result.items)
    selected_chars = sum(len(item.snippet) for item in result.items if item.item_id in selected)
    source_by_id = {source.record_id: source for source in sources}
    input_counts = {source.record_id: 0 for source in sources}
    selected_counts = {source.record_id: 0 for source in sources}
    for item in result.items:
        input_counts[item.record_id] += 1
        if item.item_id in selected:
            selected_counts[item.record_id] += 1
    return {
        "format_version": 1,
        "status": "candidate_pointers_for_expert_review" if result.gate_pass else "failed_unstable_no_output",
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "repeats": result.repeats,
        "selection_consistency": result.selection_consistency,
        "total_tokens": result.total_tokens,
        "input_pages": len(result.items),
        "selected_pages": len(selected),
        "input_excerpt_chars": input_chars,
        "selected_excerpt_chars": selected_chars,
        "excerpt_reduction_fraction": round(1 - selected_chars / input_chars, 4),
        "sources": [
            {
                "record_id": source.record_id, "doi": source.doi,
                "pdf_path": source.pdf_path, "pdf_sha256": source.pdf_sha256,
                "input_pages": input_counts[source.record_id],
                "selected_pages": selected_counts[source.record_id],
            }
            for source in sources
        ],
        "candidates": [
            {
                "candidate_id": item.item_id, "record_id": item.record_id,
                "pdf_page": item.pdf_page,
                "page_excerpt_sha256": item.block_text_sha256,
                "source_pdf_sha256": source_by_id[item.record_id].pdf_sha256,
            }
            for item in result.items if item.item_id in selected
        ],
        "limitations": [
            "DeepSeek returned page IDs only; excerpts and numeric values are absent.",
            "Candidate pages are not evidence and require deterministic source revalidation.",
            "A stronger model or human reviewer must decide relevance and evidence support.",
        ],
    }


def validate_page_shadow_manifest(
    payload: dict[str, object],
    *,
    items: Sequence[LocatorItem],
    sources: Sequence[PageShadowSource],
) -> list[str]:
    """Reject unknown pointers, metadata drift, numeric fields, and failed-gate leakage."""
    issues: list[str] = []
    allowed_top = {
        "format_version", "status", "model", "prompt_version", "repeats",
        "selection_consistency", "total_tokens", "input_pages", "selected_pages",
        "input_excerpt_chars", "selected_excerpt_chars", "excerpt_reduction_fraction",
        "sources", "candidates", "limitations",
    }
    if set(payload) != allowed_top:
        issues.append("page shadow top-level schema mismatch")
    if payload.get("prompt_version") != PROMPT_VERSION:
        issues.append("page shadow prompt version mismatch")
    expected_items = {item.item_id: item for item in items}
    expected_sources = {source.record_id: source for source in sources}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return issues + ["page shadow candidates must be a list"]
    allowed_candidate = {
        "candidate_id", "record_id", "pdf_page", "page_excerpt_sha256", "source_pdf_sha256",
    }
    seen: set[str] = set()
    for index, row in enumerate(candidates):
        if not isinstance(row, dict) or set(row) != allowed_candidate:
            issues.append(f"candidate {index} schema mismatch")
            continue
        item = expected_items.get(str(row.get("candidate_id")))
        source = expected_sources.get(str(row.get("record_id")))
        if item is None or source is None:
            issues.append(f"candidate {index} has unknown pointer")
            continue
        if item.item_id in seen:
            issues.append(f"duplicate candidate {item.item_id}")
        seen.add(item.item_id)
        expected = {
            "candidate_id": item.item_id, "record_id": item.record_id,
            "pdf_page": item.pdf_page, "page_excerpt_sha256": item.block_text_sha256,
            "source_pdf_sha256": source.pdf_sha256,
        }
        if row != expected:
            issues.append(f"candidate {item.item_id} pointer metadata mismatch")
    if payload.get("input_pages") != len(items) or payload.get("selected_pages") != len(candidates):
        issues.append("page shadow counts mismatch")
    source_rows = payload.get("sources")
    allowed_source = {
        "record_id", "doi", "pdf_path", "pdf_sha256", "input_pages", "selected_pages",
    }
    input_by_source = {record_id: 0 for record_id in expected_sources}
    selected_by_source = {record_id: 0 for record_id in expected_sources}
    for item in items:
        input_by_source[item.record_id] += 1
    for row in candidates:
        if isinstance(row, dict) and row.get("record_id") in selected_by_source:
            selected_by_source[row["record_id"]] += 1
    if not isinstance(source_rows, list):
        issues.append("page shadow sources must be a list")
    else:
        seen_sources: set[str] = set()
        for index, row in enumerate(source_rows):
            if not isinstance(row, dict) or set(row) != allowed_source:
                issues.append(f"source {index} schema mismatch")
                continue
            source = expected_sources.get(str(row.get("record_id")))
            if source is None:
                issues.append(f"source {index} is unknown")
                continue
            if source.record_id in seen_sources:
                issues.append(f"duplicate source {source.record_id}")
            seen_sources.add(source.record_id)
            expected = {
                "record_id": source.record_id, "doi": source.doi,
                "pdf_path": source.pdf_path, "pdf_sha256": source.pdf_sha256,
                "input_pages": input_by_source[source.record_id],
                "selected_pages": selected_by_source[source.record_id],
            }
            if row != expected:
                issues.append(f"source {source.record_id} metadata mismatch")
        if seen_sources != set(expected_sources):
            issues.append("page shadow source coverage mismatch")
    input_chars = sum(len(item.snippet) for item in items)
    selected_chars = sum(
        len(expected_items[row["candidate_id"]].snippet)
        for row in candidates
        if isinstance(row, dict) and row.get("candidate_id") in expected_items
    )
    expected_reduction = round(1 - selected_chars / input_chars, 4)
    if (
        payload.get("input_excerpt_chars") != input_chars
        or payload.get("selected_excerpt_chars") != selected_chars
        or payload.get("excerpt_reduction_fraction") != expected_reduction
    ):
        issues.append("page shadow excerpt accounting mismatch")
    if payload.get("status") != "candidate_pointers_for_expert_review" and candidates:
        issues.append("failed shadow status must suppress candidate output")
    return issues


def build_page_prompt(batch: Sequence[LocatorItem]) -> str:
    payload = {"pages": [{"id": item.item_id, "excerpt": item.snippet} for item in batch]}
    return (
        "Select every page that could help a reviewer locate quantitative cell-culture medium "
        "comparison evidence, including methods, results, tables, or figure captions. Optimize "
        "for recall; deterministic code and expert review will remove false positives. Return "
        "JSON only with exactly {\"candidate_ids\":[str]}. IDs must come from the input and "
        "must not repeat. Return no excerpts, numbers, explanations, confidence, or other keys.\n"
        "INPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )
