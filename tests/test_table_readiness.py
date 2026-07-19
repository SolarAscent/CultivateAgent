import csv
import hashlib
import re
from pathlib import Path

from cultivate_agent.evidence.table_readiness import (
    audit_table_structure,
    merge_acquisition_rows,
)
from cultivate_agent.schema import PaperTable, PaperTableCell


SOURCE_HASH = hashlib.sha256(b"table-source").hexdigest()
ROOT = Path(__file__).resolve().parents[1]


def _table(caption, headers, rows, footnotes=()):
    cells = []
    for column, text in enumerate(headers):
        cells.append(PaperTableCell(
            cell_id=f"T1.R1.C{column + 1}", row_index=0, column_index=column,
            text=text, is_header=True,
        ))
    for row_index, row in enumerate(rows, start=1):
        for column, text in enumerate(row):
            cells.append(PaperTableCell(
                cell_id=f"T1.R{row_index + 1}.C{column + 1}",
                row_index=row_index, column_index=column, text=text,
            ))
    return PaperTable(
        table_id="T1", source_table_id="source-1", caption=caption,
        footnotes=list(footnotes), cells=cells, row_count=1 + len(rows),
        column_count=len(headers), source_sha256=SOURCE_HASH,
    )


def test_footnote_sample_size_does_not_satisfy_cell_only_pointer_contract():
    table = _table(
        "Cell proliferation by medium treatment",
        ["Outcome", "Control", "FGF2"],
        [["Day 7 cell count", "1.0 +/- 0.1", "2.0 +/- 0.2"]],
        ["Values are mean +/- S.D. (n = 4)."],
    )
    result = audit_table_structure("R001", "paper", table)
    assert result.status == "incomplete_sample_size_not_cell_addressable"
    assert result.combined_stat_cell_ids == ("T1.R2.C2", "T1.R2.C3")
    assert result.sample_size_context_ids == ("T1.F1",)
    assert result.dispersion_kind == "sd"


def test_composition_statistics_are_excluded_even_when_sd_and_n_are_complete():
    table = _table(
        "Vitamin concentrations in ingredient powder",
        ["Vitamin", "Content"],
        [["A", "1.0 +/- 0.1"], ["B", "2.0 +/- 0.2"]],
        ["Values are mean +/- SD (n = 3)."],
    )
    result = audit_table_structure("R001", "paper", table)
    assert result.status == "excluded_non_effect_statistics"
    assert result.exclusion_reason == "composition_or_resource_statistics"


def test_response_sem_table_without_n_is_incomplete():
    table = _table(
        "Gene expression during cell proliferation",
        ["Gene", "Control", "Treatment", "SEM"],
        [["MYOD1", "1.0", "1.5", "0.2"], ["PAX7", "1.0", "1.2", "0.1"]],
    )
    result = audit_table_structure("R001", "paper", table)
    assert result.status == "incomplete_missing_sample_size"
    assert result.dispersion_context_ids == ("T1.R1.C4",)
    assert result.sample_size_cell_ids == ()


def test_response_context_is_not_excluded_by_concentration_or_p_value_columns():
    table = _table(
        "Gene expression during cell proliferation by glucose concentration",
        ["Gene", "Control", "Treatment", "SEM", "p-value"],
        [["MYOD1", "1.0", "1.5", "0.2", "0.01"]],
    )
    result = audit_table_structure("R001", "paper", table)
    assert result.status == "incomplete_missing_sample_size"
    assert result.exclusion_reason == "-"


def test_n_header_resolves_only_numeric_cells_below_that_column():
    table = _table(
        "Cell viability by treatment",
        ["Group", "Mean", "SD", "n"],
        [["Control", "1.0", "0.1", "4"], ["Treatment", "2.0", "0.2", "4"]],
    )
    result = audit_table_structure("R001", "paper", table)
    assert result.status == "structural_group_stats_candidate"
    assert result.sample_size_cell_ids == ("T1.R2.C4", "T1.R3.C4")


def test_merge_acquisition_rows_rejects_conflicts():
    row = {"record_id": "R001", "source_sha256": "a"}
    assert merge_acquisition_rows([row], [row]) == [row]
    try:
        merge_acquisition_rows([row], [{"record_id": "R001", "source_sha256": "b"}])
    except ValueError as exc:
        assert "conflicting" in str(exc)
    else:
        raise AssertionError("conflicting acquisition rows were accepted")


def test_committed_bovine_jats_audit_is_pointer_only_and_source_bound():
    with (ROOT / "data/literature/bovine_jats_group_stats_source_audit.tsv").open(
        newline=""
    ) as handle:
        sources = list(csv.DictReader(handle, delimiter="\t"))
    with (ROOT / "data/literature/bovine_jats_group_stats_table_audit.tsv").open(
        newline=""
    ) as handle:
        tables = list(csv.DictReader(handle, delimiter="\t"))
    acquisition = {}
    for name in ("bovine_jats_acquisition.tsv", "bovine_jats_acquisition_R052_R056.tsv"):
        with (ROOT / "data/literature" / name).open(newline="") as handle:
            acquisition.update({
                row["record_id"]: row for row in csv.DictReader(handle, delimiter="\t")
            })

    assert len(sources) == 14
    assert len(tables) == 37
    assert sum(int(row["cell_count"]) for row in tables) == 2103
    assert sum(int(row["structural_candidate_tables"]) for row in sources) == 0
    assert all(row["source_sha256"] == acquisition[row["record_id"]]["source_sha256"]
               for row in sources)
    forbidden_columns = {"value", "mean", "sd", "sem", "n", "effect", "variance"}
    assert forbidden_columns.isdisjoint(tables[0])
    pointer_re = re.compile(r"^T\d+\.(?:R\d+\.C\d+|F\d+|CAPTION)$")
    pointer_columns = (
        "combined_stat_cell_ids", "sample_size_cell_ids",
        "sample_size_context_ids", "dispersion_context_ids",
    )
    for row in tables:
        for column in pointer_columns:
            assert all(pointer_re.fullmatch(pointer) for pointer in row[column].split(";")
                       if pointer != "-")
