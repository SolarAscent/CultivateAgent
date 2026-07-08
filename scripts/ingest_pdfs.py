#!/usr/bin/env python3
"""Ingest loose PDFs (e.g. a Zotero storage folder) without a BibTeX file.

Zotero names attachments ``Author et al. - Year - Title.pdf``, which we parse
into a :class:`PaperRef`. Non-matching names fall back to the filename as title.
Usage:
    python scripts/ingest_pdfs.py --list /tmp/medium_pdfs.txt --limit 40
    python scripts/ingest_pdfs.py --dir /path/to/pdfs --limit 40
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cultivate_agent import load_config                       # noqa: E402
from cultivate_agent.ingest import ingest_paper               # noqa: E402
from cultivate_agent.schema.paper import PaperRef, slugify    # noqa: E402

_ZOTERO_RE = re.compile(r"^(?P<auth>.+?)\s*-\s*(?P<year>\d{4})\s*-\s*(?P<title>.+)$")
_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def _ref_from_pdf(pdf: Path) -> PaperRef:
    stem = pdf.stem
    m = _ZOTERO_RE.match(stem)
    if m:
        authors = [a.strip() for a in re.split(r",| and |&", m.group("auth").replace(" et al.", "")) if a.strip()]
        title = m.group("title").strip()
        year = int(m.group("year"))
    else:
        authors, title, year = [], stem, None
    return PaperRef(paper_id=slugify(title)[:80] or slugify(stem),
                    title=title, authors=authors, year=year, pdf_path=str(pdf))


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", help="text file of PDF paths, one per line")
    g.add_argument("--dir", help="directory to glob for *.pdf")
    ap.add_argument("--limit", type=int, default=0, help="max PDFs to ingest (0 = all)")
    ap.add_argument("--tables", action="store_true", help="also extract tables (slower)")
    args = ap.parse_args()

    if args.list:
        paths = [Path(p.strip()) for p in Path(args.list).read_text().splitlines() if p.strip()]
    else:
        paths = sorted(Path(args.dir).glob("*.pdf"))
    if args.limit:
        paths = paths[: args.limit]

    cfg = load_config(root=ROOT)
    ok = 0
    for i, pdf in enumerate(paths, 1):
        if not pdf.exists():
            print(f"[{i}/{len(paths)}] MISSING {pdf}")
            continue
        ref = _ref_from_pdf(pdf)
        try:
            r = ingest_paper(ref, cfg.papers_dir, extract_page_images=False,
                             extract_figures=False, extract_tables=args.tables)
            ok += r.ok
            flag = "ok " if r.ok else "no-text"
            print(f"[{i}/{len(paths)}] {flag} {r.status.fulltext_chars:>7}c  {ref.title[:60]}")
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(paths)}] ERROR {ref.paper_id}: {e}")
    print(f"\nIngested {ok}/{len(paths)} PDFs with full text into {cfg.papers_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
