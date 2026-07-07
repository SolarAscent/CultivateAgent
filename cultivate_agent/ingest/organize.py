"""Build the per-paper folder layout from refs + PDFs, resumably.

This is the concrete implementation of the file structure proposed in the
project record. It is idempotent: re-running skips work already done unless
``force=True``.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..schema.paper import IngestStatus, PaperMetadata, PaperPaths, PaperRef
from .grobid import GrobidError, write_fulltext_tei
from . import pdf as pdfmod


@dataclass
class IngestResult:
    paper_id: str
    slug: str
    ok: bool
    status: IngestStatus


def ingest_paper(
    ref: PaperRef,
    papers_dir: str | Path,
    *,
    extract_page_images: bool = True,
    extract_figures: bool = True,
    extract_tables: bool = True,
    page_image_dpi: int = 150,
    grobid_tei: bool = False,
    grobid_url: str = "http://localhost:8070",
    grobid_timeout: float = 60.0,
    force: bool = False,
) -> IngestResult:
    """Create ``papers/<slug>/`` and populate it for a single paper."""
    paths = PaperPaths(papers_dir, ref.paper_id, slug=ref.slug).ensure()

    existing = None if force else paths.load_metadata()
    status = existing.status if existing else IngestStatus()

    # 1) Locate + copy the source PDF.
    if ref.pdf_path and not paths.pdf.exists():
        src = Path(ref.pdf_path)
        if src.exists():
            try:
                shutil.copy2(src, paths.pdf)
            except Exception as e:  # noqa: BLE001
                status.warnings.append(f"could not copy PDF: {e}")
    status.has_pdf = paths.pdf.exists()

    # 2) Full text.
    if paths.pdf.exists() and (force or not paths.fulltext.exists()):
        text, extractor, n_pages = pdfmod.extract_text(paths.pdf)
        if text:
            paths.fulltext.write_text(text, encoding="utf-8")
            status.has_fulltext = True
            status.fulltext_chars = len(text)
            status.text_extractor = extractor
            status.n_pages = n_pages
        else:
            status.warnings.append("text extraction returned empty")
    elif paths.fulltext.exists():
        status.has_fulltext = True
        status.fulltext_chars = len(paths.read_fulltext())

    # 3) Optional structured full text via GROBID TEI.
    if paths.pdf.exists() and grobid_tei and (force or not paths.fulltext_xml.exists()):
        try:
            write_fulltext_tei(
                paths.pdf,
                paths.fulltext_xml,
                base_url=grobid_url,
                timeout=grobid_timeout,
            )
        except GrobidError as e:
            status.warnings.append(f"grobid TEI extraction failed: {e}")
    if paths.fulltext_xml.exists():
        status.has_structured_fulltext = True
        status.structured_extractor = "grobid"

    # 4) Optional assets (page images, figures, tables).
    figures: List[Path] = []
    tables: List[Path] = []
    pages: List[Path] = []
    if paths.pdf.exists():
        if extract_page_images and (force or not any(paths.page_images.glob("*.png"))):
            pages = pdfmod.render_page_images(paths.pdf, paths.page_images, dpi=page_image_dpi)
        if extract_figures and (force or not any(paths.figures.glob("*"))):
            figures = pdfmod.extract_figures(paths.pdf, paths.figures)
        if extract_tables and (force or not any(paths.tables.glob("*.csv"))):
            tables = pdfmod.extract_tables(paths.pdf, paths.tables)

    status.n_figures = len(list(paths.figures.glob("*"))) or len(figures)
    status.n_tables = len(list(paths.tables.glob("*.csv"))) or len(tables)

    # 5) Assets manifest.
    manifest = {
        "paper_id": ref.paper_id,
        "page_images": sorted(p.name for p in paths.page_images.glob("*.png")),
        "figures": sorted(p.name for p in paths.figures.glob("*")),
        "tables": sorted(p.name for p in paths.tables.glob("*.csv")),
        "fulltext": paths.fulltext.name if paths.fulltext.exists() else None,
        "fulltext_xml": paths.fulltext_xml.name if paths.fulltext_xml.exists() else None,
    }
    paths.write_assets(manifest)

    # 6) Metadata.
    meta = PaperMetadata(ref=ref, status=status, triage_category=(existing.triage_category if existing else None))
    meta.touch()
    paths.save_metadata(meta)

    return IngestResult(paper_id=ref.paper_id, slug=paths.slug, ok=status.has_fulltext, status=status)


def ingest_library(
    refs: List[PaperRef],
    papers_dir: str | Path,
    *,
    extract_page_images: bool = True,
    extract_figures: bool = True,
    extract_tables: bool = True,
    page_image_dpi: int = 150,
    grobid_tei: bool = False,
    grobid_url: str = "http://localhost:8070",
    grobid_timeout: float = 60.0,
    force: bool = False,
    on_progress=None,
) -> List[IngestResult]:
    """Ingest a whole library; ``on_progress(i, total, result)`` optional."""
    papers_dir = Path(papers_dir)
    papers_dir.mkdir(parents=True, exist_ok=True)
    results: List[IngestResult] = []
    total = len(refs)
    for i, ref in enumerate(refs, start=1):
        res = ingest_paper(
            ref, papers_dir,
            extract_page_images=extract_page_images,
            extract_figures=extract_figures,
            extract_tables=extract_tables,
            page_image_dpi=page_image_dpi,
            grobid_tei=grobid_tei,
            grobid_url=grobid_url,
            grobid_timeout=grobid_timeout,
            force=force,
        )
        results.append(res)
        if on_progress:
            on_progress(i, total, res)
    return results


def iter_ingested(papers_dir: str | Path):
    """Yield ``(PaperPaths, PaperMetadata)`` for every ingested paper on disk."""
    papers_dir = Path(papers_dir)
    if not papers_dir.exists():
        return
    for meta_file in sorted(papers_dir.glob("*/metadata.json")):
        try:
            meta = PaperMetadata.model_validate_json(meta_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        paths = PaperPaths(papers_dir, meta.ref.paper_id, slug=meta_file.parent.name)
        yield paths, meta
