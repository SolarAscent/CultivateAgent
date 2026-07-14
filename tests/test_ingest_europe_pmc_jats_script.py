import csv
from pathlib import Path

import pytest

from scripts.ingest_europe_pmc_jats import (
    _read_manifest,
    _validate_manifest_against_corpus,
    _write_report,
)


def test_source_manifest_requires_unique_complete_rows(tmp_path):
    manifest = tmp_path / "sources.tsv"
    manifest.write_text(
        "record_id\tpaper_id\tdoi\tpmcid\texpected_license\n"
        "R1\tp1\t10.1/a\tPMC1\tCC-BY-4.0\n",
        encoding="utf-8",
    )
    assert _read_manifest(manifest)[0]["pmcid"] == "PMC1"

    manifest.write_text(
        "record_id\tpaper_id\tdoi\tpmcid\texpected_license\n"
        "R1\tp1\t10.1/a\tPMC1\tCC-BY-4.0\n"
        "R1\tp2\t10.1/b\tPMC2\tCC-BY-4.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        _read_manifest(manifest)


def test_report_writer_is_stable_tsv(tmp_path):
    report = tmp_path / "report.tsv"
    row = {
        "record_id": "R1", "paper_id": "p1", "doi": "10.1/a", "pmcid": "PMC1",
        "status": "downloaded", "license": "CC-BY-4.0", "license_url": "u",
        "source_url": "s", "source_sha256": "a" * 64, "table_count": 1,
        "cell_count": 2, "stat_candidate_cells": 0, "error": "-",
    }
    _write_report([row], report)
    with report.open(encoding="utf-8") as handle:
        loaded = list(csv.DictReader(handle, delimiter="\t"))
    assert loaded[0]["source_sha256"] == "a" * 64
    assert loaded[0]["stat_candidate_cells"] == "0"


def test_source_manifest_must_match_canonical_corpus_identity(tmp_path):
    corpus = tmp_path / "corpus.tsv"
    corpus.write_text(
        "record_id\ttitle\tdoi\n"
        "R1\tExample Paper\t10.1/a\n",
        encoding="utf-8",
    )
    rows = [{"record_id": "R1", "paper_id": "example-paper", "doi": "10.1/a"}]
    _validate_manifest_against_corpus(rows, corpus)

    rows[0]["paper_id"] = "different-paper"
    with pytest.raises(ValueError, match="canonical title"):
        _validate_manifest_against_corpus(rows, corpus)
