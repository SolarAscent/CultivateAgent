#!/usr/bin/env python3
"""Run the frozen DeepSeek metadata-linkage capability canary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cultivate_agent.evaluate.deepseek_locator_probe import deepseek_caller
from cultivate_agent.evaluate.deepseek_metadata_probe import (
    load_metadata_canary,
    manifest_payload,
    report_markdown,
    run_metadata_probe,
    validate_manifest_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec", type=Path,
        default=Path("data/evaluation/gold/metadata-linkage-canary-v1/spec.tsv"),
    )
    parser.add_argument(
        "--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv")
    )
    parser.add_argument("--zotero-csv", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-requests", type=int, default=9)
    parser.add_argument("--max-total-tokens", type=int, default=15000)
    parser.add_argument("--max-output-tokens", type=int, default=160)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--prior-invalid-requests", type=int, default=0,
        help="record earlier implementation calls excluded from valid-run metrics",
    )
    args = parser.parse_args()

    items = load_metadata_canary(
        args.spec, corpus_manifest_path=args.corpus, zotero_csv_path=args.zotero_csv
    )
    result = run_metadata_probe(
        items, checkpoint_dir=args.checkpoint_dir, model=args.model,
        repeats=args.repeats, batch_size=args.batch_size, max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens, max_output_tokens=args.max_output_tokens,
        caller=deepseek_caller(args.model, args.timeout),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        report_markdown(
            result, model=args.model, max_requests=args.max_requests,
            max_total_tokens=args.max_total_tokens,
            prior_invalid_requests=args.prior_invalid_requests,
        ),
        encoding="utf-8",
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest_payload(
        result, model=args.model,
        prior_invalid_requests=args.prior_invalid_requests,
    )
    manifest_issues = validate_manifest_payload(payload, items)
    if manifest_issues:
        raise ValueError("invalid metadata-probe manifest: " + "; ".join(manifest_issues))
    args.manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"+ wrote {args.report}")
    print(f"+ wrote {args.manifest}")
    print(
        f"gate_pass={result.gate_pass}; recalls={result.repeat_recalls}; "
        f"precisions={result.repeat_precisions}; consistency={result.selection_consistency}; "
        f"tokens={result.total_tokens}"
    )
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
