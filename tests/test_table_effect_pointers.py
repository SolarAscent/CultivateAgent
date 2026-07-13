import hashlib
import math

import pytest
from pydantic import ValidationError

from cultivate_agent.evidence.tables import (
    TableCellRole,
    TableEffectPointers,
    TablePointerError,
    numeric_effect_from_table_pointers,
    parse_cell_number,
)
from cultivate_agent.schema import PaperTable, PaperTableCell


SOURCE_HASH = hashlib.sha256(b"source-jats").hexdigest()


def _table(*cells: tuple[str, str]) -> PaperTable:
    return PaperTable(
        table_id="T1",
        source_sha256=SOURCE_HASH,
        cells=[
            PaperTableCell(
                cell_id=cell_id,
                row_index=index,
                column_index=0,
                text=text,
            )
            for index, (cell_id, text) in enumerate(cells)
        ],
        row_count=len(cells),
        column_count=1,
    )


def _pointers(**roles: str) -> TableEffectPointers:
    return TableEffectPointers.model_validate({
        "table_id": "T1",
        "source_sha256": SOURCE_HASH,
        "pointers": [
            {"role": role, "cell_id": cell_id}
            for role, cell_id in roles.items()
        ],
    })


def test_pointer_schema_structurally_rejects_transcribed_numbers():
    payload = {
        "table_id": "T1",
        "source_sha256": SOURCE_HASH,
        "pointers": [{
            "role": "treatment_mean",
            "cell_id": "T1.R1.C1",
            "value": 2.0,
        }],
        "effect": 0.7,
    }
    with pytest.raises(ValidationError):
        TableEffectPointers.model_validate(payload)

    schema_text = str(TableEffectPointers.model_json_schema())
    assert "effect" not in schema_text
    assert "variance" not in schema_text


def test_pointer_schema_rejects_duplicate_roles_and_sd_sem_conflict():
    base = {"table_id": "T1", "source_sha256": SOURCE_HASH}
    with pytest.raises(ValidationError, match="at most once"):
        TableEffectPointers.model_validate({**base, "pointers": [
            {"role": "treatment_mean", "cell_id": "T1.R1.C1"},
            {"role": "treatment_mean", "cell_id": "T1.R2.C1"},
        ]})
    with pytest.raises(ValidationError, match="both SD and SEM"):
        TableEffectPointers.model_validate({**base, "pointers": [
            {"role": "treatment_sd", "cell_id": "T1.R1.C1"},
            {"role": "treatment_sem", "cell_id": "T1.R2.C1"},
        ]})


def test_deterministic_cells_feed_frozen_effect_seam_with_provenance():
    table = _table(
        ("T1.R1.C1", "FGF2"),
        ("T1.R1.C2", "2.0"),
        ("T1.R1.C3", "0.4"),
        ("T1.R1.C4", "n = 4"),
        ("T1.R2.C1", "Control"),
        ("T1.R2.C2", "1.0"),
        ("T1.R2.C3", "0.2"),
        ("T1.R2.C4", "4"),
        ("T1.R3.C1", "proliferation"),
        ("T1.R3.C2", "day 7"),
    )
    pointers = _pointers(
        treatment_label="T1.R1.C1",
        treatment_mean="T1.R1.C2",
        treatment_sd="T1.R1.C3",
        treatment_n="T1.R1.C4",
        control_label="T1.R2.C1",
        control_mean="T1.R2.C2",
        control_sd="T1.R2.C3",
        control_n="T1.R2.C4",
        outcome_label="T1.R3.C1",
        timepoint_label="T1.R3.C2",
    )

    result = numeric_effect_from_table_pointers(table, pointers)

    assert result.effect == pytest.approx(math.log(2.0))
    assert result.variance == pytest.approx(0.02)
    assert result.context["effect_endpoint"] == "proliferation"
    assert result.context["effect_timepoint"] == "day 7"
    assert result.context["treatment_mean_cell"] == "T1.R1.C2"
    assert result.treatment.reported_dispersion == "sd"


def test_sem_is_converted_to_sd_only_after_deterministic_n_resolution():
    table = _table(
        ("T1.R1.C1", "2.0 ± 0.2"),
        ("T1.R1.C2", "4"),
        ("T1.R2.C1", "1.0 ± 0.1"),
        ("T1.R2.C2", "n=4"),
    )
    pointers = _pointers(
        treatment_mean="T1.R1.C1",
        treatment_sem="T1.R1.C1",
        treatment_n="T1.R1.C2",
        control_mean="T1.R2.C1",
        control_sem="T1.R2.C1",
        control_n="T1.R2.C2",
    )

    result = numeric_effect_from_table_pointers(table, pointers)

    assert result.treatment.sd == pytest.approx(0.4)
    assert result.control.sd == pytest.approx(0.2)
    assert result.treatment.reported_dispersion == "sem"
    assert result.variance == pytest.approx(0.02)


def test_numeric_reader_handles_commas_and_scientific_notation_but_rejects_prose():
    comma = PaperTableCell(cell_id="T1.R1.C1", row_index=0, column_index=0, text="15,955.75")
    sci = PaperTableCell(cell_id="T1.R1.C2", row_index=0, column_index=1, text="2.00 × 10 −3")
    prose = PaperTableCell(cell_id="T1.R1.C3", row_index=0, column_index=2, text="about 4 cultures")

    assert parse_cell_number(comma, TableCellRole.TREATMENT_MEAN) == 15955.75
    assert parse_cell_number(sci, TableCellRole.TREATMENT_SD) == pytest.approx(0.002)
    with pytest.raises(TablePointerError, match="unambiguous"):
        parse_cell_number(prose, TableCellRole.TREATMENT_N)


def test_stale_hash_missing_pointer_and_incomplete_stats_fail_closed():
    table = _table(("T1.R1.C1", "2.0"))
    incomplete = _pointers(treatment_mean="T1.R1.C1")
    with pytest.raises(TablePointerError, match="incomplete"):
        numeric_effect_from_table_pointers(table, incomplete)

    missing = _pointers(
        treatment_mean="T1.R1.C1", treatment_sd="T1.R9.C1", treatment_n="T1.R9.C2",
        control_mean="T1.R9.C3", control_sd="T1.R9.C4", control_n="T1.R9.C5",
    )
    with pytest.raises(TablePointerError, match="does not exist"):
        numeric_effect_from_table_pointers(table, missing)

    stale = incomplete.model_copy(update={"source_sha256": "0" * 64})
    with pytest.raises(TablePointerError, match="source hash"):
        numeric_effect_from_table_pointers(table, stale)


def test_header_guard_rejects_timepoint_and_concentration_as_response_stats():
    table = PaperTable(
        table_id="T1",
        source_sha256=SOURCE_HASH,
        cells=[
            PaperTableCell(
                cell_id="T1.R1.C1", row_index=0, column_index=0,
                text="Serum concentration", is_header=True,
            ),
            PaperTableCell(
                cell_id="T1.R1.C2", row_index=0, column_index=1,
                text="Day 7", is_header=True,
            ),
            PaperTableCell(
                cell_id="T1.R2.C1", row_index=1, column_index=0, text="20%",
            ),
            PaperTableCell(
                cell_id="T1.R2.C2", row_index=1, column_index=1, text="1000",
            ),
        ],
        row_count=2,
        column_count=2,
    )

    with pytest.raises(TablePointerError, match="header"):
        numeric_effect_from_table_pointers(table, _pointers(
            treatment_mean="T1.R1.C2", treatment_sd="T1.R2.C2", treatment_n="T1.R2.C2",
            control_mean="T1.R2.C2", control_sd="T1.R2.C2", control_n="T1.R2.C2",
        ))
    with pytest.raises(TablePointerError, match="dose/composition"):
        numeric_effect_from_table_pointers(table, _pointers(
            treatment_mean="T1.R2.C1", treatment_sd="T1.R2.C1", treatment_n="T1.R2.C2",
            control_mean="T1.R2.C2", control_sd="T1.R2.C2", control_n="T1.R2.C2",
        ))
