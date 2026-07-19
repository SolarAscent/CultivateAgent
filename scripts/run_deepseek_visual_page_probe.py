#!/usr/bin/env python3
"""Run the bounded DeepSeek visual-result page-pointer capability gate."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from cultivate_agent.evaluate.deepseek_locator_probe import deepseek_caller, run_locator_probe
from cultivate_agent.evaluate.deepseek_visual_page_probe import (
    PROMPT_VERSION,
    build_visual_page_prompt,
    deployment_gate_pass,
    load_visual_page_silver,
    result_manifest,
    selected_fractions,
    validate_result_manifest,
)


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
    parser.add_argument("--silver", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-requests", type=int, default=15)
    parser.add_argument("--max-total-tokens", type=int, default=30000)
    parser.add_argument("--max-output-tokens", type=int, default=160)
    parser.add_argument("--max-wall-seconds", type=float, default=600)
    parser.add_argument("--max-selected-fraction", type=float, default=0.60)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    selector_version = json.loads(args.silver.read_text(encoding="utf-8"))["selector_version"]
    items = load_visual_page_silver(args.silver, repo_root=args.repo_root.resolve())
    result = run_locator_probe(
        items,
        checkpoint_dir=args.checkpoint_dir,
        model=args.model,
        repeats=args.repeats,
        batch_size=args.batch_size,
        max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens,
        max_output_tokens=args.max_output_tokens,
        caller=deepseek_caller(args.model, args.timeout),
        prompt_builder=build_visual_page_prompt,
        prompt_version=PROMPT_VERSION,
        max_wall_seconds=args.max_wall_seconds,
    )
    payload = result_manifest(
        result, items, model=args.model,
        max_selected_fraction=args.max_selected_fraction,
        selector_version=selector_version,
    )
    issues = validate_result_manifest(payload, items, selector_version=selector_version)
    if issues:
        raise ValueError("; ".join(issues))
    _atomic_json(args.out, payload)
    passed = deployment_gate_pass(result, max_selected_fraction=args.max_selected_fraction)
    print(
        f"+ wrote {args.out}; pass={passed}; recalls={result.repeat_recalls}; "
        f"selected_fractions={selected_fractions(result)}; "
        f"consistency={result.selection_consistency}; tokens={result.total_tokens}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
