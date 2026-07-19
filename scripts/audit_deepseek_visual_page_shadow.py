#!/usr/bin/env python3
"""Audit DeepSeek visual-page shadow recall against a deterministic broad sensitivity set."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from cultivate_agent.evaluate.deepseek_visual_page_probe import (
    audit_pdf_visual_shadow,
    validate_pdf_visual_shadow_audit,
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
    parser.add_argument("--heldout", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = audit_pdf_visual_shadow(
        args.heldout, args.result, repo_root=args.repo_root.resolve()
    )
    issues = validate_pdf_visual_shadow_audit(payload)
    if issues:
        raise ValueError("; ".join(issues))
    _atomic_json(args.out, payload)
    print(
        f"+ wrote {args.out}; status={payload['status']}; "
        f"strict_recall={payload['strict_repeat_recalls']}; "
        f"broad_recall={payload['broad_recall']}; "
        f"model_vs_baseline={payload['model_selected_pages']}/{payload['broad_baseline_pages']}"
    )
    return 0 if payload["production_gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
