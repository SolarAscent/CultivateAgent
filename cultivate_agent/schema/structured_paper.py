"""Structured scientific paper representation for section-routed extraction."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional

from pydantic import BaseModel, Field


class PaperParagraph(BaseModel):
    paragraph_id: str
    text: str
    page: Optional[int] = None


class PaperSection(BaseModel):
    section_id: str
    title: str
    paragraphs: List[PaperParagraph] = Field(default_factory=list)


class PaperTable(BaseModel):
    table_id: str
    caption: Optional[str] = None
    rows_or_csv_path: Optional[str] = None
    page: Optional[int] = None


class PaperFigure(BaseModel):
    figure_id: str
    caption: Optional[str] = None
    page: Optional[int] = None


class StructuredPaper(BaseModel):
    paper_id: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    sections: List[PaperSection] = Field(default_factory=list)
    tables: List[PaperTable] = Field(default_factory=list)
    figures: List[PaperFigure] = Field(default_factory=list)
    source: str = "plain_text"

    def all_text(self) -> str:
        parts: List[str] = []
        if self.title:
            parts.append(self.title)
        if self.abstract:
            parts.append("Abstract\n" + self.abstract)
        for section in self.sections:
            parts.append(section.title)
            parts.extend(p.text for p in section.paragraphs)
        for table in self.tables:
            if table.caption:
                parts.append(f"{table.table_id}: {table.caption}")
        for figure in self.figures:
            if figure.caption:
                parts.append(f"{figure.figure_id}: {figure.caption}")
        return "\n\n".join(p for p in parts if p)

    def section_passages(self, preferred_titles: Iterable[str]) -> List[tuple[str, str]]:
        patterns = [p.lower() for p in preferred_titles]
        hits: List[tuple[str, str]] = []
        for section in self.sections:
            title = section.title.lower()
            if any(p in title for p in patterns):
                text = "\n\n".join(p.text for p in section.paragraphs)
                if text.strip():
                    hits.append((section.section_id, f"{section.title}\n{text}"))
        return hits


_HEADING_RE = re.compile(
    r"(?im)^\s*(?:\d+(?:\.\d+)*\.?\s+)?("
    r"abstract|introduction|materials?\s+and\s+methods|methods|"
    r"experimental(?:\s+section)?|results(?:\s+and\s+discussion)?|results|"
    r"discussion|conclusion|media\s+formulation|cell\s+culture|supplementary\s+materials?"
    r")\b.*$"
)


def _paragraphs(section_id: str, text: str) -> List[PaperParagraph]:
    chunks = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return [
        PaperParagraph(paragraph_id=f"{section_id}.p{i}", text=chunk)
        for i, chunk in enumerate(chunks, start=1)
    ]


def structured_paper_from_text(paper_id: str, text: str, *, title: Optional[str] = None) -> StructuredPaper:
    """Build a lightweight structured paper from plain text.

    This is the always-available fallback. It does not pretend to recover a full
    TEI document; it only gives extraction stable section/paragraph IDs until an
    optional GROBID backend is available.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        section = PaperSection(
            section_id="S1",
            title="Full text",
            paragraphs=_paragraphs("S1", text),
        )
        return StructuredPaper(paper_id=paper_id, title=title, sections=[section])

    sections: List[PaperSection] = []
    preamble = text[:matches[0].start()].strip()
    if preamble:
        sections.append(PaperSection(
            section_id="S0",
            title="Preamble",
            paragraphs=_paragraphs("S0", preamble),
        ))

    abstract: Optional[str] = None
    for idx, match in enumerate(matches, start=1):
        start = match.end()
        end = matches[idx].start() if idx < len(matches) else len(text)
        title_text = match.group(0).strip()
        body = text[start:end].strip()
        section_id = f"S{idx}"
        paras = _paragraphs(section_id, body)
        sections.append(PaperSection(section_id=section_id, title=title_text, paragraphs=paras))
        if abstract is None and match.group(1).lower().startswith("abstract"):
            abstract = "\n\n".join(p.text for p in paras) or None

    return StructuredPaper(paper_id=paper_id, title=title, abstract=abstract, sections=sections)
