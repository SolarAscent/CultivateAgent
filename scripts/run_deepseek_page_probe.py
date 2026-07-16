#!/usr/bin/env python3
"""Run a bounded repeated page-candidate capability probe on existing gold."""

from __future__ import annotations

import argparse
from pathlib import Path

from cultivate_agent.evaluate.deepseek_locator_probe import (
    deepseek_caller, report_markdown, run_locator_probe,
)
from cultivate_agent.evaluate.deepseek_page_probe import (
    PROMPT_VERSION, build_page_prompt, load_page_silver,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-requests", type=int, default=12)
    parser.add_argument("--max-total-tokens", type=int, default=30000)
    parser.add_argument("--max-output-tokens", type=int, default=160)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-wall-seconds", type=float, default=600)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    items = load_page_silver(args.manifest, repo_root=args.repo_root.resolve())
    result = run_locator_probe(
        items, checkpoint_dir=args.checkpoint_dir, model=args.model,
        repeats=args.repeats, batch_size=args.batch_size, max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens, max_output_tokens=args.max_output_tokens,
        caller=deepseek_caller(args.model, args.timeout), prompt_builder=build_page_prompt,
        prompt_version=PROMPT_VERSION, max_wall_seconds=args.max_wall_seconds,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        report_markdown(
            result, model=args.model, max_requests=args.max_requests,
            title="DeepSeek Page-Candidate Localization Probe",
            prompt_version=PROMPT_VERSION,
            precision_label="Silver precision by repeat (decoys unadjudicated; not gated)",
        ),
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
