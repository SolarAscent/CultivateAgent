"""Structured scientific paper representation for section-routed extraction."""

from __future__ import annotations

import hashlib
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


class PaperTableCell(BaseModel):
    """One source cell with a stable pointer into a structured table."""

    cell_id: str
    row_index: int
    column_index: int
    text: str
    is_header: bool = False
    row_span: int = 1
    column_span: int = 1
    scope: Optional[str] = None


class PaperTable(BaseModel):
    table_id: str
    source_table_id: Optional[str] = None
    caption: Optional[str] = None
    footnotes: List[str] = Field(default_factory=list)
    cells: List[PaperTableCell] = Field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    source_sha256: Optional[str] = None
    rows_or_csv_path: Optional[str] = None
    page: Optional[int] = None

    def cell(self, cell_id: str) -> Optional[PaperTableCell]:
        """Resolve a model-returned pointer without reading a numeric value."""
        return next((cell for cell in self.cells if cell.cell_id == cell_id), None)

    def as_text(self) -> str:
        """Serialize source cells for extraction while preserving their pointers."""
        parts = [self.caption] if self.caption else []
        parts.extend(f"[{cell.cell_id}] {cell.text}" for cell in self.cells if cell.text)
        parts.extend(f"[footnote] {footnote}" for footnote in self.footnotes)
        return "\n".join(parts)


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
            table_text = table.as_text()
            if table_text:
                parts.append(f"{table.table_id}: {table_text}")
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


def _first_child(elem: ET.Element, name: str) -> Optional[ET.Element]:
    for child in list(elem):
        if _local_name(child.tag) == name:
            return child
    return None


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
    for article_title in _descendants_named(root, "article-title"):
        text = _text_content(article_title)
        if text:
            return text
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
    head = _text_content(_first_child(div, "head")) or f"Section {section_id}"
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


def _jats_sec_title(sec: ET.Element, section_id: str, prefix: tuple[str, ...]) -> str:
    title = _text_content(_first_child(sec, "title")) or f"Section {section_id}"
    return " / ".join([*prefix, title]) if prefix else title


def _section_from_sec(section_id: str, sec: ET.Element, prefix: tuple[str, ...] = ()) -> PaperSection:
    title = _jats_sec_title(sec, section_id, prefix)
    paragraphs: List[PaperParagraph] = []
    for idx, p in enumerate(_children_named(sec, "p"), start=1):
        text = _text_content(p)
        if text:
            paragraphs.append(PaperParagraph(paragraph_id=f"{section_id}.p{idx}", text=text))
    return PaperSection(section_id=section_id, title=title, paragraphs=paragraphs)


def _collect_jats_sections(sec: ET.Element, section_id: str, prefix: tuple[str, ...] = ()) -> List[PaperSection]:
    section = _section_from_sec(section_id, sec, prefix)
    sections = [section] if section.paragraphs else []
    title = _text_content(_first_child(sec, "title")) or f"Section {section_id}"
    for idx, child in enumerate(_children_named(sec, "sec"), start=1):
        sections.extend(_collect_jats_sections(child, f"{section_id}.{idx}", (*prefix, title)))
    return sections


def _collect_body_sections(root: ET.Element) -> List[PaperSection]:
    body = _first_descendant(root, "body")
    if body is None:
        return []
    divs = _children_named(body, "div")
    secs = _children_named(body, "sec")
    if secs:
        sections: List[PaperSection] = []
        for idx, sec in enumerate(secs, start=1):
            sections.extend(_collect_jats_sections(sec, f"S{idx}"))
        return sections
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
    for name in ("label", "head", "figDesc", "caption"):
        text = _text_content(_first_descendant(fig, name))
        if text:
            parts.append(text)
    if not parts:
        parts.append(_text_content(fig))
    return " ".join(dict.fromkeys(p for p in parts if p))


def _element_id(elem: ET.Element) -> Optional[str]:
    return elem.get("id") or elem.get("{http://www.w3.org/XML/1998/namespace}id")


def _positive_span(raw: Optional[str]) -> int:
    try:
        value = int(raw or "1")
    except ValueError:
        return 1
    return max(1, value)


def _jats_table_cells(table_id: str, table: Optional[ET.Element]) -> tuple[List[PaperTableCell], int, int]:
    if table is None:
        return [], 0, 0

    cells: List[PaperTableCell] = []
    occupied: set[tuple[int, int]] = set()
    row_count = 0
    column_count = 0
    for row_index, row in enumerate(_descendants_named(table, "tr")):
        row_count = row_index + 1
        column_index = 0
        for source_cell in list(row):
            cell_type = _local_name(source_cell.tag)
            if cell_type not in {"th", "td"}:
                continue
            while (row_index, column_index) in occupied:
                column_index += 1
            row_span = _positive_span(source_cell.get("rowspan"))
            column_span = _positive_span(source_cell.get("colspan"))
            cell_id = f"{table_id}.R{row_index + 1}.C{column_index + 1}"
            cells.append(PaperTableCell(
                cell_id=cell_id,
                row_index=row_index,
                column_index=column_index,
                text=_text_content(source_cell),
                is_header=cell_type == "th",
                row_span=row_span,
                column_span=column_span,
                scope=source_cell.get("scope"),
            ))
            for covered_row in range(row_index + 1, row_index + row_span):
                for covered_column in range(column_index, column_index + column_span):
                    occupied.add((covered_row, covered_column))
            column_index += column_span
            column_count = max(column_count, column_index)
        while (row_index, column_index) in occupied:
            column_index += 1
        column_count = max(column_count, column_index)
    return cells, row_count, column_count


def _jats_table_footnotes(table_wrap: ET.Element) -> List[str]:
    footnotes: List[str] = []
    for foot in _descendants_named(table_wrap, "table-wrap-foot"):
        notes = _descendants_named(foot, "fn")
        candidates = notes or _descendants_named(foot, "p")
        for note in candidates:
            text = _text_content(note)
            if text and text not in footnotes:
                footnotes.append(text)
    return footnotes


def _collect_figures_and_tables(
    root: ET.Element,
    *,
    source_sha256: Optional[str] = None,
) -> tuple[List[PaperFigure], List[PaperTable]]:
    figures: List[PaperFigure] = []
    tables: List[PaperTable] = []
    for fig in _descendants_named(root, "figure"):
        fig_type = (fig.get("type") or "").lower()
        caption = _figure_caption(fig) or None
        if fig_type == "table":
            tables.append(PaperTable(
                table_id=f"T{len(tables) + 1}",
                source_table_id=_element_id(fig),
                caption=caption,
                source_sha256=source_sha256,
            ))
        else:
            figures.append(PaperFigure(figure_id=f"F{len(figures) + 1}", caption=caption))
    for fig in _descendants_named(root, "fig"):
        caption = _figure_caption(fig) or None
        figures.append(PaperFigure(figure_id=f"F{len(figures) + 1}", caption=caption))
    for table_wrap in _descendants_named(root, "table-wrap"):
        table_id = f"T{len(tables) + 1}"
        caption = _jats_table_caption(table_wrap) or None
        cells, row_count, column_count = _jats_table_cells(
            table_id,
            _first_descendant(table_wrap, "table"),
        )
        tables.append(PaperTable(
            table_id=table_id,
            source_table_id=_element_id(table_wrap),
            caption=caption,
            footnotes=_jats_table_footnotes(table_wrap),
            cells=cells,
            row_count=row_count,
            column_count=column_count,
            source_sha256=source_sha256,
        ))
    return figures, tables


def _jats_table_caption(table_wrap: ET.Element) -> str:
    parts = []
    for name in ("label", "caption"):
        text = _text_content(_first_child(table_wrap, name))
        if text:
            parts.append(text)
    return " ".join(dict.fromkeys(p for p in parts if p))


def _xml_source(root: ET.Element) -> str:
    if _local_name(root.tag) == "article":
        return "jats_xml"
    return "grobid_tei"


def structured_paper_from_grobid_tei_xml(
    paper_id: str,
    xml_text: str,
    *,
    title: Optional[str] = None,
) -> StructuredPaper:
    """Build :class:`StructuredPaper` from GROBID TEI or JATS article XML.

    The parser intentionally targets the stable subset CultivateAgent needs:
    title, abstract, body sections, table captions, and figure captions. It is a
    no-dependency bridge for structured XML already produced by GROBID, Europe
    PMC, or another legal full-text source, not a PDF-to-XML service.
    """
    root = ET.fromstring(xml_text)
    parsed_title = title or _grobid_title(root)
    abstract = _grobid_abstract(root)
    sections = _collect_body_sections(root)
    source_sha256 = hashlib.sha256(xml_text.encode("utf-8")).hexdigest()
    figures, tables = _collect_figures_and_tables(root, source_sha256=source_sha256)
    return StructuredPaper(
        paper_id=paper_id,
        title=parsed_title,
        abstract=abstract,
        sections=sections,
        tables=tables,
        figures=figures,
        source=_xml_source(root),
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
