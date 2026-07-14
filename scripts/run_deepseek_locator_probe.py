#!/usr/bin/env python3
"""Run a bounded, repeated DeepSeek quantitative-block locator probe."""

from __future__ import annotations

import argparse
from pathlib import Path

from cultivate_agent.evaluate.deepseek_locator_probe import (
    deepseek_caller,
    load_locator_silver,
    report_markdown,
    run_locator_probe,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/evaluation/gold/quantitative-pilot-v1/manifest.json"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--max-requests", type=int, default=6)
    parser.add_argument("--max-total-tokens", type=int, default=12000)
    parser.add_argument("--max-output-tokens", type=int, default=200)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    items = load_locator_silver(args.manifest, repo_root=args.repo_root.resolve())
    result = run_locator_probe(
        items, checkpoint_dir=args.checkpoint_dir, model=args.model,
        repeats=args.repeats, batch_size=args.batch_size, max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens, max_output_tokens=args.max_output_tokens,
        caller=deepseek_caller(args.model, args.timeout),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        report_markdown(result, model=args.model, max_requests=args.max_requests),
        encoding="utf-8",
    )
    print(f"+ wrote {args.report}")
    print(
        f"gate_pass={result.gate_pass}; recalls={result.repeat_recalls}; "
        f"precision={result.repeat_precisions}; consistency={result.selection_consistency}; "
        f"tokens={result.total_tokens}"
    )
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
