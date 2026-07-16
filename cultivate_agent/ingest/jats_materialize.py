"""Materialize portable paper metadata and plain text from verified local JATS."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..schema.paper import IngestStatus, PaperMetadata, PaperRef, slugify
from ..schema.structured_paper import structured_paper_from_grobid_tei_path
from .europe_pmc import inspect_europe_pmc_jats
from .oa_audit import normalize_doi


MATERIALIZER_VERSION = "verified-jats-text-v1"
ACCEPTED_ACQUISITION_STATUS = {"downloaded", "existing_verified"}


@dataclass(frozen=True)
class JATSMaterialization:
    record_id: str
    paper_id: str
    source_sha256: str
    fulltext_sha256: str
    fulltext_chars: int
    sections: int
    tables: int
    figures: int
    has_local_pdf: bool


@dataclass(frozen=True)
class _PreparedMaterialization:
    paper_dir: Path
    fulltext_bytes: bytes
    metadata_bytes: bytes
    assets_bytes: bytes
    result: JATSMaterialization


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    os.replace(temporary, path)


def _index(rows: Sequence[dict[str, str]], name: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        record_id = row.get("record_id", "")
        if not record_id or record_id in indexed:
            raise ValueError(f"{name} has missing or duplicate record_id: {record_id!r}")
        indexed[record_id] = row
    return indexed


def materialize_verified_jats(
    *,
    corpus_rows: Sequence[dict[str, str]],
    source_rows: Sequence[dict[str, str]],
    acquisition_rows: Sequence[dict[str, str]],
    papers_dir: Path,
    record_ids: Sequence[str],
) -> tuple[JATSMaterialization, ...]:
    """Build local ingestion artifacts only after all committed identities agree."""
    corpus = _index(corpus_rows, "corpus")
    sources = _index(source_rows, "source manifest")
    acquisitions = _index(acquisition_rows, "acquisition report")
    requested = tuple(record_ids)
    if not requested or len(requested) != len(set(requested)):
        raise ValueError("record_ids must be nonempty and unique")

    prepared: list[_PreparedMaterialization] = []
    for record_id in requested:
        canonical = corpus.get(record_id)
        source = sources.get(record_id)
        acquisition = acquisitions.get(record_id)
        if canonical is None or source is None or acquisition is None:
            raise ValueError(f"{record_id}: missing canonical/source/acquisition row")
        dois = {
            normalize_doi(canonical.get("doi", "")),
            normalize_doi(source.get("doi", "")),
            normalize_doi(acquisition.get("doi", "")),
        }
        if "" in dois or len(dois) != 1:
            raise ValueError(f"{record_id}: DOI disagreement across manifests")
        if source.get("paper_id") != acquisition.get("paper_id"):
            raise ValueError(f"{record_id}: paper_id disagreement across manifests")
        if source.get("pmcid", "").upper() != acquisition.get("pmcid", "").upper():
            raise ValueError(f"{record_id}: PMCID disagreement across manifests")
        if source.get("expected_license") != acquisition.get("license"):
            raise ValueError(f"{record_id}: license disagreement across manifests")
        if acquisition.get("status") not in ACCEPTED_ACQUISITION_STATUS or acquisition.get("error") != "-":
            raise ValueError(f"{record_id}: acquisition is not verified")
        source_hash = acquisition.get("source_sha256", "")
        if len(source_hash) != 64:
            raise ValueError(f"{record_id}: acquisition source hash is invalid")
        paper_dir = papers_dir / source["paper_id"]
        xml_path = paper_dir / "fulltext.xml"
        if not xml_path.is_file():
            raise FileNotFoundError(f"{record_id}: verified local JATS is missing: {xml_path}")
        if hashlib.sha256(xml_path.read_bytes()).hexdigest() != source_hash:
            raise ValueError(f"{record_id}: local JATS hash mismatch")
        acquisition_data = inspect_europe_pmc_jats(
            xml_path.read_bytes(),
            pmcid=source["pmcid"],
            expected_doi=source["doi"],
            source_url=acquisition.get("source_url") or None,
        )
        if slugify(acquisition_data.article_title) != source["paper_id"]:
            raise ValueError(f"{record_id}: JATS title identity mismatch")
        if acquisition_data.license_name != source["expected_license"]:
            raise ValueError(f"{record_id}: JATS license mismatch")
        if acquisition_data.source_sha256 != acquisition["source_sha256"]:
            raise ValueError(f"{record_id}: verified source hash drifted during parse")
        if (
            acquisition_data.table_count != int(acquisition["table_count"])
            or acquisition_data.cell_count != int(acquisition["cell_count"])
        ):
            raise ValueError(f"{record_id}: JATS structural counts disagree with acquisition")

        paper = structured_paper_from_grobid_tei_path(
            source["paper_id"], xml_path, title=canonical["title"],
        )
        fulltext = paper.all_text().strip() + "\n"
        if not paper.sections or len(fulltext) < 500:
            raise ValueError(f"{record_id}: JATS parser produced insufficient body text")
        fulltext_bytes = fulltext.encode("utf-8")
        fulltext_hash = hashlib.sha256(fulltext_bytes).hexdigest()

        metadata_path = paper_dir / "metadata.json"
        existing = (
            PaperMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.exists() else None
        )
        if existing is not None and (
            slugify(existing.ref.title) != source["paper_id"]
            or (existing.ref.doi and normalize_doi(existing.ref.doi) != normalize_doi(source["doi"]))
        ):
            raise ValueError(f"{record_id}: existing metadata identity mismatch")
        has_pdf = any(paper_dir.glob("*.pdf"))
        status = IngestStatus(
            has_pdf=has_pdf,
            has_fulltext=True,
            n_pages=existing.status.n_pages if existing and has_pdf else 0,
            n_figures=len(paper.figures),
            n_tables=len(paper.tables),
            fulltext_chars=len(fulltext),
            text_extractor=MATERIALIZER_VERSION,
            has_structured_fulltext=True,
            structured_extractor="europe_pmc_jats",
        )
        metadata = PaperMetadata(
            ref=PaperRef(
                paper_id=source["paper_id"],
                title=canonical["title"],
                year=int(canonical["year"]),
                doi=normalize_doi(canonical["doi"]),
                url=acquisition_data.source_url,
            ),
            status=status,
        )
        assets_path = paper_dir / "assets.json"
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        allowed_asset_ids = {None, record_id, source["paper_id"]}
        if existing is not None:
            allowed_asset_ids.add(existing.ref.paper_id)
        if assets.get("paper_id") not in allowed_asset_ids:
            raise ValueError(f"{record_id}: existing assets paper_id mismatch")
        assets.update({
            "paper_id": source["paper_id"],
            "fulltext": "fulltext.txt",
            "fulltext_xml": "fulltext.xml",
            "source_kind": "europe_pmc_open_access_jats",
            "source_url": acquisition_data.source_url,
            "license": acquisition_data.license_name,
            "license_url": acquisition_data.license_url,
            "source_sha256": acquisition_data.source_sha256,
            "materializer_version": MATERIALIZER_VERSION,
            "materialized_fulltext_sha256": fulltext_hash,
        })
        result = JATSMaterialization(
            record_id=record_id,
            paper_id=source["paper_id"],
            source_sha256=acquisition_data.source_sha256,
            fulltext_sha256=fulltext_hash,
            fulltext_chars=len(fulltext),
            sections=len(paper.sections),
            tables=len(paper.tables),
            figures=len(paper.figures),
            has_local_pdf=has_pdf,
        )
        prepared.append(_PreparedMaterialization(
            paper_dir=paper_dir,
            fulltext_bytes=fulltext_bytes,
            metadata_bytes=metadata.model_dump_json(indent=2).encode("utf-8"),
            assets_bytes=json.dumps(assets, indent=2, ensure_ascii=False).encode("utf-8"),
            result=result,
        ))

    for item in prepared:
        _atomic_bytes(item.paper_dir / "fulltext.txt", item.fulltext_bytes)
        _atomic_bytes(item.paper_dir / "metadata.json", item.metadata_bytes)
        _atomic_bytes(item.paper_dir / "assets.json", item.assets_bytes)
    return tuple(item.result for item in prepared)
