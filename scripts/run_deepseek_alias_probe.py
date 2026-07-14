#!/usr/bin/env python3
"""Run a bounded, repeated DeepSeek alias-mapping capability probe."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

from cultivate_agent.evaluate.deepseek_alias_probe import (
    load_alias_gold,
    report_markdown,
    run_alias_probe,
)


def _deepseek_caller(model: str, timeout: int):
    from openai import OpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY or OPENAI_API_KEY is required")
    if urlparse(base_url or "").hostname != "api.deepseek.com":
        raise RuntimeError("DeepSeek probe requires base URL https://api.deepseek.com")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def call(prompt: str, max_output_tokens: int):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return strict JSON for bounded ontology candidate mapping."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=max_output_tokens,
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
        )
        usage = response.usage
        return response.choices[0].message.content or "", {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }

    return call


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontology-dir", type=Path, default=Path("config/ontology"))
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--max-aliases", type=int, default=48)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-requests", type=int, default=18)
    parser.add_argument("--max-total-tokens", type=int, default=50000)
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    gold = load_alias_gold(args.ontology_dir, max_aliases=args.max_aliases)
    result = run_alias_probe(
        gold,
        checkpoint_dir=args.checkpoint_dir,
        model=args.model,
        repeats=args.repeats,
        batch_size=args.batch_size,
        max_requests=args.max_requests,
        max_total_tokens=args.max_total_tokens,
        max_output_tokens=args.max_output_tokens,
        caller=_deepseek_caller(args.model, args.timeout),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        report_markdown(result, model=args.model, max_requests=args.max_requests),
        encoding="utf-8",
    )
    print(f"+ wrote {args.report}")
    print(
        f"gate_pass={result.gate_pass}; recalls={result.repeat_recalls}; "
        f"consistency={result.canonical_consistency}; tokens={result.total_tokens}"
    )
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
