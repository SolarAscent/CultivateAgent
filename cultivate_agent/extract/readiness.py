"""Offline readiness audit for section-routed extraction.

This module checks whether local full text can support the existing extraction
operators before spending LLM calls. It reports source/section coverage only; it
does not extract claims or adjudicate evidence.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from ..evidence.review_packet import (
    _best_paper_match,
    _review_id_label,
    load_manifest,
    load_review_tasks,
)
from ..ingest import iter_ingested
from ..schema.structured_paper import (
    StructuredPaper,
    structured_paper_from_grobid_tei_path,
    structured_paper_from_text,
)
from .operators import OPERATORS, ExtractionOperator


CRITICAL_OPERATORS = {"medium", "dose", "endpoints"}

_NUMERIC_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:ng/ml|ug/ml|mg/ml|g/l|mm|um|%|h|hours?|days?|passages?|fold)\b",
    re.I,
)

_SIGNAL_TERMS = {
    "context": {
        "bovine", "satellite", "myoblast", "muscle", "cell", "cells",
    },
    "medium": {
        "medium", "media", "serum-free", "serum", "basal", "dmem", "fgf2",
        "albumin", "supplement", "formulation", "hydrolysate", "extract",
        "conditioned",
    },
    "dose": {
        "ng/ml", "ug/ml", "mg/ml", "concentration", "dose", "doubling",
        "passage", "proliferation", "viability", "cell number",
    },
    "endpoints": {
        "proliferation", "doubling", "viability", "cell counting", "myod",
        "myog", "pax7", "differentiation", "myogenic", "fusion",
    },
    "findings": {
        "conclusion", "significant", "improved", "increased", "decreased",
        "limitation", "cost", "alternative", "serum-free",
    },
}


@dataclass
class OperatorReadiness:
    operator: str
    ready: bool
    status: str
    context_chars: int = 0
    routed_section_ids: List[str] = field(default_factory=list)
    signal_terms: List[str] = field(default_factory=list)
    numeric_hits: int = 0


@dataclass
class PaperReadiness:
    review_id: str
    source_record_id: str
    title: str
    paper_id: str = ""
    fulltext_path: str = ""
    structured_source: str = ""
    text_chars: int = 0
    sections: int = 0
    tables: int = 0
    figures: int = 0
    status: str = "missing_source"
    operators: List[OperatorReadiness] = field(default_factory=list)

    @property
    def critical_ready(self) -> int:
        return sum(1 for op in self.operators if op.operator in CRITICAL_OPERATORS and op.ready)


def build_extraction_readiness(
    *,
    review_queue_path: str | Path,
    manifest_path: str | Path,
    papers_dir: str | Path,
    review_ids: Iterable[str],
    path_base: str | Path | None = None,
) -> List[PaperReadiness]:
    """Build operator-readiness rows for selected human review tasks."""
    ids = set(review_ids)
    tasks = load_review_tasks(review_queue_path, ids=ids)
    manifest = load_manifest(manifest_path)
    ingested = list(iter_ingested(papers_dir))
    display_base = Path(path_base).resolve() if path_base is not None else Path.cwd().resolve()
    rows: List[PaperReadiness] = []

    for task in tasks:
        rec = manifest.get(task.source_record_id)
        title = rec.title if rec else ""
        row = PaperReadiness(
            review_id=task.review_id,
            source_record_id=task.source_record_id,
            title=title or "MISSING",
        )
        match = _best_paper_match(rec, ingested)
        if not match:
            row.status = "missing_ingested_paper"
            rows.append(row)
            continue

        paths, meta = match
        text = paths.read_fulltext()
        row.paper_id = meta.ref.paper_id
        row.fulltext_path = _display_path(paths.fulltext, display_base)
        row.text_chars = len(text)
        if not text.strip():
            row.status = "missing_fulltext"
            rows.append(row)
            continue

        paper = _load_structured_paper(paths.fulltext, meta.ref.paper_id, meta.ref.title)
        row.structured_source = paper.source
        row.sections = len(paper.sections)
        row.tables = len(paper.tables)
        row.figures = len(paper.figures)
        row.operators = [assess_operator_readiness(paper, op) for op in OPERATORS]
        row.status = _overall_status(row)
        rows.append(row)

    return rows


def _display_path(path: Path, base: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return str(resolved)


def assess_operator_readiness(paper: StructuredPaper, op: ExtractionOperator) -> OperatorReadiness:
    passages = paper.section_passages(op.section_hints)
    if passages:
        routed_ids = [sid for sid, _ in passages]
        context = "\n\n".join(text for _, text in passages)
    else:
        routed_ids = []
        context = paper.all_text()

    terms = _matched_terms(op.name, context)
    numeric_hits = len(_NUMERIC_RE.findall(context))
    ready = _operator_ready(op.name, len(context), terms, numeric_hits)
    if ready:
        status = "ready" if passages else "fallback_ready"
    else:
        status = "no_routed_section" if not passages else "weak_context"
    return OperatorReadiness(
        operator=op.name,
        ready=ready,
        status=status,
        context_chars=len(context),
        routed_section_ids=routed_ids,
        signal_terms=terms,
        numeric_hits=numeric_hits,
    )


def write_extraction_readiness_tsv(rows: List[PaperReadiness], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "review_id",
        "source_record_id",
        "paper_id",
        "status",
        "operator",
        "operator_status",
        "ready",
        "context_chars",
        "routed_section_ids",
        "signal_terms",
        "numeric_hits",
        "structured_source",
        "text_chars",
        "sections",
        "tables",
        "figures",
        "title",
        "fulltext_path",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            operators = row.operators or [
                OperatorReadiness(operator="", ready=False, status=row.status)
            ]
            for op in operators:
                writer.writerow({
                    "review_id": row.review_id,
                    "source_record_id": row.source_record_id,
                    "paper_id": row.paper_id,
                    "status": row.status,
                    "operator": op.operator,
                    "operator_status": op.status,
                    "ready": "yes" if op.ready else "no",
                    "context_chars": op.context_chars,
                    "routed_section_ids": ";".join(op.routed_section_ids),
                    "signal_terms": ";".join(op.signal_terms),
                    "numeric_hits": op.numeric_hits,
                    "structured_source": row.structured_source,
                    "text_chars": row.text_chars,
                    "sections": row.sections,
                    "tables": row.tables,
                    "figures": row.figures,
                    "title": row.title,
                    "fulltext_path": row.fulltext_path,
                })
    return out


def write_extraction_readiness_markdown(rows: List[PaperReadiness], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    ready = sum(1 for r in rows if r.status == "ready_for_operator_extraction")
    fallback = sum(1 for r in rows if r.status == "ready_with_fulltext_fallback")
    partial = sum(1 for r in rows if r.status == "partial_operator_ready")
    packet_label = _review_id_label(row.review_id for row in rows)
    lines = [
        f"# Extraction Readiness: {packet_label}",
        "",
        "Status: offline section-routing preflight; not an extraction result and not evidence adjudication.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Review tasks checked | {len(rows)} |",
        f"| Ready for operator extraction | {ready} |",
        f"| Ready with full-text fallback | {fallback} |",
        f"| Partial operator-ready | {partial} |",
        f"| Not ready / missing | {len(rows) - ready - fallback - partial} |",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"| `{status}` | {count} |")
    lines += [
        "",
        "## Task Detail",
        "",
        "| Review ID | Source | Status | Critical operators ready | Source type | Text chars | Sections | Tables |",
        "|---|---|---|---:|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.review_id}` | `{row.source_record_id}` | `{row.status}` | "
            f"{row.critical_ready}/3 | {row.structured_source or '-'} | {row.text_chars} | "
            f"{row.sections} | {row.tables} |"
        )
    lines += [
        "",
        "## Operator Detail",
        "",
    ]
    for row in rows:
        lines += [
            f"### {row.review_id}: {row.source_record_id}",
            "",
            f"- Title: {row.title}",
            f"- Full text: `{row.fulltext_path or 'MISSING'}`",
            "",
            "| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |",
            "|---|---|---:|---|---|---:|",
        ]
        if not row.operators:
            lines.append(f"| - | `{row.status}` | 0 | - | - | 0 |")
        else:
            for op in row.operators:
                lines.append(
                    f"| `{op.operator}` | `{op.status}` | {op.context_chars} | "
                    f"{', '.join(op.routed_section_ids) or '-'} | "
                    f"{', '.join(op.signal_terms[:10]) or '-'} | {op.numeric_hits} |"
                )
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _load_structured_paper(fulltext_path: Path, paper_id: str, title: str) -> StructuredPaper:
    tei_path = fulltext_path.with_name("fulltext.xml")
    if tei_path.exists():
        try:
            return structured_paper_from_grobid_tei_path(paper_id, tei_path, title=title)
        except Exception:  # noqa: BLE001
            pass
    text = fulltext_path.read_text(encoding="utf-8", errors="ignore")
    return structured_paper_from_text(paper_id, text, title=title)


def _matched_terms(operator: str, text: str) -> List[str]:
    lower = text.lower()
    return sorted(term for term in _SIGNAL_TERMS.get(operator, set()) if term in lower)


def _operator_ready(
    operator: str,
    context_chars: int,
    signal_terms: List[str],
    numeric_hits: int,
) -> bool:
    if context_chars < 200:
        return False
    if operator == "dose":
        return numeric_hits >= 1 or len(signal_terms) >= 2
    if operator in {"medium", "endpoints"}:
        return len(signal_terms) >= 2
    return bool(signal_terms) or context_chars >= 1000


def _overall_status(row: PaperReadiness) -> str:
    ready_ops = {op.operator for op in row.operators if op.ready}
    if CRITICAL_OPERATORS <= ready_ops:
        critical = [op for op in row.operators if op.operator in CRITICAL_OPERATORS]
        if any(op.status == "fallback_ready" for op in critical):
            return "ready_with_fulltext_fallback"
        return "ready_for_operator_extraction"
    if "medium" in ready_ops and ({"dose", "endpoints"} & ready_ops):
        return "partial_operator_ready"
    return "weak_operator_context"
