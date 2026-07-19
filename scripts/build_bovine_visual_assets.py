#!/usr/bin/env python3
"""Extract and audit source-bound visual assets for the deterministic bovine page baseline."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from cultivate_agent.evidence.visual_asset_readiness import extract_visual_asset_readiness


SOURCE_FIELDS = [
    "record_id", "paper_id", "doi", "pdf_path", "pdf_sha256", "pdf_pages", "license",
    "license_evidence", "jats_status", "jats_source_sha256", "broad_candidate_pages",
    "strict_candidate_pages", "extracted_assets", "status",
]
ASSET_FIELDS = [
    "record_id", "doi", "pdf_path", "pdf_sha256", "pdf_page", "candidate_class",
    "caption_block_indexes", "caption_block_sha256", "caption_bboxes", "source_kind",
    "image_index", "image_ext", "image_width", "image_height", "image_bytes",
    "image_color_count", "image_sha256", "image_rects", "local_asset_path", "jats_figure_id",
    "jats_figure_label", "jats_graphic_hrefs", "status",
]
SUPPLEMENT_FIELDS = [
    "record_id", "doi", "jats_source_sha256", "supplement_id", "href", "local_path",
    "local_sha256", "status",
]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _atomic_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", nargs="+", default=["R016", "R021", "R022"])
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--heldout", type=Path,
        default=Path("data/evaluation/gold/visual-page-heldout-v1/manifest.json"),
    )
    parser.add_argument(
        "--asset-dir", type=Path, default=Path("data/visual_assets/bovine-baseline-v1"),
    )
    parser.add_argument(
        "--source-out", type=Path,
        default=Path("data/literature/bovine_visual_asset_source_audit.tsv"),
    )
    parser.add_argument(
        "--asset-out", type=Path,
        default=Path("data/literature/bovine_visual_asset_inventory.tsv"),
    )
    parser.add_argument(
        "--supplement-out", type=Path,
        default=Path("data/literature/bovine_supplement_asset_inventory.tsv"),
    )
    parser.add_argument(
        "--report", type=Path, default=Path("docs/BOVINE_VISUAL_ASSET_READINESS.md"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    heldout = json.loads(args.heldout.read_text(encoding="utf-8"))
    acquisitions = _read(Path("data/literature/bovine_jats_acquisition.tsv"))
    extra = Path("data/literature/bovine_jats_acquisition_R052_R056.tsv")
    if extra.is_file():
        acquisitions.extend(_read(extra))
    sources, assets, supplements = extract_visual_asset_readiness(
        args.records,
        corpus_rows=_read(Path("data/literature/bovine_corpus_manifest.tsv")),
        pdf_audits=_read(Path("data/literature/bovine_pdf_table_audit.tsv")),
        heldout=heldout,
        jats_sources=_read(Path("data/literature/bovine_jats_source_manifest.tsv")),
        jats_acquisitions=acquisitions,
        repo_root=root,
        output_dir=root / args.asset_dir,
    )
    _atomic_tsv(args.source_out, SOURCE_FIELDS, sources)
    _atomic_tsv(args.asset_out, ASSET_FIELDS, assets)
    _atomic_tsv(args.supplement_out, SUPPLEMENT_FIELDS, supplements)
    classes = Counter(str(row["candidate_class"]) for row in assets)
    mapped = sum(bool(row["jats_figure_id"]) for row in assets)
    nonblank = sum(row["status"] == "ready_for_visual_review" for row in assets)
    local_supplements = sum(row["status"] == "available_local" for row in supplements)
    report = f"""# Bovine Visual Asset Readiness

## Scope And Boundary

- Source-verified PDFs: {len(sources)}.
- Deterministic field-aware candidate pages: {sum(int(row['broad_candidate_pages']) for row in sources)}.
- Extracted visual assets: {len(assets)}.
- This stage extracts embedded images and records source/layout hashes. It does
  not interpret plots, transcribe scientific numbers, assign treatment/control
  roles, or approve an evidence tier.

## Result

- Strict group-statistics visual candidates: {classes['strict_group_stats_visual_candidate']}.
- Broader visual candidates: {classes['broad_visual_candidate']}.
- Assets mapped to verified JATS figure IDs: {mapped}/{len(assets)}.
- Nonblank pixel check: {nonblank}/{len(assets)} passed.
- Unique JATS supplement references: {len(supplements)}; available locally: {local_supplements}.
- All {nonblank} extracted nonblank assets are ready for bounded visual review. The
  strict candidates should be reviewed first; broader candidates are not
  assumed to contain complete mean-dispersion-n structures.

## Safety And Availability

- Image files remain generated local assets under `{args.asset_dir}`; the
  committed inventory contains paths, hashes, dimensions, and locators only.
- R016 and R022 licenses and JATS hashes come from the verified acquisition
  registry. R021's CC BY status is verified from its hash-bound PDF text.
- Missing supplement files remain `referenced_not_local`; a JATS href alone is
  not reported as a locally available asset.

## Reproduction

```bash
python scripts/build_bovine_visual_assets.py
```
"""
    _atomic_text(args.report, report)
    print(
        f"+ sources={len(sources)} pages={sum(int(row['broad_candidate_pages']) for row in sources)} "
        f"assets={len(assets)} strict={classes['strict_group_stats_visual_candidate']} "
        f"jats_mapped={mapped} supplements={len(supplements)}/{local_supplements}_local"
    )
    print(f"+ wrote {args.source_out}, {args.asset_out}, {args.supplement_out}, {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
