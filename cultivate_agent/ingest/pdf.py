"""PDF -> text / page images / figures / tables.

Primary backend is PyMuPDF (``fitz``); text falls back to the ``pdftotext`` CLI
(as used in the first attempt described in the project record). Everything
degrades gracefully: if a backend is unavailable the function returns empty
results and records a warning rather than raising, so a batch run never dies on
one bad PDF.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


def _try_import_fitz():
    try:
        import fitz  # type: ignore  # PyMuPDF
        return fitz
    except ImportError:
        return None


def extract_text(pdf_path: str | Path) -> Tuple[str, str, int]:
    """Return ``(text, extractor_name, n_pages)``.

    Tries PyMuPDF first, then the ``pdftotext`` CLI. Empty text if both fail.
    """
    pdf_path = Path(pdf_path)
    fitz = _try_import_fitz()
    if fitz is not None:
        try:
            doc = fitz.open(pdf_path)
            pages = [page.get_text("text") for page in doc]
            n = doc.page_count
            doc.close()
            return "\n".join(pages), "pymupdf", n
        except Exception:  # noqa: BLE001
            pass

    if shutil.which("pdftotext"):
        try:
            out = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                capture_output=True, text=True, timeout=180,
            )
            if out.returncode == 0:
                text = out.stdout
                n = text.count("\f") + 1  # form-feed per page
                return text, "pdftotext", n
        except Exception:  # noqa: BLE001
            pass

    return "", "none", 0


def render_page_images(pdf_path: str | Path, out_dir: str | Path, *, dpi: int = 150) -> List[Path]:
    """Render each page to a PNG (useful for vision QA of figures/tables)."""
    fitz = _try_import_fitz()
    if fitz is None:
        return []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    try:
        doc = fitz.open(pdf_path)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=mat)
            p = out_dir / f"page_{i:03d}.png"
            pix.save(p)
            saved.append(p)
        doc.close()
    except Exception:  # noqa: BLE001
        return saved
    return saved


def extract_figures(pdf_path: str | Path, out_dir: str | Path, *, min_bytes: int = 4096) -> List[Path]:
    """Extract embedded raster images (figures). Skips tiny logos/icons."""
    fitz = _try_import_fitz()
    if fitz is None:
        return []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    try:
        doc = fitz.open(pdf_path)
        seen = set()
        for pno, page in enumerate(doc, start=1):
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in seen:
                    continue
                seen.add(xref)
                try:
                    base = doc.extract_image(xref)
                except Exception:  # noqa: BLE001
                    continue
                data, ext = base.get("image"), base.get("ext", "png")
                if not data or len(data) < min_bytes:
                    continue
                p = out_dir / f"fig_p{pno:03d}_{xref}.{ext}"
                p.write_bytes(data)
                saved.append(p)
        doc.close()
    except Exception:  # noqa: BLE001
        return saved
    return saved


def extract_tables(pdf_path: str | Path, out_dir: str | Path) -> List[Path]:
    """Extract tables to CSV using PyMuPDF's table finder (>=1.23).

    Tables are where the quantitative modeling data (block J) usually lives, so
    getting them out as CSV is high value. No-op if the API is unavailable.
    """
    fitz = _try_import_fitz()
    if fitz is None:
        return []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    try:
        doc = fitz.open(pdf_path)
        for pno, page in enumerate(doc, start=1):
            finder = getattr(page, "find_tables", None)
            if finder is None:
                break  # older PyMuPDF; give up cleanly
            try:
                tabs = finder()
            except Exception:  # noqa: BLE001
                continue
            for ti, tab in enumerate(getattr(tabs, "tables", []) or [], start=1):
                try:
                    import csv
                    rows = tab.extract()
                    if not rows:
                        continue
                    p = out_dir / f"table_p{pno:03d}_{ti}.csv"
                    with p.open("w", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows(rows)
                    saved.append(p)
                except Exception:  # noqa: BLE001
                    continue
        doc.close()
    except Exception:  # noqa: BLE001
        return saved
    return saved
