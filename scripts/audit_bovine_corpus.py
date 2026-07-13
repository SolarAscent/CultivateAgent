#!/usr/bin/env python3
"""Audit the bovine corpus manifest against pre-wet-lab Gate 1."""

from __future__ import annotations

import argparse
from pathlib import Path

from cultivate_agent.evaluate.corpus_gate import (
    audit_corpus_manifest,
    corpus_gate_markdown,
    write_corpus_issues_tsv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv"))
    parser.add_argument("--out", type=Path, default=Path("docs/BOVINE_CORPUS_GATE1_AUDIT.md"))
    parser.add_argument("--issues", type=Path, default=Path("data/literature/bovine_corpus_gate1_issues.tsv"))
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    result = audit_corpus_manifest(args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(corpus_gate_markdown(result), encoding="utf-8")
    write_corpus_issues_tsv(result.issues, args.issues)
    print(f"+ wrote {args.out}")
    print(f"+ wrote {args.issues}")
    print(f"Gate 1: {result.gate_status}")
    return 1 if args.require_pass and result.gate_status != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
