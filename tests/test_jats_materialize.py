import hashlib
import json
import csv
from pathlib import Path

import pytest

from cultivate_agent.ingest.jats_materialize import materialize_verified_jats


ROOT = Path(__file__).resolve().parents[1]


def _read_tsv(relative_path):
    with (ROOT / relative_path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


JATS = b'''<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article">
<front><article-meta><article-id pub-id-type="doi">10.1/example</article-id>
<title-group><article-title>Verified JATS Paper</article-title></title-group>
<permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/">
<p>Creative Commons Attribution 4.0.</p></license></permissions></article-meta></front>
<body><sec><title>Methods</title><p>Primary bovine satellite cells were cultured in medium.</p></sec>
<sec><title>Results</title><p>Proliferation and differentiation were measured repeatedly in culture.</p>
<p>This sufficiently long fixture paragraph verifies deterministic body materialization without network access. It describes medium preparation, primary cell culture, controlled comparisons, proliferation measurements, and myogenic identity checks.</p>
<p>The second fixture paragraph adds enough source-authentic structure for the minimum-body guard while making no scientific claim outside this synthetic test. It repeats the concepts of culture medium, treatment groups, cell counts, and differentiation endpoints.</p>
<p>The final fixture paragraph confirms that multiple JATS sections and paragraphs are serialized consistently. The materializer must preserve section ordering, source identity, and the verified XML hash before it writes local review text.</p></sec></body>
</article>'''


def _rows(tmp_path):
    paper_id = "verified-jats-paper"
    paper_dir = tmp_path / paper_id
    paper_dir.mkdir()
    (paper_dir / "fulltext.xml").write_bytes(JATS)
    (paper_dir / "assets.json").write_text(json.dumps({"paper_id": paper_id}))
    digest = hashlib.sha256(JATS).hexdigest()
    corpus = [{"record_id": "R001", "title": "Verified JATS Paper", "year": "2025",
               "doi": "10.1/example"}]
    sources = [{"record_id": "R001", "paper_id": paper_id, "doi": "10.1/example",
                "pmcid": "PMC123", "expected_license": "CC-BY-4.0"}]
    acquisition = [{"record_id": "R001", "paper_id": paper_id, "doi": "10.1/example",
                    "pmcid": "PMC123", "status": "existing_verified", "license": "CC-BY-4.0",
                    "source_sha256": digest, "table_count": "0", "cell_count": "0", "error": "-"}]
    return corpus, sources, acquisition, paper_dir


def test_materialize_verified_jats_writes_hash_bound_portable_assets(tmp_path):
    corpus, sources, acquisition, paper_dir = _rows(tmp_path)
    result = materialize_verified_jats(
        corpus_rows=corpus, source_rows=sources, acquisition_rows=acquisition,
        papers_dir=tmp_path, record_ids=["R001"],
    )
    assert len(result) == 1
    text = (paper_dir / "fulltext.txt").read_text()
    metadata = json.loads((paper_dir / "metadata.json").read_text())
    assets = json.loads((paper_dir / "assets.json").read_text())
    assert text.startswith("Verified JATS Paper")
    assert metadata["ref"]["doi"] == "10.1/example"
    assert metadata["status"]["text_extractor"] == "verified-jats-text-v1"
    assert assets["materialized_fulltext_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert result[0].source_sha256 == acquisition[0]["source_sha256"]


def test_materialize_verified_jats_rejects_hash_drift_before_writing(tmp_path):
    corpus, sources, acquisition, paper_dir = _rows(tmp_path)
    acquisition[0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="local JATS hash mismatch"):
        materialize_verified_jats(
            corpus_rows=corpus, source_rows=sources, acquisition_rows=acquisition,
            papers_dir=tmp_path, record_ids=["R001"],
        )
    assert not (paper_dir / "fulltext.txt").exists()


def test_materialize_verified_jats_refuses_missing_local_xml_without_network(tmp_path):
    corpus, sources, acquisition, paper_dir = _rows(tmp_path)
    (paper_dir / "fulltext.xml").unlink()
    with pytest.raises(FileNotFoundError, match="verified local JATS is missing"):
        materialize_verified_jats(
            corpus_rows=corpus, source_rows=sources, acquisition_rows=acquisition,
            papers_dir=tmp_path, record_ids=["R001"],
        )


def test_materialize_verified_jats_validates_whole_batch_before_writing(tmp_path):
    corpus, sources, acquisition, first_dir = _rows(tmp_path)
    second_xml = JATS.replace(b"10.1/example", b"10.1/second").replace(
        b"Verified JATS Paper", b"Second JATS Paper"
    )
    second_dir = tmp_path / "second-jats-paper"
    second_dir.mkdir()
    (second_dir / "fulltext.xml").write_bytes(second_xml)
    (second_dir / "assets.json").write_text(json.dumps({"paper_id": "second-jats-paper"}))
    corpus.append({"record_id": "R002", "title": "Second JATS Paper", "year": "2025",
                   "doi": "10.1/second"})
    sources.append({"record_id": "R002", "paper_id": "second-jats-paper",
                    "doi": "10.1/second", "pmcid": "PMC124",
                    "expected_license": "CC-BY-4.0"})
    acquisition.append({"record_id": "R002", "paper_id": "second-jats-paper",
                        "doi": "10.1/second", "pmcid": "PMC124",
                        "status": "existing_verified", "license": "CC-BY-4.0",
                        "source_sha256": hashlib.sha256(second_xml).hexdigest(),
                        "table_count": "1", "cell_count": "0", "error": "-"})
    with pytest.raises(ValueError, match="structural counts disagree"):
        materialize_verified_jats(
            corpus_rows=corpus, source_rows=sources, acquisition_rows=acquisition,
            papers_dir=tmp_path, record_ids=["R001", "R002"],
        )
    assert not (first_dir / "fulltext.txt").exists()
    assert not (second_dir / "fulltext.txt").exists()


def test_committed_materialization_binds_new_review_packet_and_readiness():
    materialized = _read_tsv("data/literature/bovine_jats_materialization_R052_R056.tsv")
    acquisition = {
        row["record_id"]: row
        for row in _read_tsv("data/literature/bovine_jats_acquisition_R052_R056.tsv")
    }
    scope = {
        row["record_id"]: row["review_id"]
        for row in _read_tsv("data/literature/zotero_epmc_bovine_scope_review.tsv")
        if row["decision"].startswith("promote_")
    }
    readiness = _read_tsv("data/literature/bovine_extraction_readiness_H038_H042.tsv")
    packet = (ROOT / "docs/HUMAN_REVIEW_PACKET_H038_H042.md").read_text()
    expected_ids = {f"R{number:03d}" for number in range(52, 57)}

    assert {row["record_id"] for row in materialized} == expected_ids
    assert len(readiness) == 25
    assert {row["review_id"] for row in readiness} == set(scope.values())
    assert all(row["status"] == "ready_for_operator_extraction" for row in readiness)
    assert all(row["structured_source"] == "jats_xml" for row in readiness)
    for row in materialized:
        assert row["status"] == "materialized_from_verified_jats"
        assert row["source_sha256"] == acquisition[row["record_id"]]["source_sha256"]
        assert row["fulltext_sha256"] in packet
        matching = [item for item in readiness if item["source_record_id"] == row["record_id"]]
        assert {item["text_chars"] for item in matching} == {row["fulltext_chars"]}
