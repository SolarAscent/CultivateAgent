#!/usr/bin/env python3
"""Audit the actionable Zotero queue for license-verifiable OA candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
from pathlib import Path

from cultivate_agent.ingest.oa_audit import OUTPUT_FIELDS, AuditResult, audit_rows


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"year", "doi", "title", "why"}
        if reader.fieldnames is None or required - set(reader.fieldnames):
            raise ValueError(f"{path} is missing required columns")
        return list(reader)


def _atomic_tsv(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _report(result: AuditResult, source: Path, output: Path) -> str:
    counts = [f"| `{status}` | {count} |" for status, count in result.status_counts]
    return "\n".join([
        "# Zotero Open-Access Discovery Audit", "",
        "Status: **discovery complete; no full text downloaded**.", "",
        "Europe PMC and Crossref metadata identify candidates only. A candidate is not",
        "authorized for corpus entry until the source DOI, in-document license, and file",
        "structure pass the existing deterministic acquisition checks.", "",
        "## Counts", "", "| Status | Rows |", "|---|---:|", *counts, "",
        "## Integrity", "",
        f"- Input: `{source.as_posix()}`; SHA-256 `{result.source_sha256}`",
        f"- Output: `{output.as_posix()}`; SHA-256 `{hashlib.sha256(output.read_bytes()).hexdigest()}`",
        f"- Requests used in this invocation: {result.requests_used}",
        f"- Checkpoints reused in this invocation: {result.checkpoints_reused}",
        "- Crossref Creative Commons metadata is treated as a lead, not source-level proof.",
        "- Europe PMC rows still require fullTextXML DOI/license/structure verification.", "",
        "## Method Boundary", "",
        "- Europe PMC DOI search and `fullTextXML` are documented by the",
        "  [Europe PMC REST service](https://europepmc.org/RestfulWebService).",
        "- Crossref supports DOI work lookup plus deposited license and full-text-link",
        "  fields through its [REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).",
        "- OpenAlex was not used because its current API requires a key. No provider key",
        "  or language model was needed for this deterministic audit.",
        "- A public metadata record can be incomplete or stale. The 109 candidates are",
        "  ordered acquisition leads, not permission findings and not evidence records.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/literature/zotero_acquire_actionable.tsv"))
    parser.add_argument("--out", type=Path, default=Path("data/literature/zotero_oa_audit.tsv"))
    parser.add_argument("--report", type=Path, default=Path("docs/ZOTERO_OA_AUDIT.md"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("data/checkpoints/zotero_oa_audit"))
    parser.add_argument("--max-requests", type=int, default=410)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--delay-ms", type=int, default=300)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.max_requests < 0 or args.timeout <= 0 or args.delay_ms < 0 or args.workers < 1:
        parser.error("request controls must be non-negative and timeout must be positive")

    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    result = audit_rows(
        _read_rows(args.source), source_sha256=source_hash,
        checkpoint_dir=args.checkpoint_dir, max_requests=args.max_requests,
        timeout=args.timeout, delay_seconds=args.delay_ms / 1000, workers=args.workers,
    )
    _atomic_tsv(args.out, result.rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(_report(result, args.source, args.out), encoding="utf-8")
    print(f"Audited {len(result.rows)} rows; requests={result.requests_used}; reused={result.checkpoints_reused}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
