#!/usr/bin/env python3
"""Acquire DOI- and license-verified Europe PMC JATS from an explicit manifest."""

from __future__ import annotations

import argparse
import csv
import os
import re
import tempfile
from pathlib import Path

from cultivate_agent.ingest import EuropePMCError, acquire_europe_pmc_jats
from cultivate_agent.schema import structured_paper_from_grobid_tei_path


REPORT_FIELDS = [
    "record_id", "paper_id", "doi", "pmcid", "status", "license",
    "license_url", "source_url", "source_sha256", "table_count", "cell_count",
    "stat_candidate_cells", "error",
]
_STAT_RE = re.compile(
    r"(?:±|\+/-|\b(?:SD|SEM|standard deviation|standard error)\b|\bn\s*=)",
    re.I,
)


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"record_id", "paper_id", "doi", "pmcid", "expected_license"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"source manifest missing columns: {', '.join(sorted(missing))}")
    if len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("source manifest contains duplicate record_id values")
    return rows


def _write_report(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/literature/bovine_jats_source_manifest.tsv"),
    )
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument(
        "--report", type=Path,
        default=Path("data/literature/bovine_jats_acquisition.tsv"),
    )
    parser.add_argument("--record-id", action="append", default=[])
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    rows = _read_manifest(args.manifest)
    if args.record_id:
        requested = set(args.record_id)
        rows = [row for row in rows if row["record_id"] in requested]
        missing_ids = requested - {row["record_id"] for row in rows}
        if missing_ids:
            raise ValueError(f"unknown record IDs: {', '.join(sorted(missing_ids))}")
    if args.max_items <= 0 or len(rows) > args.max_items:
        raise ValueError(f"refusing {len(rows)} items with --max-items={args.max_items}")

    report = []
    failed = False
    for row in rows:
        base = {key: row[key] for key in ("record_id", "paper_id", "doi", "pmcid")}
        try:
            paper_dir = args.papers_dir / row["paper_id"]
            acquisition, status = acquire_europe_pmc_jats(
                paper_dir,
                pmcid=row["pmcid"],
                expected_doi=row["doi"],
                expected_license=row["expected_license"],
                timeout=args.timeout,
                force=args.force,
            )
            paper = structured_paper_from_grobid_tei_path(row["record_id"], paper_dir / "fulltext.xml")
            stat_candidates = sum(
                1 for table in paper.tables for cell in table.cells if _STAT_RE.search(cell.text)
            )
            report.append({
                **base,
                "status": status,
                "license": acquisition.license_name,
                "license_url": acquisition.license_url,
                "source_url": acquisition.source_url,
                "source_sha256": acquisition.source_sha256,
                "table_count": acquisition.table_count,
                "cell_count": acquisition.cell_count,
                "stat_candidate_cells": stat_candidates,
                "error": "",
            })
            print(f"+ {row['record_id']}: {status}, tables={acquisition.table_count}")
        except Exception as exc:
            failed = True
            report.append({
                **base,
                "status": "failed",
                "license": "",
                "license_url": "",
                "source_url": "",
                "source_sha256": "",
                "table_count": "",
                "cell_count": "",
                "stat_candidate_cells": "",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"! {row['record_id']}: {type(exc).__name__}: {exc}")
    _write_report(report, args.report)
    print(f"+ wrote {args.report}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
