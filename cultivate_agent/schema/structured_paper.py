"""Structured scientific paper representation for section-routed extraction."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
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


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _children_named(elem: ET.Element, name: str) -> List[ET.Element]:
    return [child for child in list(elem) if _local_name(child.tag) == name]


def _descendants_named(elem: ET.Element, name: str) -> List[ET.Element]:
    return [child for child in elem.iter() if _local_name(child.tag) == name]


def _first_descendant(elem: ET.Element, name: str) -> Optional[ET.Element]:
    for child in elem.iter():
        if _local_name(child.tag) == name:
            return child
    return None


def _text_content(elem: Optional[ET.Element]) -> str:
    if elem is None:
        return ""
    return " ".join(" ".join(elem.itertext()).split())


def _grobid_title(root: ET.Element) -> Optional[str]:
    for title in _descendants_named(root, "title"):
        if title.get("level") in {None, "a"}:
            text = _text_content(title)
            if text:
                return text
    return None


def _grobid_abstract(root: ET.Element) -> Optional[str]:
    for abstract in _descendants_named(root, "abstract"):
        text = _text_content(abstract)
        if text:
            return text
    return None


def _section_from_div(section_id: str, div: ET.Element) -> PaperSection:
    head = _text_content(_first_descendant(div, "head")) or f"Section {section_id}"
    paragraphs: List[PaperParagraph] = []
    for idx, p in enumerate(_children_named(div, "p"), start=1):
        text = _text_content(p)
        if text:
            paragraphs.append(PaperParagraph(paragraph_id=f"{section_id}.p{idx}", text=text))
    if not paragraphs:
        direct_text = []
        for child in list(div):
            if _local_name(child.tag) not in {"head", "div", "figure"}:
                text = _text_content(child)
                if text:
                    direct_text.append(text)
        if direct_text:
            paragraphs = [
                PaperParagraph(paragraph_id=f"{section_id}.p1", text="\n\n".join(direct_text))
            ]
    return PaperSection(section_id=section_id, title=head, paragraphs=paragraphs)


def _collect_body_sections(root: ET.Element) -> List[PaperSection]:
    body = _first_descendant(root, "body")
    if body is None:
        return []
    divs = _children_named(body, "div")
    if not divs:
        text = _text_content(body)
        return [PaperSection(section_id="S1", title="Body", paragraphs=_paragraphs("S1", text))] if text else []
    sections: List[PaperSection] = []
    for idx, div in enumerate(divs, start=1):
        section = _section_from_div(f"S{idx}", div)
        if section.paragraphs:
            sections.append(section)
    return sections


def _figure_caption(fig: ET.Element) -> str:
    parts = []
    for name in ("label", "head", "figDesc"):
        text = _text_content(_first_descendant(fig, name))
        if text:
            parts.append(text)
    if not parts:
        parts.append(_text_content(fig))
    return " ".join(dict.fromkeys(p for p in parts if p))


def _collect_figures_and_tables(root: ET.Element) -> tuple[List[PaperFigure], List[PaperTable]]:
    figures: List[PaperFigure] = []
    tables: List[PaperTable] = []
    for fig in _descendants_named(root, "figure"):
        fig_type = (fig.get("type") or "").lower()
        caption = _figure_caption(fig) or None
        if fig_type == "table":
            tables.append(PaperTable(table_id=f"T{len(tables) + 1}", caption=caption))
        else:
            figures.append(PaperFigure(figure_id=f"F{len(figures) + 1}", caption=caption))
    return figures, tables


def structured_paper_from_grobid_tei_xml(
    paper_id: str,
    xml_text: str,
    *,
    title: Optional[str] = None,
) -> StructuredPaper:
    """Build :class:`StructuredPaper` from GROBID-flavored TEI XML.

    The parser intentionally targets the stable subset CultivateAgent needs:
    title, abstract, body ``div/head/p`` sections, figure captions, and GROBID's
    common ``figure type="table"`` table representation. It is a no-dependency
    bridge for TEI already produced by GROBID, not a GROBID server/client.
    """
    root = ET.fromstring(xml_text)
    parsed_title = title or _grobid_title(root)
    abstract = _grobid_abstract(root)
    sections = _collect_body_sections(root)
    figures, tables = _collect_figures_and_tables(root)
    return StructuredPaper(
        paper_id=paper_id,
        title=parsed_title,
        abstract=abstract,
        sections=sections,
        tables=tables,
        figures=figures,
        source="grobid_tei",
    )


def structured_paper_from_grobid_tei_path(
    paper_id: str,
    tei_path: str | Path,
    *,
    title: Optional[str] = None,
) -> StructuredPaper:
    return structured_paper_from_grobid_tei_xml(
        paper_id,
        Path(tei_path).read_text(encoding="utf-8"),
        title=title,
    )
