import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "ingest_verified_sources.py"
SPEC = importlib.util.spec_from_file_location("ingest_verified_sources", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ingest_verified_sources = MODULE.ingest_verified_sources


def _write_sources(path: Path, pdf: Path, digest: str) -> None:
    fields = ["record_id", "title", "year", "doi", "pdf_path", "pdf_sha256", "status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerow({
            "record_id": "Z001",
            "title": "Verified Paper",
            "year": "2025",
            "doi": "10.1/example",
            "pdf_path": pdf.as_posix(),
            "pdf_sha256": digest,
            "status": "identity_license_verified",
        })


def test_ingest_verified_sources_checks_hash_before_ingest(tmp_path):
    paper_dir = tmp_path / "data" / "papers" / "verified-paper"
    paper_dir.mkdir(parents=True)
    pdf = paper_dir / "verified-paper.pdf"
    pdf.write_bytes(b"not the expected PDF")
    sources = tmp_path / "sources.tsv"
    _write_sources(sources, pdf.relative_to(tmp_path), "0" * 64)

    with pytest.raises(ValueError, match="PDF hash mismatch"):
        ingest_verified_sources(sources, papers_dir=tmp_path / "data/papers", repo_root=tmp_path)


def test_ingest_verified_sources_writes_exact_metadata(tmp_path, monkeypatch):
    paper_dir = tmp_path / "data" / "papers" / "verified-paper"
    paper_dir.mkdir(parents=True)
    pdf = paper_dir / "verified-paper.pdf"
    pdf.write_bytes(b"verified PDF bytes")
    sources = tmp_path / "sources.tsv"
    _write_sources(sources, pdf.relative_to(tmp_path), hashlib.sha256(pdf.read_bytes()).hexdigest())
    monkeypatch.setattr(
        "cultivate_agent.ingest.pdf.extract_text",
        lambda _: ("full verified text", "test", 1),
    )

    assert ingest_verified_sources(
        sources, papers_dir=tmp_path / "data/papers", repo_root=tmp_path
    ) == ["Z001"]
    metadata = json.loads((paper_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["ref"]["title"] == "Verified Paper"
    assert metadata["ref"]["doi"] == "10.1/example"
    assert (paper_dir / "fulltext.txt").read_text(encoding="utf-8") == "full verified text"
