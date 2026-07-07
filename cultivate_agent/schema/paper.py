"""Paper-level records and the on-disk folder layout.

The layout mirrors the structure proposed in the project record::

    data/papers/<paper_slug>/
        page_images/           # one PNG per page (optional, for vision/QA)
        figures/               # extracted figure images
        tables/                # extracted tables (csv/json)
        <slug>.pdf             # the source PDF (if available)
        fulltext.txt           # pdftotext / PyMuPDF plain text (LLM-friendly)
        fulltext.xml           # structured full text (optional; e.g. GROBID TEI)
        references.json        # parsed reference list (optional)
        assets.json            # manifest of figures/tables/page images
        metadata.json          # PaperRef + ingestion status (this module)
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


def slugify(text: str, *, max_len: int = 80) -> str:
    """Filesystem-safe, stable slug from a title (or any string)."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return (text[:max_len] or "untitled").strip("-")


class PaperRef(BaseModel):
    """Bibliographic reference (typically parsed from Zotero BibTeX)."""

    paper_id: str = Field(..., description="Stable local ID (e.g. bibtex key or slug).")
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    bibtex_key: Optional[str] = None
    pdf_path: Optional[str] = Field(None, description="Original PDF path if known (pre-ingestion).")

    @property
    def slug(self) -> str:
        base = self.title or self.paper_id
        return f"{slugify(base)}"


class IngestStatus(BaseModel):
    """Records what has been produced for a paper, so runs are resumable."""

    has_pdf: bool = False
    has_fulltext: bool = False
    n_pages: int = 0
    n_figures: int = 0
    n_tables: int = 0
    fulltext_chars: int = 0
    text_extractor: Optional[str] = None      # "pymupdf" | "pdftotext" | "manual"
    ingested_at: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class PaperMetadata(BaseModel):
    """What lives in ``metadata.json``: the ref + ingestion status."""

    ref: PaperRef
    status: IngestStatus = Field(default_factory=IngestStatus)
    triage_category: Optional[str] = None    # A / B / C, once classified

    def touch(self) -> None:
        self.status.ingested_at = datetime.now(timezone.utc).isoformat()


class PaperPaths:
    """Resolves and creates the per-paper folder layout."""

    def __init__(self, root: Path, paper_id: str, slug: Optional[str] = None):
        self.root = Path(root)
        self.paper_id = paper_id
        self.slug = slug or slugify(paper_id)
        self.dir = self.root / self.slug

    # --- subdirectories ---
    @property
    def page_images(self) -> Path: return self.dir / "page_images"
    @property
    def figures(self) -> Path: return self.dir / "figures"
    @property
    def tables(self) -> Path: return self.dir / "tables"

    # --- files ---
    @property
    def pdf(self) -> Path: return self.dir / f"{self.slug}.pdf"
    @property
    def fulltext(self) -> Path: return self.dir / "fulltext.txt"
    @property
    def fulltext_xml(self) -> Path: return self.dir / "fulltext.xml"
    @property
    def references(self) -> Path: return self.dir / "references.json"
    @property
    def assets(self) -> Path: return self.dir / "assets.json"
    @property
    def metadata(self) -> Path: return self.dir / "metadata.json"

    def ensure(self) -> "PaperPaths":
        for d in (self.dir, self.page_images, self.figures, self.tables):
            d.mkdir(parents=True, exist_ok=True)
        return self

    # --- metadata helpers ---
    def load_metadata(self) -> Optional[PaperMetadata]:
        if self.metadata.exists():
            return PaperMetadata.model_validate_json(self.metadata.read_text(encoding="utf-8"))
        return None

    def save_metadata(self, meta: PaperMetadata) -> None:
        self.metadata.write_text(meta.model_dump_json(indent=2), encoding="utf-8")

    def read_fulltext(self) -> str:
        return self.fulltext.read_text(encoding="utf-8", errors="ignore") if self.fulltext.exists() else ""

    def write_assets(self, manifest: dict) -> None:
        self.assets.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
