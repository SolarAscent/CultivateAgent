"""Pointer-only table annotations and deterministic numeric resolution.

An LLM may identify the semantic role of a source cell, but it never returns a
numeric value. This module resolves validated pointers against ``PaperTable``,
reads the source text deterministically, converts SEM to SD, and calls the
frozen effect-size seam in ``effect_operator``.
"""

from __future__ import annotations

import math
import re
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cultivate_agent.schema import PaperTable, PaperTableCell

from .effect_operator import numeric_effect_from_group_stats


class TableCellRole(str, Enum):
    TREATMENT_LABEL = "treatment_label"
    CONTROL_LABEL = "control_label"
    TREATMENT_MEAN = "treatment_mean"
    TREATMENT_SD = "treatment_sd"
    TREATMENT_SEM = "treatment_sem"
    TREATMENT_N = "treatment_n"
    CONTROL_MEAN = "control_mean"
    CONTROL_SD = "control_sd"
    CONTROL_SEM = "control_sem"
    CONTROL_N = "control_n"
    OUTCOME_LABEL = "outcome_label"
    TIMEPOINT_LABEL = "timepoint_label"


class TableCellPointer(BaseModel):
    """One semantic role assigned to one existing source cell."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: TableCellRole
    cell_id: str = Field(pattern=r"^T\d+\.R\d+\.C\d+$")


class TableEffectPointers(BaseModel):
    """The complete allowed LLM output for one treatment/control comparison."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    table_id: str = Field(pattern=r"^T\d+$")
    source_sha256: str
    pointers: List[TableCellPointer]

    @field_validator("source_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("source_sha256 must be 64 hexadecimal characters")
        return value.lower()

    @model_validator(mode="after")
    def _unique_and_consistent_roles(self):
        roles = [pointer.role for pointer in self.pointers]
        if len(roles) != len(set(roles)):
            raise ValueError("each semantic role may appear at most once")
        for group in ("treatment", "control"):
            sd = TableCellRole(f"{group}_sd")
            sem = TableCellRole(f"{group}_sem")
            if sd in roles and sem in roles:
                raise ValueError(f"{group} cannot provide both SD and SEM")
        return self

    def by_role(self) -> Dict[TableCellRole, str]:
        return {pointer.role: pointer.cell_id for pointer in self.pointers}


class ResolvedGroupStatistics(BaseModel):
    """Deterministic values plus the exact cells from which they were read."""

    mean: float
    sd: float
    n: int
    mean_cell_id: str
    dispersion_cell_id: str
    sample_size_cell_id: str
    reported_dispersion: str


class TableNumericEffect(BaseModel):
    effect: float
    variance: float
    context: Dict[str, str]
    table_id: str
    source_sha256: str
    treatment: ResolvedGroupStatistics
    control: ResolvedGroupStatistics


class TablePointerError(ValueError):
    """Raised when pointers cannot support a deterministic tier-1 effect."""


_NUMBER = r"[-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?"
_PLAIN_NUMBER_RE = re.compile(rf"^\s*(?P<value>{_NUMBER})\s*(?:%|[*†‡]|[a-z])?\s*$", re.I)
_PLUS_MINUS_RE = re.compile(
    rf"^\s*(?P<mean>{_NUMBER})\s*(?:±|\+/-|\+/−)\s*(?P<dispersion>{_NUMBER})"
    r"\s*(?:%|[*†‡]|[a-z])?\s*$",
    re.I,
)
_SCIENTIFIC_RE = re.compile(
    rf"^\s*(?P<coefficient>{_NUMBER})\s*(?:×|x)\s*10\s*(?P<exponent>[-+−]?\d+)\s*$",
    re.I,
)
_LABELLED_N_RE = re.compile(r"\bn\s*=\s*(?P<n>\d+)\b", re.I)
_NON_RESPONSE_HEADER_RE = re.compile(
    r"\b(?:concentration|dose|composition|minimum value|maximum value|factor level)\b"
    r"|(?:ng|[uμµ]g|mg|g)\s*/\s*m[lL]\b|\bm[mM]\b",
    re.I,
)


def _as_float(token: str) -> float:
    return float(token.replace(",", "").replace("−", "-"))


def parse_cell_number(cell: PaperTableCell, role: TableCellRole) -> float:
    """Read one role-specific number from source text without model transcription."""
    text = " ".join(cell.text.split())
    if role in {TableCellRole.TREATMENT_N, TableCellRole.CONTROL_N}:
        labelled = list(_LABELLED_N_RE.finditer(text))
        if len(labelled) == 1:
            return float(labelled[0].group("n"))

    combined = _PLUS_MINUS_RE.fullmatch(text)
    if combined:
        if role in {TableCellRole.TREATMENT_MEAN, TableCellRole.CONTROL_MEAN}:
            return _as_float(combined.group("mean"))
        if role in {
            TableCellRole.TREATMENT_SD,
            TableCellRole.TREATMENT_SEM,
            TableCellRole.CONTROL_SD,
            TableCellRole.CONTROL_SEM,
        }:
            return _as_float(combined.group("dispersion"))

    scientific = _SCIENTIFIC_RE.fullmatch(text)
    if scientific:
        coefficient = _as_float(scientific.group("coefficient"))
        exponent = int(scientific.group("exponent").replace("−", "-"))
        return coefficient * (10 ** exponent)

    plain = _PLAIN_NUMBER_RE.fullmatch(text)
    if plain:
        return _as_float(plain.group("value"))
    raise TablePointerError(f"{cell.cell_id} is not an unambiguous numeric source cell")


def _require_cell(table: PaperTable, cell_id: str) -> PaperTableCell:
    cell = table.cell(cell_id)
    if cell is None:
        raise TablePointerError(f"pointer {cell_id} does not exist in {table.table_id}")
    return cell


def _header_context(table: PaperTable, cell: PaperTableCell) -> List[PaperTableCell]:
    headers: List[PaperTableCell] = []
    for header in table.cells:
        if not header.is_header or header.cell_id == cell.cell_id:
            continue
        covers_column = (
            header.column_index <= cell.column_index
            < header.column_index + header.column_span
        )
        above_cell = header.row_index < cell.row_index and covers_column
        same_row_before_cell = (
            header.row_index == cell.row_index
            and header.column_index < cell.column_index
        )
        if above_cell or same_row_before_cell:
            headers.append(header)
    return headers


def _reject_non_response_context(
    table: PaperTable,
    cell: PaperTableCell,
    role: TableCellRole,
) -> None:
    if role in {
        TableCellRole.TREATMENT_MEAN,
        TableCellRole.TREATMENT_SD,
        TableCellRole.TREATMENT_SEM,
        TableCellRole.CONTROL_MEAN,
        TableCellRole.CONTROL_SD,
        TableCellRole.CONTROL_SEM,
    } and cell.is_header:
        raise TablePointerError(f"{cell.cell_id} is a header, not a response statistic")
    header_text = " | ".join(header.text for header in _header_context(table, cell))
    if _NON_RESPONSE_HEADER_RE.search(header_text):
        raise TablePointerError(
            f"{cell.cell_id} is under a dose/composition header, not a response statistic"
        )


def validate_table_pointers(table: PaperTable, pointers: TableEffectPointers) -> None:
    """Reject stale, cross-table, incomplete, or non-existent pointer sets."""
    if pointers.table_id != table.table_id:
        raise TablePointerError(
            f"pointer table {pointers.table_id} does not match source table {table.table_id}"
        )
    if table.source_sha256 is None or pointers.source_sha256 != table.source_sha256.lower():
        raise TablePointerError("pointer source hash does not match the parsed table source")
    by_role = pointers.by_role()
    required = {
        TableCellRole.TREATMENT_MEAN,
        TableCellRole.TREATMENT_N,
        TableCellRole.CONTROL_MEAN,
        TableCellRole.CONTROL_N,
    }
    missing = required - set(by_role)
    for group in ("treatment", "control"):
        sd = TableCellRole(f"{group}_sd")
        sem = TableCellRole(f"{group}_sem")
        if sd not in by_role and sem not in by_role:
            missing.add(sd)
    if missing:
        labels = ", ".join(sorted(role.value for role in missing))
        raise TablePointerError(f"incomplete pointer set; missing: {labels}")
    for cell_id in by_role.values():
        _require_cell(table, cell_id)


def _resolve_group(
    table: PaperTable,
    by_role: Dict[TableCellRole, str],
    group: str,
) -> ResolvedGroupStatistics:
    mean_role = TableCellRole(f"{group}_mean")
    n_role = TableCellRole(f"{group}_n")
    sd_role = TableCellRole(f"{group}_sd")
    sem_role = TableCellRole(f"{group}_sem")
    dispersion_role = sd_role if sd_role in by_role else sem_role

    mean_cell = _require_cell(table, by_role[mean_role])
    dispersion_cell = _require_cell(table, by_role[dispersion_role])
    n_cell = _require_cell(table, by_role[n_role])
    _reject_non_response_context(table, mean_cell, mean_role)
    _reject_non_response_context(table, dispersion_cell, dispersion_role)
    _reject_non_response_context(table, n_cell, n_role)
    mean = parse_cell_number(mean_cell, mean_role)
    dispersion = parse_cell_number(dispersion_cell, dispersion_role)
    raw_n = parse_cell_number(n_cell, n_role)
    if not raw_n.is_integer():
        raise TablePointerError(f"{n_cell.cell_id} sample size must be an integer")
    n = int(raw_n)
    sd = dispersion * math.sqrt(n) if dispersion_role == sem_role else dispersion
    return ResolvedGroupStatistics(
        mean=mean,
        sd=sd,
        n=n,
        mean_cell_id=mean_cell.cell_id,
        dispersion_cell_id=dispersion_cell.cell_id,
        sample_size_cell_id=n_cell.cell_id,
        reported_dispersion="sem" if dispersion_role == sem_role else "sd",
    )


def numeric_effect_from_table_pointers(
    table: PaperTable,
    pointers: TableEffectPointers,
) -> TableNumericEffect:
    """Resolve a pointer-only annotation into a provenance-bearing tier-1 effect."""
    validate_table_pointers(table, pointers)
    by_role = pointers.by_role()
    treatment = _resolve_group(table, by_role, "treatment")
    control = _resolve_group(table, by_role, "control")

    def optional_source_text(role: TableCellRole) -> str:
        cell_id = by_role.get(role)
        return _require_cell(table, cell_id).text if cell_id else ""

    outcome = optional_source_text(TableCellRole.OUTCOME_LABEL)
    timepoint = optional_source_text(TableCellRole.TIMEPOINT_LABEL)
    inferred = numeric_effect_from_group_stats(
        treatment.model_dump(include={"mean", "sd", "n"}),
        control.model_dump(include={"mean", "sd", "n"}),
        outcome=outcome,
        timepoint=timepoint,
    )
    if inferred.effect is None or inferred.variance is None:
        raise TablePointerError("resolved group statistics fail numeric effect guards")
    context = dict(inferred.context)
    context.update({
        "table_id": table.table_id,
        "source_sha256": pointers.source_sha256,
        "treatment_mean_cell": treatment.mean_cell_id,
        "treatment_dispersion_cell": treatment.dispersion_cell_id,
        "treatment_n_cell": treatment.sample_size_cell_id,
        "control_mean_cell": control.mean_cell_id,
        "control_dispersion_cell": control.dispersion_cell_id,
        "control_n_cell": control.sample_size_cell_id,
    })
    for role, key in (
        (TableCellRole.TREATMENT_LABEL, "treatment_label_cell"),
        (TableCellRole.CONTROL_LABEL, "control_label_cell"),
        (TableCellRole.OUTCOME_LABEL, "outcome_label_cell"),
        (TableCellRole.TIMEPOINT_LABEL, "timepoint_label_cell"),
    ):
        if role in by_role:
            context[key] = by_role[role]
    return TableNumericEffect(
        effect=inferred.effect,
        variance=inferred.variance,
        context=context,
        table_id=table.table_id,
        source_sha256=pointers.source_sha256,
        treatment=treatment,
        control=control,
    )
