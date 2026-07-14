"""Reproducible PDF table-discovery audit for the tier-1 off-ramp."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .pdf import _try_import_fitz


_NUMBER = r"[-+]?(?:\d+(?:[,.]\d+)*)"
STAT_CANDIDATE_RE = re.compile(
    rf"(?:{_NUMBER}\s*(?:±|\+/-|\+/−)\s*{_NUMBER}"
    r"|\b(?:SD|SEM|standard deviation|standard error)\b"
    r"|\bn\s*=\s*\d+)",
    re.I,
)


@dataclass(frozen=True)
class TableStrategyAudit:
    regions: int = 0
    cells: int = 0
    stat_candidate_cells: int = 0


@dataclass(frozen=True)
class PDFTableAudit:
    pdf_sha256: str
    pages: int
    lines: TableStrategyAudit
    text: TableStrategyAudit
    classification: str


class PDFTableAuditError(RuntimeError):
    """Raised when a requested PDF cannot be audited."""


def is_stat_candidate(text: str) -> bool:
    """Recognize explicit numeric dispersion/sample-size syntax, not bare ±."""
    return bool(STAT_CANDIDATE_RE.search(" ".join(str(text).split())))


def _audit_strategy(doc, strategy: Optional[str]) -> TableStrategyAudit:
    regions = cells = candidates = 0
    for page in doc:
        try:
            found = page.find_tables(strategy=strategy).tables
        except Exception:  # one malformed page must not erase the document audit
            continue
        for table in found or []:
            try:
                rows = table.extract() or []
            except Exception:
                continue
            regions += 1
            for row in rows:
                for cell in row:
                    if cell is None:
                        continue
                    cells += 1
                    if is_stat_candidate(cell):
                        candidates += 1
    return TableStrategyAudit(regions=regions, cells=cells, stat_candidate_cells=candidates)


def audit_pdf_tables(pdf_path: str | Path, *, fitz_module=None) -> PDFTableAudit:
    """Compare PyMuPDF line and text strategies without persisting extracted cells."""
    path = Path(pdf_path)
    if not path.is_file():
        raise PDFTableAuditError(f"PDF does not exist: {path}")
    fitz_module = fitz_module or _try_import_fitz()
    if fitz_module is None:
        raise PDFTableAuditError("PyMuPDF is unavailable")
    try:
        document = fitz_module.open(path)
    except Exception as exc:
        raise PDFTableAuditError(f"cannot open PDF: {path}") from exc
    try:
        pages = document.page_count
        lines = _audit_strategy(document, None)
        text = _audit_strategy(document, "text")
    finally:
        document.close()
    if lines.stat_candidate_cells:
        classification = "structured_stat_candidates_require_review"
    elif text.stat_candidate_cells:
        classification = "layout_text_candidates_only"
    else:
        classification = "no_stat_candidates"
    return PDFTableAudit(
        pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        pages=pages,
        lines=lines,
        text=text,
        classification=classification,
    )
