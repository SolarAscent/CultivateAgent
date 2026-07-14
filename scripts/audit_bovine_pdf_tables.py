#!/usr/bin/env python3
"""Audit P1 bovine PDFs for structured statistical tables and text-only candidates."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path

from cultivate_agent.ingest import PDFTableAuditError, audit_pdf_tables
from cultivate_agent.schema import slugify


FIELDS = [
    "record_id", "paper_id", "pdf_status", "pdf_path", "pdf_sha256", "pages",
    "line_tables", "line_cells", "line_stat_cells", "text_regions", "text_cells",
    "text_stat_cells", "classification", "error",
]


def _read_sources(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"record_id", "paper_id"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"source manifest missing columns: {', '.join(sorted(missing))}")
    if len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("source manifest contains duplicate record_id values")
    return rows


def _validate_sources_against_corpus(
    rows: list[dict[str, str]], corpus_path: Path
) -> None:
    with corpus_path.open(encoding="utf-8", newline="") as handle:
        corpus_rows = list(csv.DictReader(handle, delimiter="\t"))
    by_record = {row["record_id"]: row for row in corpus_rows}
    if len(by_record) != len(corpus_rows):
        raise ValueError("corpus manifest contains duplicate record_id values")
    for row in rows:
        canonical = by_record.get(row["record_id"])
        if canonical is None:
            raise ValueError(f"{row['record_id']} is absent from the corpus manifest")
        canonical_paper_id = slugify(canonical["title"])
        if row["paper_id"] != canonical_paper_id:
            raise ValueError(
                f"{row['record_id']} paper_id disagrees with canonical title: "
                f"{row['paper_id']} != {canonical_paper_id}"
            )


def _write_report(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _summary_markdown(rows: list[dict[str, object]]) -> str:
    audited = [row for row in rows if row["pdf_status"] == "audited"]
    missing = [row for row in rows if row["pdf_status"] != "audited"]
    total = lambda field: sum(int(row[field] or 0) for row in audited)
    line_stats = total("line_stat_cells")
    status = "FAIL" if line_stats == 0 else "REVIEW_REQUIRED"
    lines = [
        "# P1 Bovine PDF Table Off-Ramp Audit",
        "",
        f"**Status: {status}**",
        "",
        "The table-first off-ramp requires at least 10 gold-verified tier-1 effects. "
        "This audit only discovers candidate source cells; it never promotes a cell to tier-1.",
        "",
        "## Result",
        "",
        f"- P1 primary records: {len(rows)}",
        f"- PDFs audited: {len(audited)}; unavailable/ambiguous: {len(missing)}",
        f"- Pages: {total('pages')}",
        f"- Default line-strategy tables/cells: {total('line_tables')} / {total('line_cells')}",
        f"- Default line-strategy statistical cells: {line_stats}",
        f"- Text-layout regions/cells: {total('text_regions')} / {total('text_cells')}",
        f"- Text-layout statistical locator candidates: {total('text_stat_cells')}",
        "- Gold-verified tier-1 effects produced by this audit: 0",
        "",
        "## Interpretation",
        "",
        "PyMuPDF's default strategy detects vector-line tables. Its zero statistical-cell "
        "yield means the current PDFs do not expose an immediately usable structured "
        "mean/SD-or-SEM/n table path. The text strategy is deliberately reported "
        "separately: it reconstructs page-wide layout grids and its hits include prose and "
        "figure captions, so they are locator candidates rather than table cells or effects.",
        "PyMuPDF officially recommends `strategy=\"text\"` when borderless tables are missed "
        "([documentation](https://pymupdf.readthedocs.io/en/latest/faq/index.html#table-extraction)); "
        "the separation here is an empirical safeguard for this corpus, not a rejection of "
        "that strategy in general.",
        "",
        "The result triggers the planned off-ramp from structured tables to a bounded "
        "caption/prose and figure-data pilot. It does not justify scaling text extraction, "
        f"and it does not establish that all {total('text_stat_cells')} locator candidates "
        "are relevant.",
        "R023, R029, and R046 have already been audited through JATS; R024 remains the only P1 "
        "primary record in this set without either audited JATS or a local PDF.",
        "",
        "## Per-Record Counts",
        "",
        "| record | PDF | line tables | line stat cells | text locator candidates | classification |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['record_id']} | {row['pdf_status']} | {row['line_tables'] or 0} | "
            f"{row['line_stat_cells'] or 0} | {row['text_stat_cells'] or 0} | "
            f"{row['classification']} |"
        )
    lines.extend([
        "",
        "## Reproduce",
        "",
        "```bash",
        "python scripts/audit_bovine_pdf_tables.py --max-items 14",
        "```",
        "",
        "The TSV report binds each available PDF to SHA-256. Extracted page text and table "
        "content remain local and are not committed.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/literature/bovine_pdf_table_source_manifest.tsv"),
    )
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument(
        "--corpus-manifest", type=Path,
        default=Path("data/literature/bovine_corpus_manifest.tsv"),
    )
    parser.add_argument(
        "--report", type=Path,
        default=Path("data/literature/bovine_pdf_table_audit.tsv"),
    )
    parser.add_argument(
        "--summary", type=Path,
        default=Path("docs/PDF_TABLE_OFFRAMP_AUDIT.md"),
    )
    parser.add_argument("--max-items", type=int, default=20)
    args = parser.parse_args()

    sources = _read_sources(args.manifest)
    _validate_sources_against_corpus(sources, args.corpus_manifest)
    if args.max_items <= 0 or len(sources) > args.max_items:
        raise ValueError(f"refusing {len(sources)} items with --max-items={args.max_items}")
    report = []
    for source in sources:
        base = {"record_id": source["record_id"], "paper_id": source["paper_id"]}
        paper_dir = args.papers_dir / source["paper_id"]
        pdfs = sorted(paper_dir.glob("*.pdf")) if paper_dir.exists() else []
        if len(pdfs) != 1:
            status = "missing" if not pdfs else "ambiguous"
            report.append({
                **base, "pdf_status": status, "pdf_path": "", "pdf_sha256": "",
                "pages": "", "line_tables": "", "line_cells": "",
                "line_stat_cells": "", "text_regions": "", "text_cells": "",
                "text_stat_cells": "", "classification": "not_audited",
                "error": f"found {len(pdfs)} PDF files",
            })
            print(f"! {source['record_id']}: {status} ({len(pdfs)} PDFs)")
            continue
        pdf = pdfs[0]
        try:
            result = audit_pdf_tables(pdf)
            report.append({
                **base,
                "pdf_status": "audited",
                "pdf_path": pdf.as_posix(),
                "pdf_sha256": result.pdf_sha256,
                "pages": result.pages,
                "line_tables": result.lines.regions,
                "line_cells": result.lines.cells,
                "line_stat_cells": result.lines.stat_candidate_cells,
                "text_regions": result.text.regions,
                "text_cells": result.text.cells,
                "text_stat_cells": result.text.stat_candidate_cells,
                "classification": result.classification,
                "error": "-",
            })
            print(
                f"+ {source['record_id']}: line_stats={result.lines.stat_candidate_cells}, "
                f"text_stats={result.text.stat_candidate_cells}"
            )
        except PDFTableAuditError as exc:
            report.append({
                **base, "pdf_status": "failed", "pdf_path": pdf.as_posix(),
                "pdf_sha256": "", "pages": "", "line_tables": "", "line_cells": "",
                "line_stat_cells": "", "text_regions": "", "text_cells": "",
                "text_stat_cells": "", "classification": "not_audited", "error": str(exc),
            })
            print(f"! {source['record_id']}: {exc}")
    _write_report(report, args.report)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(_summary_markdown(report), encoding="utf-8")
    line_stats = sum(int(row["line_stat_cells"] or 0) for row in report)
    text_stats = sum(int(row["text_stat_cells"] or 0) for row in report)
    print(f"+ wrote {args.report}")
    print(f"+ wrote {args.summary}")
    print(f"structured_stat_cells={line_stats}; layout_text_candidates={text_stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
