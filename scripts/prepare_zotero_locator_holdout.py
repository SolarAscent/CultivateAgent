#!/usr/bin/env python3
"""Build an identity- and license-verified locator holdout from local Zotero PDFs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import shutil
import tempfile
from pathlib import Path

from cultivate_agent.evaluate.quantitative_review import (
    create_quantitative_review,
    validate_quantitative_review,
)
from cultivate_agent.schema import slugify


DEFAULT_DIR = Path("data/evaluation/gold/zotero-locator-heldout-v1")
SOURCE_FIELDS = [
    "record_id", "title", "year", "doi", "expected_license", "screen_relevance",
    "screen_has_pdf", "screen_model", "screen_run_id", "pdf_path", "pdf_sha256",
    "pages", "zotero_duplicate_paths", "status",
]


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", html.unescape(value).lower()).split())


def _pdf_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _zotero_pdfs(rows: list[dict[str, str]], doi: str) -> list[Path]:
    paths = []
    for row in rows:
        if (row.get("DOI") or "").strip().lower() != doi.lower():
            continue
        for raw_path in (row.get("File Attachments") or "").split(";"):
            path = Path(raw_path.strip())
            if path.is_file() and path.suffix.lower() == ".pdf":
                paths.append(path)
    return sorted(set(paths))


def verify_pdf(
    path: Path,
    *,
    doi: str,
    title: str,
    expected_license: str,
    fitz_module=None,
) -> tuple[str, int]:
    """Verify source identity and an explicit in-document CC BY statement."""
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    document = fitz_module.open(path)
    try:
        text = "\n".join(page.get_text() for page in document)
        metadata_title = str((document.metadata or {}).get("title") or "")
        pages = int(document.page_count)
    finally:
        document.close()
    normalized_text = _normalized(text)
    normalized_title = _normalized(title)
    title_match = normalized_title in normalized_text or normalized_title == _normalized(metadata_title)
    if not title_match:
        raise ValueError(f"title mismatch in {path.name}")
    if doi.lower() not in text.lower():
        raise ValueError(f"DOI mismatch in {path.name}")
    if expected_license != "CC-BY-4.0":
        raise ValueError(f"unsupported expected license {expected_license!r}")
    license_match = (
        "creative commons attribution" in normalized_text
        and "cc by" in normalized_text
        and ("licenses by 4 0" in normalized_text or "license cc by" in normalized_text)
    )
    if not license_match:
        raise ValueError(f"CC BY statement missing in {path.name}")
    return _pdf_hash(path), pages


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
    temporary.replace(path)


def build_holdout(
    *,
    source_spec_path: Path,
    zotero_csv_path: Path,
    relevance_screen_path: Path,
    corpus_manifest_path: Path,
    papers_dir: Path,
    output_dir: Path,
    repo_root: Path,
    fitz_module=None,
) -> tuple[Path, Path]:
    specs = _read_tsv(source_spec_path)
    required = {"record_id", "target_count", "doi", "title", "year", "expected_license"}
    if not specs or required - set(specs[0]):
        raise ValueError("holdout source spec is missing required columns")
    if len({row["record_id"] for row in specs}) != len(specs):
        raise ValueError("holdout source spec contains duplicate record IDs")
    if len({row["doi"].lower() for row in specs}) != len(specs):
        raise ValueError("holdout source spec contains duplicate DOIs")

    screen = {row["doi"].lower(): row for row in _read_tsv(relevance_screen_path) if row["doi"]}
    existing_dois = {
        row["doi"].lower() for row in _read_tsv(corpus_manifest_path)
        if row.get("doi") and row["doi"].upper() != "NONE"
    }
    with zotero_csv_path.open(encoding="utf-8-sig", newline="") as handle:
        zotero_rows = list(csv.DictReader(handle))

    source_rows: list[dict[str, object]] = []
    corpus_rows: list[dict[str, object]] = []
    for spec in specs:
        doi = spec["doi"].lower()
        if doi in existing_dois:
            raise ValueError(f"{doi} already exists in the bovine corpus")
        screened = screen.get(doi)
        if screened is None or screened["relevance"] != "yes" or screened["has_pdf"] != "yes":
            raise ValueError(f"{doi} is not a yes/has_pdf Zotero screen row")
        paths = _zotero_pdfs(zotero_rows, doi)
        if not paths:
            raise ValueError(f"{doi} has no readable local Zotero PDF")
        verified = [
            (path, *verify_pdf(
                path, doi=doi, title=spec["title"],
                expected_license=spec["expected_license"], fitz_module=fitz_module,
            ))
            for path in paths
        ]
        hashes = {pdf_hash for _, pdf_hash, _ in verified}
        if len(hashes) != 1:
            raise ValueError(f"{doi} has conflicting local PDF contents")
        source_path, pdf_hash, pages = verified[0]
        paper_id = slugify(spec["title"])
        destination = papers_dir / paper_id / f"{paper_id}.pdf"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and _pdf_hash(destination) != pdf_hash:
            raise ValueError(f"existing destination PDF differs for {doi}")
        if not destination.exists():
            shutil.copy2(source_path, destination)
        relative_pdf = destination.resolve().relative_to(repo_root.resolve()).as_posix()
        source_rows.append({
            "record_id": spec["record_id"], "title": spec["title"], "year": spec["year"],
            "doi": doi, "expected_license": spec["expected_license"],
            "screen_relevance": screened["relevance"], "screen_has_pdf": screened["has_pdf"],
            "screen_model": screened["model"], "screen_run_id": screened["run_id"],
            "pdf_path": relative_pdf, "pdf_sha256": pdf_hash, "pages": pages,
            "zotero_duplicate_paths": len(paths), "status": "identity_license_verified",
        })
        corpus_rows.append({
            "record_id": spec["record_id"], "title": spec["title"],
            "year": spec["year"], "doi": doi,
        })

    sources_path = output_dir / "verified_sources.tsv"
    corpus_path = output_dir / "source_corpus.tsv"
    _atomic_tsv(sources_path, SOURCE_FIELDS, source_rows)
    _atomic_tsv(corpus_path, ["record_id", "title", "year", "doi"], corpus_rows)
    manifest_path = output_dir / "manifest.json"
    template_path = output_dir / "reviewer_blank.tsv"
    create_quantitative_review(
        source_spec_path,
        corpus_manifest_path=corpus_path,
        papers_dir=papers_dir,
        repo_root=repo_root,
        benchmark_version="zotero-locator-heldout-v1",
        manifest_path=manifest_path,
        reviewer_template_path=template_path,
        fitz_module=fitz_module,
    )
    validation = validate_quantitative_review(
        manifest_path, template_path, repo_root=repo_root, fitz_module=fitz_module
    )
    if validation.issues or validation.rows != validation.expected_rows:
        raise ValueError("generated holdout failed validation: " + "; ".join(validation.issues))
    template_path.unlink()
    return sources_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-spec", type=Path, default=DEFAULT_DIR / "source_spec.tsv")
    parser.add_argument("--zotero-csv", type=Path, required=True)
    parser.add_argument(
        "--relevance-screen", type=Path,
        default=Path("data/literature/zotero_relevance_screen.tsv"),
    )
    parser.add_argument(
        "--corpus-manifest", type=Path,
        default=Path("data/literature/bovine_corpus_manifest.tsv"),
    )
    parser.add_argument("--papers-dir", type=Path, default=Path("data/papers"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    paths = build_holdout(
        source_spec_path=args.source_spec,
        zotero_csv_path=args.zotero_csv,
        relevance_screen_path=args.relevance_screen,
        corpus_manifest_path=args.corpus_manifest,
        papers_dir=args.papers_dir,
        output_dir=args.output_dir,
        repo_root=args.repo_root.resolve(),
    )
    for path in paths:
        print(f"+ wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
