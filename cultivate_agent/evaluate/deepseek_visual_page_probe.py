"""Source-bound DeepSeek gate for quantitative visual-result page pointers."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

from .deepseek_locator_probe import LocatorItem, LocatorProbeResult
from .deepseek_page_probe import _page_excerpt
from .quantitative_review import _sha256


PROMPT_VERSION = "visual-result-page-pointer-v1"
SELECTOR_VERSION = "jats-caption-stat-context-v1"
_DISPERSION = re.compile(r"\b(?:sd|sem)\b|standard deviation|standard error|error bars?", re.I)
_SAMPLE = re.compile(r"\bn\s*[=><]|replicat|observations|independent experiments?", re.I)
_OUTCOME = re.compile(
    r"prolifer|cell (?:number|count|growth|viability)|doubling|myod|pax7|"
    r"differenti|expression|growth rate|utilization rate",
    re.I,
)
_COMPARISON = re.compile(r"control|medium|media|treat|versus|compared|concentration|cultured", re.I)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "of", "on", "or", "that", "the", "to", "was", "were", "with",
}


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN.findall(text.casefold()) if token not in _STOP}


def _caption(fig: ET.Element) -> str:
    node = fig.find("caption")
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def _qualifies(caption: str) -> bool:
    return all(pattern.search(caption) for pattern in (_DISPERSION, _SAMPLE, _OUTCOME, _COMPARISON))


def _best_page(caption: str, pages: Sequence[str]) -> tuple[int, float, float]:
    wanted = _tokens(caption)
    if not wanted:
        return 0, 0.0, 0.0
    scores = sorted(
        ((len(wanted & _tokens(page)) / len(wanted), index) for index, page in enumerate(pages, 1)),
        reverse=True,
    )
    best_score, best_page = scores[0]
    second = scores[1][0] if len(scores) > 1 else 0.0
    return best_page, best_score, second


def build_visual_silver_manifest(
    record_ids: Sequence[str],
    *,
    jats_sources: Sequence[dict[str, str]],
    jats_acquisitions: Sequence[dict[str, str]],
    pdf_audits: Sequence[dict[str, str]],
    repo_root: Path,
    max_excerpt_chars: int = 2400,
    fitz_module=None,
) -> dict[str, object]:
    """Derive page silver from verified JATS captions without copying source text."""
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    source_by_id = {row["record_id"]: row for row in jats_sources}
    acquisition_by_id = {row["record_id"]: row for row in jats_acquisitions}
    pdf_by_id = {row["record_id"]: row for row in pdf_audits}
    sources: list[dict[str, object]] = []
    candidates: list[dict[str, object]] = []
    for record_id in record_ids:
        source = source_by_id.get(record_id)
        acquisition = acquisition_by_id.get(record_id)
        pdf = pdf_by_id.get(record_id)
        if not source or not acquisition or not pdf:
            raise ValueError(f"{record_id}: source metadata is incomplete")
        if len({source["paper_id"], acquisition["paper_id"], pdf["paper_id"]}) != 1:
            raise ValueError(f"{record_id}: paper ID mismatch")
        jats_path = repo_root / "data/papers" / source["paper_id"] / "fulltext.xml"
        pdf_path = repo_root / pdf["pdf_path"]
        if not jats_path.is_file() or _sha256(jats_path.read_bytes()) != acquisition["source_sha256"]:
            raise ValueError(f"{record_id}: JATS missing or hash mismatch")
        if not pdf_path.is_file() or _sha256(pdf_path.read_bytes()) != pdf["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        document = fitz_module.open(pdf_path)
        try:
            page_texts = [" ".join(page.get_text().split()) for page in document]
            page_excerpts = [
                _page_excerpt(page, max_chars=max_excerpt_chars) for page in document
            ]
        finally:
            document.close()
        figures = []
        unmatched = 0
        for index, fig in enumerate(ET.parse(jats_path).getroot().findall(".//fig"), 1):
            caption = _caption(fig)
            if not _qualifies(caption):
                continue
            page, score, second = _best_page(caption, page_texts)
            if score < 0.59 or score - second < 0.05:
                unmatched += 1
                continue
            figures.append((str(fig.get("id") or f"fig-{index}"), page))
        if not figures:
            raise ValueError(f"{record_id}: no qualifying visual-result figure")
        by_page: dict[int, list[str]] = {}
        for figure_id, page in figures:
            by_page.setdefault(page, []).append(figure_id)
        for page, figure_ids in sorted(by_page.items()):
            excerpt = page_excerpts[page - 1]
            if not excerpt:
                raise ValueError(f"{record_id}: candidate page {page} has no deterministic excerpt")
            candidates.append({
                "record_id": record_id,
                "pdf_page": page,
                "figure_ids": sorted(figure_ids),
                "page_excerpt_sha256": _sha256(excerpt.encode()),
            })
        sources.append({
            "record_id": record_id,
            "paper_id": source["paper_id"],
            "jats_path": str(jats_path.relative_to(repo_root)),
            "jats_sha256": acquisition["source_sha256"],
            "pdf_path": pdf["pdf_path"],
            "pdf_sha256": pdf["pdf_sha256"],
            "pdf_pages": len(page_texts),
            "unmatched_qualifying_figures": unmatched,
        })
    return {
        "format_version": 1,
        "selector_version": SELECTOR_VERSION,
        "sources": sources,
        "candidates": candidates,
        "limitations": [
            "Silver positives are deterministic JATS-caption-to-PDF-page pointers, not biological evidence.",
            "Qualifying captions without an unambiguous PDF text match are excluded from silver.",
            "No caption text or numeric value is stored in this manifest.",
        ],
    }


def load_visual_page_silver(
    manifest_path: Path,
    *,
    repo_root: Path,
    max_excerpt_chars: int = 2400,
    fitz_module=None,
) -> list[LocatorItem]:
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("selector_version") != SELECTOR_VERSION:
        raise ValueError("visual silver selector version mismatch")
    positives = {
        (str(row["record_id"]), int(row["pdf_page"])): str(row["page_excerpt_sha256"])
        for row in payload.get("candidates", [])
    }
    items: list[LocatorItem] = []
    index = 0
    for source in payload.get("sources", []):
        path = repo_root / source["pdf_path"]
        if not path.is_file() or _sha256(path.read_bytes()) != source["pdf_sha256"]:
            raise ValueError(f"{source['record_id']}: PDF missing or hash mismatch")
        document = fitz_module.open(path)
        try:
            for page_number, page in enumerate(document, 1):
                excerpt = _page_excerpt(page, max_chars=max_excerpt_chars)
                if not excerpt:
                    continue
                index += 1
                digest = _sha256(excerpt.encode())
                expected = positives.get((source["record_id"], page_number))
                if expected is not None and digest != expected:
                    raise ValueError(f"{source['record_id']}: candidate page excerpt hash mismatch")
                items.append(LocatorItem(
                    item_id=f"V{index:03d}", snippet=excerpt, positive=expected is not None,
                    record_id=source["record_id"], pdf_page=page_number, block_index=-1,
                    block_text_sha256=digest,
                ))
        finally:
            document.close()
    if len({(item.record_id, item.pdf_page) for item in items if item.positive}) != len(positives):
        raise ValueError("one or more visual silver pages were not loaded")
    return items


def build_visual_page_prompt(batch: Sequence[LocatorItem]) -> str:
    payload = {"pages": [{"id": item.item_id, "excerpt": item.snippet} for item in batch]}
    return (
        "Select every page that could contain a quantitative visual result needed to recover "
        "treatment/control group statistics for cell-culture medium evaluation. Include pages "
        "with result figures or figure captions that mention a measured cell outcome together "
        "with dispersion/error bars and sample-size or replicate context. Optimize for recall. "
        "Return JSON only with exactly {\"candidate_ids\":[str]}. Use only supplied IDs, no "
        "duplicates, and return no excerpts, numbers, explanations, confidence, or other keys.\n"
        "INPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


def selected_fractions(result: LocatorProbeResult) -> tuple[float, ...]:
    return tuple(round(len(selection) / result.items, 4) for selection in result.selections)


def deployment_gate_pass(result: LocatorProbeResult, *, max_selected_fraction: float = 0.60) -> bool:
    fractions = selected_fractions(result)
    return (
        0 < max_selected_fraction < 1
        and len(fractions) >= 3
        and result.gate_pass
        and max(fractions) <= max_selected_fraction
    )


def result_manifest(
    result: LocatorProbeResult,
    items: Sequence[LocatorItem],
    *,
    model: str,
    max_selected_fraction: float = 0.60,
) -> dict[str, object]:
    by_id = {item.item_id: item for item in items}
    passed = deployment_gate_pass(result, max_selected_fraction=max_selected_fraction)
    return {
        "format_version": 1,
        "status": "pass_for_bounded_shadow" if passed else "failed_no_routing",
        "deployment_gate_pass": passed,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "selector_version": SELECTOR_VERSION,
        "repeats": len(result.selections),
        "requests_expected": result.requests_expected,
        "requests_valid": result.requests_valid,
        "validation_issues": list(result.issues),
        "items": result.items,
        "positives": result.positives,
        "repeat_recalls": list(result.repeat_recalls),
        "repeat_selected_fractions": list(selected_fractions(result)),
        "selection_consistency": result.selection_consistency,
        "total_tokens": result.total_tokens,
        "max_selected_fraction_gate": max_selected_fraction,
        "repeat_selections": [
            [
                {
                    "candidate_id": item_id,
                    "record_id": by_id[item_id].record_id,
                    "pdf_page": by_id[item_id].pdf_page,
                    "page_excerpt_sha256": by_id[item_id].block_text_sha256,
                }
                for item_id in selection
            ]
            for selection in result.selections
        ],
        "limitations": [
            "DeepSeek returned page pointers only; no source number or excerpt is stored.",
            "Passing authorizes a bounded shadow run only, not evidence or tier decisions.",
        ],
    }


def validate_result_manifest(payload: dict[str, object], items: Sequence[LocatorItem]) -> list[str]:
    issues: list[str] = []
    allowed = {
        "format_version", "status", "deployment_gate_pass", "model", "prompt_version",
        "selector_version", "repeats", "items", "positives", "repeat_recalls",
        "repeat_selected_fractions", "selection_consistency", "total_tokens",
        "max_selected_fraction_gate", "requests_expected", "requests_valid",
        "validation_issues", "repeat_selections", "limitations",
    }
    if set(payload) != allowed:
        issues.append("visual result manifest top-level schema mismatch")
    expected = {item.item_id: item for item in items}
    selections = payload.get("repeat_selections")
    if not isinstance(selections, list):
        return issues + ["repeat selections must be a list"]
    keys = {"candidate_id", "record_id", "pdf_page", "page_excerpt_sha256"}
    for repeat in selections:
        if not isinstance(repeat, list):
            issues.append("repeat selection must be a list")
            continue
        seen: set[str] = set()
        for row in repeat:
            if not isinstance(row, dict) or set(row) != keys:
                issues.append("selection pointer schema mismatch")
                continue
            item = expected.get(str(row.get("candidate_id")))
            if item is None or row != {
                "candidate_id": item.item_id, "record_id": item.record_id,
                "pdf_page": item.pdf_page, "page_excerpt_sha256": item.block_text_sha256,
            }:
                issues.append("selection pointer provenance mismatch")
            if item and item.item_id in seen:
                issues.append("duplicate selection pointer")
            if item:
                seen.add(item.item_id)
    selected_sets = [
        {str(row.get("candidate_id")) for row in repeat if isinstance(row, dict)}
        for repeat in selections if isinstance(repeat, list)
    ]
    positive_ids = {item.item_id for item in items if item.positive}
    recalls = [round(len(selected & positive_ids) / len(positive_ids), 4) for selected in selected_sets]
    fractions = [round(len(selected) / len(items), 4) for selected in selected_sets]
    consistency = round(sum(
        len({item.item_id in selected for selected in selected_sets}) == 1 for item in items
    ) / len(items), 4) if selected_sets else 0.0
    if payload.get("repeats") != len(selected_sets):
        issues.append("repeat count mismatch")
    if payload.get("items") != len(items) or payload.get("positives") != len(positive_ids):
        issues.append("item count mismatch")
    if payload.get("repeat_recalls") != recalls:
        issues.append("repeat recall mismatch")
    if payload.get("repeat_selected_fractions") != fractions:
        issues.append("selected fraction mismatch")
    if payload.get("selection_consistency") != consistency:
        issues.append("selection consistency mismatch")
    valid_requests = payload.get("requests_valid")
    expected_requests = payload.get("requests_expected")
    validation_issues = payload.get("validation_issues")
    recomputed_pass = (
        len(selected_sets) >= 3
        and bool(recalls)
        and min(recalls) >= 0.95
        and consistency >= 0.95
        and bool(fractions)
        and max(fractions) <= payload.get("max_selected_fraction_gate", 0)
        and valid_requests == expected_requests
        and validation_issues == []
    )
    if payload.get("deployment_gate_pass") != recomputed_pass:
        issues.append("deployment gate mismatch")
    expected_status = "pass_for_bounded_shadow" if recomputed_pass else "failed_no_routing"
    if payload.get("status") != expected_status:
        issues.append("deployment status mismatch")
    return issues
