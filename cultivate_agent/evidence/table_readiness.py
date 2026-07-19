"""Deterministic readiness audit for tier-1 group statistics in JATS tables."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..ingest.europe_pmc import inspect_europe_pmc_jats
from ..schema import PaperTable, PaperTableCell, slugify, structured_paper_from_grobid_tei_path
from .tables import TableCellRole, TablePointerError, parse_cell_number


_PLUS_MINUS_RE = re.compile(
    r"[-+]?\d[\d,.]*(?:\s*)(?:±|\+/-|\+/−)(?:\s*)[-+]?\d",
    re.I,
)
_EXPLICIT_N_RE = re.compile(r"\bn\s*=\s*\d+\b", re.I)
_N_HEADER_RE = re.compile(r"^\s*(?:n|sample size)\s*$", re.I)
_SD_RE = re.compile(r"\bSD\b|\bS\.D\.|standard deviation", re.I)
_SEM_RE = re.compile(
    r"\bSEM\b|\bS\.E\.M\.|\bSE\b|standard error|\bSE\s+Coef\b",
    re.I,
)
_MEAN_RE = re.compile(r"\bmeans?\b|\baverage\b", re.I)
_RESPONSE_RE = re.compile(
    r"proliferat|differentiat|cell\s+(?:count|number|growth|viability)|"
    r"gene expression|fusion index|myogenic|adipogenic|metabolic assay",
    re.I,
)
_COMPOSITION_RE = re.compile(
    r"\b(?:component|composition|concentration|amino acid|vitamin|mineral|"
    r"primer|reagent|resource|inorganic salt|factor level)s?\b",
    re.I,
)
_MODEL_RE = re.compile(
    r"analysis of variance|\bANOVA\b|\bcoefficient\b|\bSE\s+Coef\b|"
    r"\bt-value\b|\bp\s*-?values?\b",
    re.I,
)
_NON_MEDIUM_OUTCOME_RE = re.compile(r"carcass|meat quality", re.I)


@dataclass(frozen=True)
class TableReadinessAudit:
    record_id: str
    paper_id: str
    table_id: str
    source_table_id: str
    source_sha256: str
    row_count: int
    column_count: int
    cell_count: int
    numeric_cell_count: int
    combined_stat_cell_ids: tuple[str, ...]
    sample_size_cell_ids: tuple[str, ...]
    sample_size_context_ids: tuple[str, ...]
    dispersion_context_ids: tuple[str, ...]
    dispersion_kind: str
    response_context: bool
    exclusion_reason: str
    status: str

    def to_row(self) -> dict[str, str | int]:
        return {
            "record_id": self.record_id,
            "paper_id": self.paper_id,
            "table_id": self.table_id,
            "source_table_id": self.source_table_id or "-",
            "source_sha256": self.source_sha256,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "cell_count": self.cell_count,
            "numeric_cell_count": self.numeric_cell_count,
            "combined_stat_cell_ids": ";".join(self.combined_stat_cell_ids) or "-",
            "sample_size_cell_ids": ";".join(self.sample_size_cell_ids) or "-",
            "sample_size_context_ids": ";".join(self.sample_size_context_ids) or "-",
            "dispersion_context_ids": ";".join(self.dispersion_context_ids) or "-",
            "dispersion_kind": self.dispersion_kind,
            "response_context": str(self.response_context).lower(),
            "exclusion_reason": self.exclusion_reason,
            "status": self.status,
        }


@dataclass(frozen=True)
class SourceTableReadinessAudit:
    record_id: str
    paper_id: str
    doi: str
    source_sha256: str
    table_count: int
    cell_count: int
    structural_candidate_tables: int
    incomplete_tables: int
    excluded_statistical_tables: int
    status: str

    def to_row(self) -> dict[str, str | int]:
        return self.__dict__.copy()


def _normalize_doi(value: object) -> str:
    return str(value or "").strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")


def _cell_is_numeric(cell: PaperTableCell) -> bool:
    try:
        parse_cell_number(cell, TableCellRole.TREATMENT_MEAN)
    except TablePointerError:
        return False
    return True


def _header_covers_cell(header: PaperTableCell, cell: PaperTableCell) -> bool:
    return (
        header.is_header
        and header.row_index < cell.row_index
        and header.column_index <= cell.column_index < header.column_index + header.column_span
    )


def _context_items(table: PaperTable) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    if table.caption:
        items.append((f"{table.table_id}.CAPTION", table.caption))
    items.extend((cell.cell_id, cell.text) for cell in table.cells if cell.is_header and cell.text)
    items.extend(
        (f"{table.table_id}.F{index}", footnote)
        for index, footnote in enumerate(table.footnotes, start=1)
        if footnote
    )
    return items


def audit_table_structure(record_id: str, paper_id: str, table: PaperTable) -> TableReadinessAudit:
    """Classify one table without assigning treatment/control semantics."""
    context_items = _context_items(table)
    context_text = " | ".join(text for _, text in context_items)
    numeric_cells = [cell for cell in table.cells if not cell.is_header and _cell_is_numeric(cell)]
    combined_cells = tuple(
        cell.cell_id for cell in table.cells
        if not cell.is_header and _PLUS_MINUS_RE.search(" ".join(cell.text.split()))
    )
    explicit_n_cells = {
        cell.cell_id for cell in table.cells if _EXPLICIT_N_RE.search(cell.text)
    }
    n_headers = [cell for cell in table.cells if cell.is_header and _N_HEADER_RE.fullmatch(cell.text)]
    for cell in numeric_cells:
        if any(_header_covers_cell(header, cell) for header in n_headers):
            explicit_n_cells.add(cell.cell_id)
    sample_context = tuple(
        locator for locator, text in context_items if _EXPLICIT_N_RE.search(text)
    )
    dispersion_context = tuple(
        locator for locator, text in context_items if _SD_RE.search(text) or _SEM_RE.search(text)
    )
    has_sd = any(_SD_RE.search(text) for _, text in context_items)
    has_sem = any(_SEM_RE.search(text) for _, text in context_items)
    if has_sd and has_sem:
        dispersion_kind = "mixed"
    elif has_sd:
        dispersion_kind = "sd"
    elif has_sem:
        dispersion_kind = "sem"
    elif combined_cells:
        dispersion_kind = "unspecified"
    else:
        dispersion_kind = "none"

    response_context = bool(_RESPONSE_RE.search(context_text))
    if _NON_MEDIUM_OUTCOME_RE.search(context_text):
        exclusion_reason = "non_medium_outcome_statistics"
    elif _MODEL_RE.search(context_text) and not response_context:
        exclusion_reason = "model_or_significance_statistics"
    elif _COMPOSITION_RE.search(context_text) and not response_context:
        exclusion_reason = "composition_or_resource_statistics"
    else:
        exclusion_reason = "-"

    mean_context = bool(_MEAN_RE.search(context_text))
    has_stat_values = bool(combined_cells) or (
        len(numeric_cells) >= 2 and (mean_context or dispersion_kind not in {"none", "unspecified"})
    )
    has_sample_size_cell = bool(explicit_n_cells)
    has_typed_dispersion = dispersion_kind in {"sd", "sem", "mixed"}
    if exclusion_reason != "-" and has_stat_values:
        status = "excluded_non_effect_statistics"
    elif not has_stat_values:
        status = "no_group_stat_structure"
    elif not has_typed_dispersion and not has_sample_size_cell:
        status = "incomplete_missing_dispersion_type_and_sample_size"
    elif not has_typed_dispersion:
        status = "incomplete_missing_dispersion_type"
    elif not has_sample_size_cell and sample_context:
        status = "incomplete_sample_size_not_cell_addressable"
    elif not has_sample_size_cell:
        status = "incomplete_missing_sample_size"
    elif not response_context:
        status = "ambiguous_complete_structure_needs_review"
    elif len(combined_cells) < 2 and len(numeric_cells) < 3:
        status = "incomplete_insufficient_group_values"
    else:
        status = "structural_group_stats_candidate"

    return TableReadinessAudit(
        record_id=record_id,
        paper_id=paper_id,
        table_id=table.table_id,
        source_table_id=table.source_table_id or "",
        source_sha256=table.source_sha256 or "",
        row_count=table.row_count,
        column_count=table.column_count,
        cell_count=len(table.cells),
        numeric_cell_count=len(numeric_cells),
        combined_stat_cell_ids=combined_cells,
        sample_size_cell_ids=tuple(sorted(explicit_n_cells)),
        sample_size_context_ids=sample_context,
        dispersion_context_ids=dispersion_context,
        dispersion_kind=dispersion_kind,
        response_context=response_context,
        exclusion_reason=exclusion_reason,
        status=status,
    )


def audit_verified_jats_group_stats(
    *,
    corpus_rows: Sequence[Mapping[str, str]],
    source_rows: Sequence[Mapping[str, str]],
    acquisition_rows: Sequence[Mapping[str, str]],
    papers_dir: str | Path,
) -> tuple[tuple[SourceTableReadinessAudit, ...], tuple[TableReadinessAudit, ...]]:
    """Verify every source before producing source- and table-level audits."""
    corpus_by_id = {row["record_id"]: row for row in corpus_rows}
    acquisition_by_id = {row["record_id"]: row for row in acquisition_rows}
    if len(corpus_by_id) != len(corpus_rows):
        raise ValueError("corpus contains duplicate record IDs")
    if len(acquisition_by_id) != len(acquisition_rows):
        raise ValueError("acquisition reports contain duplicate record IDs")
    source_ids = [row["record_id"] for row in source_rows]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source manifest contains duplicate record IDs")

    papers_dir = Path(papers_dir)
    source_audits: list[SourceTableReadinessAudit] = []
    table_audits: list[TableReadinessAudit] = []
    for source in source_rows:
        record_id = source["record_id"]
        canonical = corpus_by_id.get(record_id)
        acquisition = acquisition_by_id.get(record_id)
        if canonical is None or acquisition is None:
            raise ValueError(f"{record_id}: missing canonical or acquisition row")
        expected_doi = _normalize_doi(canonical.get("doi"))
        if any(
            _normalize_doi(row.get("doi")) != expected_doi
            for row in (source, acquisition)
        ):
            raise ValueError(f"{record_id}: DOI disagrees across manifests")
        if source["paper_id"] != slugify(canonical.get("title", "")):
            raise ValueError(f"{record_id}: paper ID disagrees with canonical title")
        if acquisition.get("status") not in {"downloaded", "existing_verified"}:
            raise ValueError(f"{record_id}: acquisition is not verified")

        xml_path = papers_dir / source["paper_id"] / "fulltext.xml"
        if not xml_path.is_file():
            raise FileNotFoundError(f"{record_id}: local JATS is missing: {xml_path}")
        xml_bytes = xml_path.read_bytes()
        source_hash = hashlib.sha256(xml_bytes).hexdigest()
        if source_hash != acquisition.get("source_sha256"):
            raise ValueError(f"{record_id}: local JATS hash mismatch")
        verified = inspect_europe_pmc_jats(
            xml_bytes,
            pmcid=source["pmcid"],
            expected_doi=source["doi"],
            source_url=acquisition.get("source_url") or None,
        )
        if slugify(verified.article_title) != source["paper_id"]:
            raise ValueError(f"{record_id}: JATS title identity mismatch")
        if verified.license_name != source.get("expected_license"):
            raise ValueError(f"{record_id}: JATS license mismatch")
        if verified.table_count != int(acquisition.get("table_count", "-1")):
            raise ValueError(f"{record_id}: table count disagrees with acquisition")
        if verified.cell_count != int(acquisition.get("cell_count", "-1")):
            raise ValueError(f"{record_id}: cell count disagrees with acquisition")

        paper = structured_paper_from_grobid_tei_path(record_id, xml_path)
        audits = [
            audit_table_structure(record_id, source["paper_id"], table)
            for table in paper.tables
        ]
        if len(audits) != verified.table_count:
            raise ValueError(f"{record_id}: parsed table count drifted")
        if sum(item.cell_count for item in audits) != verified.cell_count:
            raise ValueError(f"{record_id}: parsed cell count drifted")
        if any(item.source_sha256 != source_hash for item in audits):
            raise ValueError(f"{record_id}: parsed table source hash drifted")
        table_audits.extend(audits)
        candidates = sum(item.status == "structural_group_stats_candidate" for item in audits)
        incomplete = sum(item.status.startswith("incomplete_") for item in audits)
        excluded = sum(item.status == "excluded_non_effect_statistics" for item in audits)
        source_status = (
            "structural_candidates" if candidates
            else "no_structured_tables" if not audits
            else "no_tier1_structure"
        )
        source_audits.append(SourceTableReadinessAudit(
            record_id=record_id,
            paper_id=source["paper_id"],
            doi=expected_doi,
            source_sha256=source_hash,
            table_count=len(audits),
            cell_count=sum(item.cell_count for item in audits),
            structural_candidate_tables=candidates,
            incomplete_tables=incomplete,
            excluded_statistical_tables=excluded,
            status=source_status,
        ))
    return tuple(source_audits), tuple(table_audits)


def merge_acquisition_rows(*groups: Iterable[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Merge disjoint acquisition reports and reject conflicting duplicates."""
    merged: dict[str, Mapping[str, str]] = {}
    for rows in groups:
        for row in rows:
            existing = merged.get(row["record_id"])
            if existing is not None and dict(existing) != dict(row):
                raise ValueError(f"{row['record_id']}: conflicting acquisition rows")
            merged[row["record_id"]] = row
    return [merged[key] for key in sorted(merged)]
