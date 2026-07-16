import csv
from collections import Counter
from pathlib import Path

from scripts.deduplicate_zotero_acquisition import (
    deduplicate_acquisition,
    normalize_doi,
    normalize_title,
)


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def test_normalizers_handle_doi_urls_and_title_punctuation():
    assert normalize_doi(" HTTPS://doi.org/10.1000/ABC. ") == "10.1000/abc"
    assert normalize_doi("doi: 10.1000/ABC") == "10.1000/abc"
    assert normalize_title("FGF2: serum-free—medium") == "fgf2 serum free medium"
    assert normalize_title("TGF-β medium") != normalize_title("TGF medium")


def test_dedup_partitions_doi_duplicates_missing_doi_titles_and_conflicts(tmp_path):
    corpus = tmp_path / "corpus.tsv"
    _write(corpus, ["record_id", "title", "doi"], [
        {"record_id": "R1", "title": "Existing Study", "doi": "10.1/existing"},
        {"record_id": "R2", "title": "Title Only Existing", "doi": "NONE"},
    ])
    acquire = tmp_path / "acquire.tsv"
    _write(acquire, ["year", "doi", "title", "why"], [
        {"year": "2024", "doi": "https://doi.org/10.1/EXISTING", "title": "Variant", "why": "a"},
        {"year": "2024", "doi": "", "title": "Title-Only Existing", "why": "b"},
        {"year": "2024", "doi": "10.1/final", "title": "Versioned Study", "why": "c"},
        {"year": "2023", "doi": "10.1/preprint", "title": "Versioned Study", "why": "d"},
        {"year": "2024", "doi": "10.1/with-doi", "title": "Duplicate Metadata", "why": "e"},
        {"year": "2024", "doi": "", "title": "Duplicate Metadata", "why": "f"},
        {"year": "2025", "doi": "10.1/new", "title": "New Study", "why": "g"},
    ])

    result = deduplicate_acquisition(acquire, corpus)
    assert result.source_rows == 7
    assert [row["doi"] for row in result.actionable] == ["10.1/with-doi", "10.1/new"]
    assert Counter(row["reason"] for row in result.exclusions) == Counter({
        "corpus_doi_duplicate": 1,
        "corpus_title_duplicate_missing_doi": 1,
        "queue_title_duplicate_missing_doi": 1,
    })
    assert len(result.conflicts) == 2
    assert {row["doi"] for row in result.conflicts} == {"10.1/final", "10.1/preprint"}
    assert sum(dict(result.reason_counts).values()) == 7


def test_nonempty_doi_title_collision_with_corpus_is_not_auto_excluded(tmp_path):
    corpus = tmp_path / "corpus.tsv"
    _write(corpus, ["record_id", "title", "doi"], [
        {"record_id": "R1", "title": "Same Title", "doi": "10.1/final"},
    ])
    acquire = tmp_path / "acquire.tsv"
    _write(acquire, ["year", "doi", "title", "why"], [
        {"year": "2023", "doi": "10.1/preprint", "title": "Same Title", "why": "candidate"},
    ])

    result = deduplicate_acquisition(acquire, corpus)
    assert not result.actionable
    assert not result.exclusions
    assert result.conflicts[0]["reason"] == "title_match_different_doi"
    assert result.conflicts[0]["matched_record_id"] == "R1"
