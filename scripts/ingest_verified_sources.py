#!/usr/bin/env python3
"""Ingest identity-verified local PDFs with exact bibliographic metadata."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from cultivate_agent.ingest import ingest_paper
from cultivate_agent.schema import PaperRef, slugify


def ingest_verified_sources(
    verified_sources: Path,
    *,
    papers_dir: Path,
    repo_root: Path,
) -> list[str]:
    with verified_sources.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"record_id", "title", "year", "doi", "pdf_path", "pdf_sha256", "status"}
    if not rows or required - set(rows[0]):
        raise ValueError("verified source table is missing required columns")

    ingested: list[str] = []
    for row in rows:
        if row["status"] != "identity_license_verified":
            raise ValueError(f"{row['record_id']} is not identity/license verified")
        pdf_path = (repo_root / row["pdf_path"]).resolve()
        if not pdf_path.is_file():
            raise FileNotFoundError(pdf_path)
        actual_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        if actual_hash != row["pdf_sha256"]:
            raise ValueError(f"PDF hash mismatch for {row['record_id']}")

        paper_id = slugify(row["title"])
        if pdf_path.parent != (papers_dir / paper_id).resolve():
            raise ValueError(f"unexpected paper directory for {row['record_id']}")
        result = ingest_paper(
            PaperRef(
                paper_id=paper_id,
                title=row["title"],
                year=int(row["year"]),
                doi=row["doi"].lower(),
                url=f"https://doi.org/{row['doi'].lower()}",
                pdf_path=row["pdf_path"],
            ),
            papers_dir,
            extract_page_images=False,
            extract_figures=False,
            extract_tables=False,
            force=True,
        )
        if not result.ok:
            raise ValueError(f"full-text extraction failed for {row['record_id']}")
        ingested.append(row["record_id"])
    return ingested


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-sources", type=Path, required=True)
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    ids = ingest_verified_sources(
        args.verified_sources,
        papers_dir=args.papers_dir.resolve(),
        repo_root=args.repo_root.resolve(),
    )
    print(f"+ ingested {len(ids)} verified sources: {','.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
