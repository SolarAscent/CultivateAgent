import hashlib

from cultivate_agent.ingest.pdf_table_audit import audit_pdf_tables, is_stat_candidate
from scripts.audit_bovine_pdf_tables import _summary_markdown


class FakeTable:
    def __init__(self, rows):
        self.rows = rows

    def extract(self):
        return self.rows


class FakeFinder:
    def __init__(self, tables):
        self.tables = tables


class FakePage:
    def find_tables(self, strategy=None):
        if strategy == "text":
            return FakeFinder([FakeTable([["mean ± SD", "n = 4"], ["2.0 ± 0.4", None]])])
        return FakeFinder([FakeTable([["Group", "Value"], ["A", "2.0"]])])


class FakeDocument:
    page_count = 1

    def __iter__(self):
        return iter([FakePage()])

    def close(self):
        return None


class FakeFitz:
    @staticmethod
    def open(path):
        return FakeDocument()


def test_stat_candidate_requires_numeric_dispersion_or_explicit_stat_syntax():
    assert is_stat_candidate("2.0 ± 0.4")
    assert is_stat_candidate("mean ± SD")
    assert is_stat_candidate("n = 4")
    assert not is_stat_candidate("± ACh")
    assert not is_stat_candidate("standard culture medium")


def test_audit_keeps_line_tables_separate_from_text_layout_regions(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"test-pdf")
    result = audit_pdf_tables(pdf, fitz_module=FakeFitz)

    assert result.pdf_sha256 == hashlib.sha256(b"test-pdf").hexdigest()
    assert result.pages == 1
    assert result.lines.regions == 1
    assert result.lines.cells == 4
    assert result.lines.stat_candidate_cells == 0
    assert result.text.regions == 1
    assert result.text.cells == 3
    assert result.text.stat_candidate_cells == 3
    assert result.classification == "layout_text_candidates_only"


def test_summary_fails_off_ramp_without_promoting_text_candidates():
    row = {
        "record_id": "R1", "pdf_status": "audited", "pages": 1,
        "line_tables": 1, "line_cells": 4, "line_stat_cells": 0,
        "text_regions": 1, "text_cells": 20, "text_stat_cells": 3,
        "classification": "layout_text_candidates_only",
    }
    summary = _summary_markdown([row])
    assert "**Status: FAIL**" in summary
    assert "Gold-verified tier-1 effects produced by this audit: 0" in summary
    assert "locator candidates rather than table cells or effects" in summary
    assert "strategy=\"text\"" in summary
