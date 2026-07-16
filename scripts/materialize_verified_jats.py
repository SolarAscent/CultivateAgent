#!/usr/bin/env python3
"""Materialize canonical metadata/plain text from a verified local JATS subset."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path

from cultivate_agent.ingest import materialize_verified_jats


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv"))
    parser.add_argument("--sources", type=Path, default=Path("data/literature/bovine_jats_source_manifest.tsv"))
    parser.add_argument(
        "--acquisition", type=Path,
        default=Path("data/literature/bovine_jats_acquisition_R052_R056.tsv"),
    )
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument("--record-id", action="append", dest="record_ids")
    parser.add_argument(
        "--report", type=Path,
        default=Path("data/literature/bovine_jats_materialization_R052_R056.tsv"),
    )
    args = parser.parse_args()
    acquisition_rows = _read(args.acquisition)
    record_ids = args.record_ids or [row["record_id"] for row in acquisition_rows]
    results = materialize_verified_jats(
        corpus_rows=_read(args.corpus), source_rows=_read(args.sources),
        acquisition_rows=acquisition_rows, papers_dir=args.papers_dir.resolve(),
        record_ids=record_ids,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "record_id", "paper_id", "source_sha256", "fulltext_sha256", "fulltext_chars",
        "sections", "tables", "figures", "has_local_pdf", "status",
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=args.report.parent,
        prefix=f".{args.report.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for result in results:
            row = {name: getattr(result, name) for name in columns[:-1]}
            row["has_local_pdf"] = "yes" if result.has_local_pdf else "no"
            row["status"] = "materialized_from_verified_jats"
            writer.writerow(row)
    os.replace(temporary, args.report)
    print(f"+ materialized {len(results)} verified JATS records; wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
