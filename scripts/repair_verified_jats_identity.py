#!/usr/bin/env python3
"""Repair one paper's metadata from canonical, hash-bound local sources."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cultivate_agent.ingest.identity_repair import repair_paper_identity_from_verified_jats


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _one(rows: list[dict[str, str]], record_id: str, label: str) -> dict[str, str]:
    matches = [row for row in rows if row.get("record_id") == record_id]
    if len(matches) != 1:
        raise ValueError(f"{record_id}: expected one {label} row, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record_id")
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument("--quarantine-dir", type=Path, default=Path("data/quarantine/identity-repair"))
    parser.add_argument("--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv"))
    parser.add_argument(
        "--sources", type=Path,
        default=Path("data/literature/bovine_jats_source_manifest.tsv"),
    )
    parser.add_argument(
        "--acquisition", type=Path,
        default=Path("data/literature/bovine_jats_acquisition.tsv"),
    )
    parser.add_argument("--pdf-audit", type=Path, default=Path("data/literature/bovine_pdf_table_audit.tsv"))
    args = parser.parse_args()

    canonical = _one(_rows(args.corpus), args.record_id, "corpus")
    source = _one(_rows(args.sources), args.record_id, "source")
    acquisition = _one(_rows(args.acquisition), args.record_id, "acquisition")
    pdf_rows = [row for row in _rows(args.pdf_audit) if row.get("record_id") == args.record_id]
    pdf_audit = pdf_rows[0] if len(pdf_rows) == 1 else None
    result = repair_paper_identity_from_verified_jats(
        record_id=args.record_id,
        paper_dir=args.papers_dir / source["paper_id"],
        canonical=canonical,
        source=source,
        acquisition=acquisition,
        quarantine_root=args.quarantine_dir,
        pdf_audit=pdf_audit,
    )
    print(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
