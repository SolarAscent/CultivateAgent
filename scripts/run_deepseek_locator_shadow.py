#!/usr/bin/env python3
"""Run the gated DeepSeek locator on a bounded unlabeled shadow set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cultivate_agent.evaluate.deepseek_locator_probe import (
    deepseek_caller,
    load_shadow_pool,
    run_shadow_localization,
    shadow_manifest,
    validate_shadow_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/evaluation/gold/quantitative-pilot-v1/manifest.json"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--records", nargs="+", default=["R018", "R045"])
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--max-requests", type=int, default=6)
    parser.add_argument("--max-total-tokens", type=int, default=45000)
    parser.add_argument("--max-output-tokens", type=int, default=250)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    items = load_shadow_pool(
        args.manifest, repo_root=args.repo_root.resolve(), record_ids=args.records
    )
    result = run_shadow_localization(
        items, checkpoint_dir=args.checkpoint_dir, model=args.model,
        repeats=args.repeats, batch_size=args.batch_size, max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens, max_output_tokens=args.max_output_tokens,
        caller=deepseek_caller(args.model, args.timeout),
    )
    payload = shadow_manifest(result, model=args.model)
    validation_issues = validate_shadow_manifest(payload, items)
    if validation_issues:
        raise RuntimeError("; ".join(validation_issues))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"gate_pass={result.gate_pass}; items={len(items)}; selected={len(result.selected_ids)}; "
        f"consistency={result.selection_consistency}; tokens={result.total_tokens}"
    )
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
