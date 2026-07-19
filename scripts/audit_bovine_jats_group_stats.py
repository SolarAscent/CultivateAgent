#!/usr/bin/env python3
"""Audit verified bovine JATS tables for pointer-ready group statistics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
from collections import Counter
from pathlib import Path

from cultivate_agent.evidence.table_readiness import (
    audit_verified_jats_group_stats,
    merge_acquisition_rows,
)


SOURCE_FIELDS = [
    "record_id", "paper_id", "doi", "source_sha256", "table_count", "cell_count",
    "structural_candidate_tables", "incomplete_tables", "excluded_statistical_tables",
    "status",
]
TABLE_FIELDS = [
    "record_id", "paper_id", "table_id", "source_table_id", "source_sha256",
    "row_count", "column_count", "cell_count", "numeric_cell_count",
    "combined_stat_cell_ids", "sample_size_cell_ids", "sample_size_context_ids",
    "dispersion_context_ids", "dispersion_kind", "response_context",
    "exclusion_reason", "status",
]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _atomic_tsv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument("--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv"))
    parser.add_argument(
        "--sources", type=Path,
        default=Path("data/literature/bovine_jats_source_manifest.tsv"),
    )
    parser.add_argument(
        "--acquisition", type=Path, action="append",
        default=None,
    )
    parser.add_argument(
        "--source-out", type=Path,
        default=Path("data/literature/bovine_jats_group_stats_source_audit.tsv"),
    )
    parser.add_argument(
        "--table-out", type=Path,
        default=Path("data/literature/bovine_jats_group_stats_table_audit.tsv"),
    )
    parser.add_argument(
        "--report", type=Path,
        default=Path("docs/BOVINE_JATS_GROUP_STATS_AUDIT.md"),
    )
    args = parser.parse_args()

    acquisition_paths = args.acquisition or [
        Path("data/literature/bovine_jats_acquisition.tsv"),
        Path("data/literature/bovine_jats_acquisition_R052_R056.tsv"),
    ]
    acquisitions = merge_acquisition_rows(*(_read(path) for path in acquisition_paths))
    source_audits, table_audits = audit_verified_jats_group_stats(
        corpus_rows=_read(args.corpus),
        source_rows=_read(args.sources),
        acquisition_rows=acquisitions,
        papers_dir=args.papers_dir,
    )
    _atomic_tsv(args.source_out, SOURCE_FIELDS, [item.to_row() for item in source_audits])
    _atomic_tsv(args.table_out, TABLE_FIELDS, [item.to_row() for item in table_audits])

    statuses = Counter(item.status for item in table_audits)
    candidates = [item for item in table_audits if item.status == "structural_group_stats_candidate"]
    incomplete = [item for item in table_audits if item.status.startswith("incomplete_")]
    excluded = [item for item in table_audits if item.status == "excluded_non_effect_statistics"]
    source_hash = _sha(args.source_out)
    table_hash = _sha(args.table_out)
    status_rows = "\n".join(
        f"| `{status}` | {count} |" for status, count in sorted(statuses.items())
    ) or "| `none` | 0 |"
    incomplete_rows = "\n".join(
        f"| {item.record_id} | {item.table_id} | `{item.status}` | "
        f"{';'.join(item.dispersion_context_ids) or '-'} | "
        f"{';'.join(item.sample_size_context_ids) or '-'} |"
        for item in incomplete
    ) or "| - | - | - | - | - |"
    excluded_rows = "\n".join(
        f"| {item.record_id} | {item.table_id} | `{item.exclusion_reason}` |"
        for item in excluded
    ) or "| - | - | - |"
    verdict = (
        "`PROCEED_TO_POINTER_REVIEW`" if candidates else "`OFF_RAMP_NO_COMPLETE_TABLE_STRUCTURE`"
    )
    report = f"""# Bovine JATS Group-Statistics Readiness Audit

## Scope And Safety Boundary

- Verified JATS sources: {len(source_audits)}.
- Parsed structured tables: {len(table_audits)}; cells: {sum(x.cell_count for x in table_audits)}.
- This audit emits source/table/cell/footnote pointers and counts only. It does
  not transcribe source numbers, assign treatment/control roles, approve an
  evidence tier, or call an LLM.
- Every source passed canonical DOI/paper-ID, PMCID, license, XML SHA-256, and
  acquisition table/cell-count checks before classification.

## Result

- Structural group-statistics candidates: {len(candidates)}.
- Incomplete statistical tables: {len(incomplete)}.
- Excluded non-effect statistical tables: {len(excluded)}.
- Decision: {verdict}.

| Deterministic status | Tables |
|---|---:|
{status_rows}

The current verified JATS set does not justify a DeepSeek cell-role run unless
the candidate count is nonzero. Tables with dispersion but no table-bound sample
size remain incomplete; composition/resource statistics and model coefficients
cannot be promoted as treatment/control effects. Caption and footnote sample-size
locators are diagnostic only: the frozen pointer schema requires an addressable
table cell for n.

## Incomplete Tables

| Record | Table | Status | Dispersion locators | Sample-size context locators |
|---|---|---|---|---|
{incomplete_rows}

## Excluded Statistical Tables

| Record | Table | Reason |
|---|---|---|
{excluded_rows}

## Reproduction

```bash
python scripts/audit_bovine_jats_group_stats.py
```

- Source audit SHA-256: `{source_hash}`.
- Table audit SHA-256: `{table_hash}`.
- Source and table TSVs contain no source numeric values.
"""
    _atomic_text(args.report, report)
    print(
        f"+ sources={len(source_audits)} tables={len(table_audits)} "
        f"candidates={len(candidates)} incomplete={len(incomplete)} excluded={len(excluded)}"
    )
    print(f"+ wrote {args.source_out}, {args.table_out}, {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
