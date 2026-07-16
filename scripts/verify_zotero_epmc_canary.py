#!/usr/bin/env python3
"""Verify a bounded bovine-focused Europe PMC JATS canary without corpus entry."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
from pathlib import Path

from cultivate_agent.ingest.epmc_canary import (
    REPORT_FIELDS, CanaryResult, validate_canary_manifest, verify_canary,
)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path} lacks a header")
        return list(reader)


def _atomic_tsv(path: Path, rows: tuple[dict[str, str], ...]) -> None:
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


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown(
    result: CanaryResult, *, manifest: Path, audit: Path, report: Path,
) -> str:
    counts = [f"| `{status}` | {count} |" for status, count in result.status_counts]
    verified = [row for row in result.rows if row["status"] == "verified"]
    role_counts: dict[str, int] = {}
    for row in verified:
        role_counts[row["scope_role"]] = role_counts.get(row["scope_role"], 0) + 1
    roles = [f"| `{role}` | {count} |" for role, count in sorted(role_counts.items())]
    return "\n".join([
        "# Europe PMC Bovine JATS Canary", "",
        "Status: **source verification only; no canonical corpus entry or evidence approval**.", "",
        "The canary tests whether selected bovine-focused candidates resolve to the expected",
        "DOI/title, identify as a research article, declare a recognized Creative Commons",
        "license inside JATS, and contain parseable table structure. Biological scope hints",
        "remain unadjudicated.", "",
        "## Verification Result", "", "| Status | Rows |", "|---|---:|", *counts, "",
        "| Selection role | Verified rows |", "|---|---:|", *roles, "",
        f"- Requests used in this invocation: {result.requests_used}",
        f"- Checkpoints reused in this invocation: {result.checkpoints_reused}",
        f"- Total JATS tables: {sum(int(row['table_count']) for row in verified)}",
        f"- Total JATS cells: {sum(int(row['cell_count']) for row in verified)}",
        f"- Cells with statistical notation: {sum(int(row['stat_candidate_cells']) for row in verified)}",
        f"- Table-bearing JATS: {sum(int(row['table_count']) > 0 for row in verified)}/{len(verified)}",
        f"- JATS with statistical-notation cells: "
        f"{sum(int(row['stat_candidate_cells']) > 0 for row in verified)}/{len(verified)}", "",
        "## Integrity", "",
        f"- Canary manifest SHA-256: `{_hash(manifest)}`",
        f"- OA audit SHA-256: `{_hash(audit)}`",
        f"- Verification TSV SHA-256: `{_hash(report)}`",
        "- XML checkpoints are local, ignored artifacts; each committed row retains the",
        "  verified source SHA-256 and contains no source text or numeric result.",
        "- `verified` means acquisition-ready only. It does not mean bovine-scope approved,",
        "  quantitatively extractable, human-reviewed, or wet-lab ready.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/literature/zotero_epmc_bovine_canary.tsv"))
    parser.add_argument("--oa-audit", type=Path, default=Path("data/literature/zotero_oa_audit.tsv"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("data/checkpoints/zotero_epmc_canary"))
    parser.add_argument("--report", type=Path, default=Path("data/literature/zotero_epmc_bovine_canary_verification.tsv"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/ZOTERO_EPMC_BOVINE_CANARY.md"))
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--max-downloads", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if args.max_items <= 0 or args.max_downloads < 0 or args.timeout <= 0:
        parser.error("limits must be non-negative and max-items/timeout must be positive")

    rows = validate_canary_manifest(_read_tsv(args.manifest), _read_tsv(args.oa_audit))
    if len(rows) > args.max_items:
        raise ValueError(f"refusing {len(rows)} items with --max-items={args.max_items}")
    result = verify_canary(
        rows, checkpoint_dir=args.checkpoint_dir,
        max_downloads=args.max_downloads, timeout=args.timeout,
    )
    _atomic_tsv(args.report, result.rows)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(
        _markdown(result, manifest=args.manifest, audit=args.oa_audit, report=args.report),
        encoding="utf-8",
    )
    print(
        f"Verified {sum(row['status'] == 'verified' for row in result.rows)}/{len(result.rows)}; "
        f"requests={result.requests_used}; reused={result.checkpoints_reused}"
    )
    return 0 if all(row["status"] == "verified" for row in result.rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
