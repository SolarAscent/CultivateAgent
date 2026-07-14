#!/usr/bin/env python3
"""Create, validate, and compare the bounded quantitative review pilot."""

from __future__ import annotations

import argparse
from pathlib import Path

from cultivate_agent.evaluate.quantitative_review import (
    compare_quantitative_reviews,
    comparison_markdown,
    copy_working_reviews,
    create_quantitative_review,
    render_candidate_crops,
    validate_quantitative_review,
)


DEFAULT_DIR = Path("data/evaluation/gold/quantitative-pilot-v1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--source-spec", type=Path, default=DEFAULT_DIR / "source_spec.tsv")
    create.add_argument(
        "--corpus-manifest", type=Path,
        default=Path("data/literature/bovine_corpus_manifest.tsv"),
    )
    create.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    create.add_argument("--manifest", type=Path, default=DEFAULT_DIR / "manifest.json")
    create.add_argument("--template", type=Path, default=DEFAULT_DIR / "reviewer_blank.tsv")
    create.add_argument("--version", default="quantitative-pilot-v1")
    create.add_argument("--repo-root", type=Path, default=Path.cwd())
    create.add_argument("--working-dir", type=Path)
    create.add_argument("--render-crops", action="store_true")

    validate = sub.add_parser("validate")
    validate.add_argument("--manifest", type=Path, default=DEFAULT_DIR / "manifest.json")
    validate.add_argument("--reviewer", type=Path, required=True)
    validate.add_argument("--repo-root", type=Path, default=Path.cwd())
    validate.add_argument("--require-complete", action="store_true")

    compare = sub.add_parser("compare")
    compare.add_argument("--manifest", type=Path, default=DEFAULT_DIR / "manifest.json")
    compare.add_argument("--reviewer-a", type=Path, required=True)
    compare.add_argument("--reviewer-b", type=Path, required=True)
    compare.add_argument("--repo-root", type=Path, default=Path.cwd())
    compare.add_argument("--out", type=Path)
    render = sub.add_parser("render")
    render.add_argument("--manifest", type=Path, default=DEFAULT_DIR / "manifest.json")
    render.add_argument("--repo-root", type=Path, default=Path.cwd())
    render.add_argument(
        "--out-dir", type=Path,
        default=Path("data/evaluation/reviews/quantitative-pilot-v1/crops"),
    )
    args = parser.parse_args()

    if args.command == "create":
        manifest, template = create_quantitative_review(
            args.source_spec,
            corpus_manifest_path=args.corpus_manifest,
            papers_dir=args.papers_dir,
            repo_root=args.repo_root.resolve(),
            benchmark_version=args.version,
            manifest_path=args.manifest,
            reviewer_template_path=args.template,
        )
        print(f"+ wrote {manifest}")
        print(f"+ wrote {template}")
        if args.working_dir:
            left, right = copy_working_reviews(template, args.working_dir)
            print(f"+ wrote {left}")
            print(f"+ wrote {right}")
            if args.render_crops:
                crops = render_candidate_crops(
                    manifest,
                    repo_root=args.repo_root.resolve(),
                    output_dir=args.working_dir / "crops",
                )
                print(f"+ rendered {len(crops)} local review crops")
        return 0

    if args.command == "validate":
        result = validate_quantitative_review(
            args.manifest, args.reviewer, repo_root=args.repo_root.resolve()
        )
        print(
            f"rows={result.rows}/{result.expected_rows}; completed={result.completed}; "
            f"issues={len(result.issues)}; complete={result.complete}"
        )
        for issue in result.issues:
            print(f"! {issue}")
        return 1 if result.issues or (args.require_complete and not result.complete) else 0

    if args.command == "render":
        crops = render_candidate_crops(
            args.manifest,
            repo_root=args.repo_root.resolve(),
            output_dir=args.out_dir,
        )
        print(f"+ rendered {len(crops)} local review crops")
        return 0

    result = compare_quantitative_reviews(
        args.manifest,
        args.reviewer_a,
        args.reviewer_b,
        repo_root=args.repo_root.resolve(),
    )
    report = comparison_markdown(result)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"+ wrote {args.out}")
    else:
        print(report, end="")
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
