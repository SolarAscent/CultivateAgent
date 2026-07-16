#!/usr/bin/env python3
"""Run bounded DeepSeek page-pointer shadow localization on unlabeled PDFs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from cultivate_agent.evaluate.deepseek_locator_probe import deepseek_caller, run_shadow_localization
from cultivate_agent.evaluate.deepseek_page_probe import (
    PROMPT_VERSION, build_page_prompt, load_page_shadow_pool,
    page_shadow_manifest, validate_page_shadow_manifest,
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
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-requests", type=int, default=18)
    parser.add_argument("--max-total-tokens", type=int, default=150000)
    parser.add_argument("--max-output-tokens", type=int, default=180)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-wall-seconds", type=float, default=900)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    items, sources = load_page_shadow_pool(
        _read(args.sources), corpus_rows=_read(args.corpus), repo_root=args.repo_root.resolve(),
    )
    result = run_shadow_localization(
        items, checkpoint_dir=args.checkpoint_dir, model=args.model,
        repeats=args.repeats, batch_size=args.batch_size, max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens, max_output_tokens=args.max_output_tokens,
        caller=deepseek_caller(args.model, args.timeout), prompt_builder=build_page_prompt,
        prompt_version=PROMPT_VERSION, max_wall_seconds=args.max_wall_seconds,
    )
    payload = page_shadow_manifest(result, sources=sources, model=args.model)
    issues = validate_page_shadow_manifest(payload, items=items, sources=sources)
    if issues:
        raise ValueError("; ".join(issues))
    _atomic_json(args.out, payload)
    print(
        f"+ wrote {args.out}; status={payload['status']}; "
        f"pages={payload['selected_pages']}/{payload['input_pages']}; "
        f"excerpt_reduction={payload['excerpt_reduction_fraction']}; "
        f"consistency={payload['selection_consistency']}; tokens={payload['total_tokens']}"
    )
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
