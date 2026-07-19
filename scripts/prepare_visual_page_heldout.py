#!/usr/bin/env python3
"""Freeze a source-disjoint PDF visual-page held-out set before API evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from cultivate_agent.evaluate.deepseek_visual_page_probe import (
    build_pdf_visual_heldout_manifest,
)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", nargs="+", default=["R016", "R021", "R022"])
    parser.add_argument(
        "--corpus", type=Path,
        default=Path("data/literature/bovine_corpus_manifest.tsv"),
    )
    parser.add_argument(
        "--pdf-audit", type=Path,
        default=Path("data/literature/bovine_pdf_table_audit.tsv"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_pdf_visual_heldout_manifest(
        args.records,
        corpus_rows=_read(args.corpus),
        pdf_audits=_read(args.pdf_audit),
        repo_root=args.repo_root.resolve(),
    )
    _atomic_json(args.out, payload)
    print(
        f"+ wrote {args.out}; sources={len(payload['sources'])}; "
        f"candidate_pages={len(payload['candidates'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
