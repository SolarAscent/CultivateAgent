import csv
import hashlib
import json
from pathlib import Path

import pytest

from cultivate_agent.ingest import parse_bibtex
from cultivate_agent.ingest.identity_repair import (
    IdentityRepairError,
    repair_paper_identity_from_verified_jats,
)
from cultivate_agent.schema import slugify


ROOT = Path(__file__).resolve().parents[1]
JATS = b'''<article xmlns:xlink="http://www.w3.org/1999/xlink">
<front><journal-meta><journal-title>Verified Journal</journal-title></journal-meta><article-meta>
<article-id pub-id-type="doi">10.1/verified</article-id>
<title-group><article-title>Verified Paper</article-title></title-group>
<contrib-group><contrib contrib-type="author"><name><surname>Author</surname>
<given-names>Ada</given-names></name></contrib></contrib-group>
<pub-date><year>2024</year></pub-date><abstract><p>Verified abstract.</p></abstract>
<permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/">
<p>CC BY.</p></license></permissions></article-meta></front>
<body><sec><p>Body.</p></sec><fig/>
<table-wrap><table><tr><td>x</td></tr></table></table-wrap></body></article>'''


def _fixture(tmp_path):
    paper_dir = tmp_path / "verified-paper"
    paper_dir.mkdir()
    pdf = b"verified-pdf"
    fulltext = b"Verified Paper\ndoi: 10.1/verified\nBody."
    (paper_dir / "verified-paper.pdf").write_bytes(pdf)
    (paper_dir / "fulltext.txt").write_bytes(fulltext)
    (paper_dir / "fulltext.xml").write_bytes(JATS)
    old_metadata = {
        "ref": {"paper_id": "wrong", "title": "Verified Paper", "year": 2023,
                "doi": "10.1/wrong", "authors": ["Wrong Author"]},
        "status": {"has_pdf": True, "has_fulltext": True, "n_pages": 3,
                   "text_extractor": "pymupdf", "ingested_at": "fixed"},
    }
    old_assets = {"paper_id": "wrong", "fulltext": "fulltext.txt", "figures": []}
    (paper_dir / "metadata.json").write_text(json.dumps(old_metadata))
    (paper_dir / "assets.json").write_text(json.dumps(old_assets))
    canonical = {"record_id": "R001", "title": "Verified Paper", "year": "2024",
                 "doi": "10.1/verified", "url": "https://example.test/paper"}
    source = {"record_id": "R001", "paper_id": "verified-paper", "doi": "10.1/verified",
              "pmcid": "PMC1", "expected_license": "CC-BY-4.0"}
    acquisition = {"record_id": "R001", "doi": "10.1/verified", "status": "existing_verified",
                   "source_sha256": hashlib.sha256(JATS).hexdigest(),
                   "source_url": "https://example.test/jats"}
    audit = {"record_id": "R001", "pdf_status": "audited", "pages": "7",
             "pdf_sha256": hashlib.sha256(pdf).hexdigest()}
    return paper_dir, canonical, source, acquisition, audit, old_metadata, old_assets


def test_identity_repair_quarantines_metadata_only_and_is_idempotent(tmp_path):
    paper_dir, canonical, source, acquisition, audit, old_metadata, old_assets = _fixture(tmp_path)
    immutable = {name: (paper_dir / name).read_bytes() for name in
                 ("verified-paper.pdf", "fulltext.txt", "fulltext.xml")}
    result = repair_paper_identity_from_verified_jats(
        record_id="R001", paper_dir=paper_dir, canonical=canonical, source=source,
        acquisition=acquisition, quarantine_root=tmp_path / "quarantine", pdf_audit=audit,
    )
    assert result.status == "repaired"
    assert all((paper_dir / name).read_bytes() == payload for name, payload in immutable.items())
    metadata = json.loads((paper_dir / "metadata.json").read_text())
    assets = json.loads((paper_dir / "assets.json").read_text())
    assert metadata["ref"]["paper_id"] == "verified-paper"
    assert metadata["ref"]["doi"] == "10.1/verified"
    assert metadata["ref"]["authors"] == ["Ada Author"]
    assert metadata["ref"]["journal"] == "Verified Journal"
    assert metadata["status"]["n_pages"] == 7
    assert assets["source_sha256"] == hashlib.sha256(JATS).hexdigest()
    quarantine = Path(result.quarantine_path)
    assert json.loads((quarantine / "metadata.json").read_text()) == old_metadata
    assert json.loads((quarantine / "assets.json").read_text()) == old_assets
    assert json.loads((quarantine / "repair_audit.json").read_text())["source_files_modified"] is False

    replay = repair_paper_identity_from_verified_jats(
        record_id="R001", paper_dir=paper_dir, canonical=canonical, source=source,
        acquisition=acquisition, quarantine_root=tmp_path / "quarantine", pdf_audit=audit,
    )
    assert replay.status == "already_verified"


def test_identity_repair_rejects_pdf_hash_drift_without_writes(tmp_path):
    paper_dir, canonical, source, acquisition, audit, _, _ = _fixture(tmp_path)
    before = {path.name: path.read_bytes() for path in paper_dir.iterdir()}
    audit["pdf_sha256"] = "0" * 64
    with pytest.raises(IdentityRepairError, match="PDF hash"):
        repair_paper_identity_from_verified_jats(
            record_id="R001", paper_dir=paper_dir, canonical=canonical, source=source,
            acquisition=acquisition, quarantine_root=tmp_path / "quarantine", pdf_audit=audit,
        )
    assert {path.name: path.read_bytes() for path in paper_dir.iterdir()} == before
    assert not (tmp_path / "quarantine").exists()


def test_example_bibtex_identity_matches_canonical_corpus():
    refs = parse_bibtex(ROOT / "data/library.example.bib")
    with (ROOT / "data/literature/bovine_corpus_manifest.tsv").open(newline="") as handle:
        corpus = {slugify(row["title"]): row for row in csv.DictReader(handle, delimiter="\t")}
    matched = [ref for ref in refs if slugify(ref.title) in corpus]
    assert matched
    for ref in matched:
        canonical = corpus[slugify(ref.title)]
        assert ref.doi.lower() == canonical["doi"].lower()
        assert ref.year == int(canonical["year"])
