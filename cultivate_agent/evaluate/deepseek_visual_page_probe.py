"""Source-bound DeepSeek gate for quantitative visual-result page pointers."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

from .deepseek_locator_probe import LocatorItem, LocatorProbeResult
from .deepseek_page_probe import _page_excerpt
from .quantitative_review import _sha256, _signals


PROMPT_VERSION = "visual-result-page-pointer-v1"
SELECTOR_VERSION = "jats-caption-stat-context-v1"
PDF_HELDOUT_SELECTOR_VERSION = "pdf-visual-stat-block-v1"
_PDF_DISPERSION_SIGNALS = {
    "explicit_dispersion", "named_dispersion_value", "sd", "sem", "error_policy",
}
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
    if payload.get("selector_version") not in {SELECTOR_VERSION, PDF_HELDOUT_SELECTOR_VERSION}:
        raise ValueError("visual page selector version mismatch")
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


def build_pdf_visual_heldout_manifest(
    record_ids: Sequence[str],
    *,
    corpus_rows: Sequence[dict[str, str]],
    pdf_audits: Sequence[dict[str, str]],
    repo_root: Path,
    max_excerpt_chars: int = 2400,
    fitz_module=None,
) -> dict[str, object]:
    """Freeze strict visual-result page locators from audited PDFs before an API run."""
    if not record_ids or len(record_ids) != len(set(record_ids)):
        raise ValueError("held-out record IDs are empty or duplicated")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    corpus = {row["record_id"]: row for row in corpus_rows}
    audits = {row["record_id"]: row for row in pdf_audits}
    sources: list[dict[str, object]] = []
    candidates: list[dict[str, object]] = []
    for record_id in record_ids:
        canonical = corpus.get(record_id)
        audit = audits.get(record_id)
        if canonical is None or audit is None or audit.get("pdf_status") != "audited":
            raise ValueError(f"{record_id}: canonical audited PDF metadata is incomplete")
        path = repo_root / audit["pdf_path"]
        if not path.is_file() or _sha256(path.read_bytes()) != audit["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        document = fitz_module.open(path)
        page_candidates: dict[int, list[dict[str, object]]] = {}
        readable_pages = 0
        try:
            actual_pages = len(document)
            for page_number, page in enumerate(document, 1):
                if _page_excerpt(page, max_chars=max_excerpt_chars):
                    readable_pages += 1
                for block_index, block in enumerate(page.get_text("blocks", sort=True)):
                    text = " ".join(str(block[4]).split())
                    signals = set(_signals(text))
                    required = {"figure_caption", "outcome", "medium", "sample_size"}
                    if not required <= signals or not signals & _PDF_DISPERSION_SIGNALS:
                        continue
                    page_candidates.setdefault(page_number, []).append({
                        "block_index": block_index,
                        "block_text_sha256": _sha256(text.encode()),
                    })
        finally:
            document.close()
        if actual_pages != int(audit["pages"]):
            raise ValueError(f"{record_id}: audited PDF page count mismatch")
        for page_number, locators in sorted(page_candidates.items()):
            document = fitz_module.open(path)
            try:
                excerpt = _page_excerpt(
                    document[page_number - 1], max_chars=max_excerpt_chars
                )
            finally:
                document.close()
            if not excerpt:
                raise ValueError(f"{record_id}: positive page {page_number} has no excerpt")
            candidates.append({
                "record_id": record_id,
                "pdf_page": page_number,
                "supporting_blocks": locators,
                "page_excerpt_sha256": _sha256(excerpt.encode()),
            })
        sources.append({
            "record_id": record_id,
            "paper_id": audit["paper_id"],
            "doi": canonical["doi"],
            "pdf_path": audit["pdf_path"],
            "pdf_sha256": audit["pdf_sha256"],
            "pdf_pages": int(audit["pages"]),
            "readable_pages": readable_pages,
            "positive_pages": len(page_candidates),
        })
    if not candidates:
        raise ValueError("PDF visual held-out set has no strict positive pages")
    return {
        "format_version": 1,
        "selector_version": PDF_HELDOUT_SELECTOR_VERSION,
        "sources": sources,
        "candidates": candidates,
        "limitations": [
            "Positive pages are strict field-aware PDF locators, not adjudicated effects.",
            "Unlabeled pages can still contain useful evidence and are not precision gold.",
            "No source text or numeric value is stored in this manifest.",
        ],
    }


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
    selector_version: str = SELECTOR_VERSION,
) -> dict[str, object]:
    by_id = {item.item_id: item for item in items}
    passed = deployment_gate_pass(result, max_selected_fraction=max_selected_fraction)
    return {
        "format_version": 1,
        "status": "pass_for_bounded_shadow" if passed else "failed_no_routing",
        "deployment_gate_pass": passed,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "selector_version": selector_version,
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


def validate_result_manifest(
    payload: dict[str, object],
    items: Sequence[LocatorItem],
    *,
    selector_version: str = SELECTOR_VERSION,
) -> list[str]:
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
    if payload.get("selector_version") != selector_version:
        issues.append("visual result selector version mismatch")
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


def audit_pdf_visual_shadow(
    heldout_manifest_path: Path,
    result_manifest_path: Path,
    *,
    repo_root: Path,
    fitz_module=None,
) -> dict[str, object]:
    """Compare a strict held-out result with a broader deterministic post-hoc sensitivity set."""
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    heldout = json.loads(heldout_manifest_path.read_text(encoding="utf-8"))
    if heldout.get("selector_version") != PDF_HELDOUT_SELECTOR_VERSION:
        raise ValueError("PDF visual shadow requires the PDF held-out selector")
    items = load_visual_page_silver(
        heldout_manifest_path, repo_root=repo_root, fitz_module=fitz_module
    )
    result = json.loads(result_manifest_path.read_text(encoding="utf-8"))
    result_issues = validate_result_manifest(
        result, items, selector_version=PDF_HELDOUT_SELECTOR_VERSION
    )
    if result_issues:
        raise ValueError("invalid visual shadow result: " + "; ".join(result_issues))
    item_by_pointer = {(item.record_id, item.pdf_page): item for item in items}
    repeat_sets = [
        {str(row["candidate_id"]) for row in repeat}
        for repeat in result["repeat_selections"]
    ]
    unanimous = set.intersection(*repeat_sets) if repeat_sets else set()
    broad_pointers: set[tuple[str, int]] = set()
    source_by_id = {str(row["record_id"]): row for row in heldout["sources"]}
    for record_id, source in source_by_id.items():
        path = repo_root / str(source["pdf_path"])
        if not path.is_file() or _sha256(path.read_bytes()) != source["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch during shadow audit")
        document = fitz_module.open(path)
        try:
            if len(document) != int(source["pdf_pages"]):
                raise ValueError(f"{record_id}: PDF page count drift during shadow audit")
            for page_number, page in enumerate(document, 1):
                for block in page.get_text("blocks", sort=True):
                    signals = set(_signals(" ".join(str(block[4]).split())))
                    if {"figure_caption", "outcome", "medium"} <= signals:
                        broad_pointers.add((record_id, page_number))
                        break
        finally:
            document.close()
    if not broad_pointers or not broad_pointers <= set(item_by_pointer):
        raise ValueError("broad visual sensitivity pages are empty or absent from input pool")
    broad_ids = {item_by_pointer[pointer].item_id for pointer in broad_pointers}
    strict_ids = {item.item_id for item in items if item.positive}
    if not strict_ids <= broad_ids:
        raise ValueError("strict PDF held-out positives must be a subset of broad visual pages")
    selected_broad = broad_ids & unanimous
    broad_recall = round(len(selected_broad) / len(broad_ids), 4)
    incremental_utility_pass = len(unanimous) < len(broad_ids)
    independent_gold = False
    production_pass = (
        result["deployment_gate_pass"] is True
        and broad_recall >= 0.95
        and incremental_utility_pass
        and independent_gold
    )
    missed = sorted(broad_ids - selected_broad)
    return {
        "format_version": 1,
        "status": "pass_for_bounded_production" if production_pass else "failed_no_production_routing",
        "production_gate_pass": production_pass,
        "provider_result_sha256": _sha256(result_manifest_path.read_bytes()),
        "heldout_manifest_sha256": _sha256(heldout_manifest_path.read_bytes()),
        "selector_version": PDF_HELDOUT_SELECTOR_VERSION,
        "broad_sensitivity_timing": "post_hoc_not_independent_gold",
        "input_pages": len(items),
        "strict_positive_pages": len(strict_ids),
        "strict_repeat_recalls": result["repeat_recalls"],
        "broad_baseline_pages": len(broad_ids),
        "model_selected_pages": len(unanimous),
        "broad_selected_pages": len(selected_broad),
        "broad_recall": broad_recall,
        "incremental_utility_pass": incremental_utility_pass,
        "missed_broad_pages": [
            {
                "candidate_id": item_by_pointer[pointer].item_id,
                "record_id": pointer[0],
                "pdf_page": pointer[1],
                "page_excerpt_sha256": item_by_pointer[pointer].block_text_sha256,
            }
            for pointer in sorted(broad_pointers)
            if item_by_pointer[pointer].item_id in missed
        ],
        "limitations": [
            "The broad sensitivity rule was applied after the API run and cannot approve deployment.",
            "Unlabeled pages are not precision negatives and no source text or numeric value is stored.",
            "Production requires both high recall and less review work than the deterministic baseline.",
        ],
    }


def validate_pdf_visual_shadow_audit(payload: dict[str, object]) -> list[str]:
    issues: list[str] = []
    allowed = {
        "format_version", "status", "production_gate_pass", "provider_result_sha256",
        "heldout_manifest_sha256", "selector_version", "broad_sensitivity_timing",
        "input_pages", "strict_positive_pages", "strict_repeat_recalls",
        "broad_baseline_pages", "model_selected_pages", "broad_selected_pages",
        "broad_recall", "incremental_utility_pass", "missed_broad_pages", "limitations",
    }
    if set(payload) != allowed:
        issues.append("visual shadow audit top-level schema mismatch")
    missed = payload.get("missed_broad_pages")
    pointer_keys = {"candidate_id", "record_id", "pdf_page", "page_excerpt_sha256"}
    if not isinstance(missed, list) or any(
        not isinstance(row, dict) or set(row) != pointer_keys for row in missed
    ):
        issues.append("missed broad-page pointer schema mismatch")
    broad_total = payload.get("broad_baseline_pages")
    broad_selected = payload.get("broad_selected_pages")
    if isinstance(broad_total, int) and broad_total > 0 and isinstance(broad_selected, int):
        expected_recall = round(broad_selected / broad_total, 4)
        if payload.get("broad_recall") != expected_recall:
            issues.append("broad recall mismatch")
    else:
        issues.append("invalid broad sensitivity counts")
    expected_utility = (
        isinstance(payload.get("model_selected_pages"), int)
        and isinstance(broad_total, int)
        and payload["model_selected_pages"] < broad_total
    )
    if payload.get("incremental_utility_pass") != expected_utility:
        issues.append("incremental utility mismatch")
    strict_recalls = payload.get("strict_repeat_recalls", [])
    expected_pass = (
        isinstance(strict_recalls, list)
        and len(strict_recalls) >= 3
        and all(float(value) >= 0.95 for value in strict_recalls)
        and isinstance(payload.get("broad_recall"), float)
        and payload["broad_recall"] >= 0.95
        and expected_utility
        and payload.get("broad_sensitivity_timing") != "post_hoc_not_independent_gold"
    )
    if payload.get("production_gate_pass") != expected_pass:
        issues.append("production gate mismatch")
    expected_status = "pass_for_bounded_production" if expected_pass else "failed_no_production_routing"
    if payload.get("status") != expected_status:
        issues.append("production status mismatch")
    return issues
