#!/usr/bin/env python3
"""Create or validate a versioned dual-review A-M gold worksheet."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from cultivate_agent.evaluate.gold_review import (
    create_gold_review,
    create_reviewer_template,
    merge_independent_reviews,
    validate_gold_review,
    validation_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--paper", action="append", required=True, metavar="RECORD_ID=PATH")
    create.add_argument("--version", required=True)
    create.add_argument(
        "--field",
        action="append",
        help="optional A-M field path; repeat to create a controlled pilot subset",
    )
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--worksheet", type=Path, required=True)
    create.add_argument("--reviewer-template", type=Path)
    create.add_argument("--repo-root", type=Path, default=Path.cwd())
    create.add_argument(
        "--corpus-manifest",
        type=Path,
        help="optional TSV supplying authoritative title/year/DOI/URL by record_id",
    )
    validate = sub.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--worksheet", type=Path, required=True)
    validate.add_argument("--repo-root", type=Path, default=Path.cwd())
    validate.add_argument("--out", type=Path)
    validate.add_argument("--require-ready", action="store_true")
    merge = sub.add_parser("merge")
    merge.add_argument("--master", type=Path, required=True)
    merge.add_argument("--reviewer-1", type=Path, required=True)
    merge.add_argument("--reviewer-2", type=Path, required=True)
    merge.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "create":
        selections = []
        for spec in args.paper:
            if "=" not in spec:
                parser.error("--paper must look like RECORD_ID=PATH")
            record_id, raw_path = spec.split("=", 1)
            selections.append((record_id.strip(), Path(raw_path).resolve()))
        bibliography = {}
        if args.corpus_manifest:
            with args.corpus_manifest.open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    bibliography[row["record_id"]] = {
                        key: row.get(key, "") for key in ("title", "year", "doi", "url")
                    }
        manifest, worksheet = create_gold_review(
            selections,
            repo_root=args.repo_root.resolve(),
            benchmark_version=args.version,
            manifest_path=args.manifest,
            worksheet_path=args.worksheet,
            bibliography=bibliography,
            field_paths=args.field,
        )
        print(f"+ wrote {manifest}")
        print(f"+ wrote {worksheet}")
        if args.reviewer_template:
            output = create_reviewer_template(worksheet, args.reviewer_template)
            print(f"+ wrote {output}")
        return 0

    if args.command == "merge":
        output = merge_independent_reviews(
            args.master, args.reviewer_1, args.reviewer_2, args.out
        )
        print(f"+ wrote {output}")
        return 0

    result = validate_gold_review(
        args.manifest,
        args.worksheet,
        repo_root=args.repo_root.resolve(),
    )
    report = validation_markdown(result)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"+ wrote {args.out}")
    else:
        print(report, end="")
    return 1 if args.require_ready and not result.ready else 0


if __name__ == "__main__":
    raise SystemExit(main())
