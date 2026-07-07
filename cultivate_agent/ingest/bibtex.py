"""Parse a Zotero BibTeX export into :class:`PaperRef` records.

Zotero's ``Export -> BibTeX`` writes a ``file = {...}`` field pointing at the
matched PDF; we parse it so ingestion can locate the source PDF automatically.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from ..schema.paper import PaperRef, slugify


def _clean(s: Optional[str]) -> str:
    if not s:
        return ""
    # Strip BibTeX braces and collapse whitespace.
    s = re.sub(r"[{}]", "", s)
    return " ".join(s.split()).strip()


def _parse_authors(raw: str) -> List[str]:
    raw = _clean(raw)
    if not raw:
        return []
    authors = [a.strip() for a in re.split(r"\s+and\s+", raw) if a.strip()]
    # Normalize "Last, First" -> "First Last" for readability; keep as-is if no comma.
    out = []
    for a in authors:
        if "," in a:
            last, _, first = a.partition(",")
            out.append(f"{first.strip()} {last.strip()}".strip())
        else:
            out.append(a)
    return out


def _parse_zotero_file_field(raw: str) -> Optional[str]:
    """Zotero stores files as ``desc:path:mimetype`` groups joined by ';'.

    Return the first path that looks like a PDF.
    """
    if not raw:
        return None
    for group in raw.split(";"):
        parts = group.split(":")
        for part in parts:
            part = part.strip()
            if part.lower().endswith(".pdf"):
                return part.replace("\\:", ":")
    return None


def parse_bibtex(path: str | Path) -> List[PaperRef]:
    """Parse a ``.bib`` file into a list of :class:`PaperRef`.

    Requires ``bibtexparser`` (``pip install bibtexparser``).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"BibTeX file not found: {path}")
    try:
        import bibtexparser  # type: ignore
        from bibtexparser.bparser import BibTexParser  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError("bibtexparser not installed. `pip install bibtexparser`") from e

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    with path.open(encoding="utf-8", errors="ignore") as f:
        db = bibtexparser.load(f, parser=parser)

    refs: List[PaperRef] = []
    for entry in db.entries:
        key = entry.get("ID") or entry.get("id") or ""
        title = _clean(entry.get("title"))
        year_raw = _clean(entry.get("year"))
        year = int(year_raw) if year_raw.isdigit() else None
        keywords_raw = _clean(entry.get("keywords") or entry.get("keyword"))
        keywords = [k.strip() for k in re.split(r"[;,]", keywords_raw) if k.strip()]

        paper_id = key or slugify(title) or f"paper-{len(refs)+1:04d}"
        refs.append(
            PaperRef(
                paper_id=paper_id,
                title=title,
                authors=_parse_authors(entry.get("author", "")),
                year=year,
                journal=_clean(entry.get("journal") or entry.get("journaltitle") or entry.get("booktitle")),
                doi=_clean(entry.get("doi")) or None,
                url=_clean(entry.get("url")) or None,
                abstract=_clean(entry.get("abstract")) or None,
                keywords=keywords,
                bibtex_key=key or None,
                pdf_path=_parse_zotero_file_field(entry.get("file", "")),
            )
        )
    return refs
