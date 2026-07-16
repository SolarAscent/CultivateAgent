"""Repair paper metadata from hash-bound JATS without changing source files."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from ..schema.paper import IngestStatus, PaperMetadata, PaperRef, slugify
from .europe_pmc import inspect_europe_pmc_jats


class IdentityRepairError(RuntimeError):
    """Raised when a local paper cannot be repaired from verified evidence."""


@dataclass(frozen=True)
class IdentityRepairResult:
    record_id: str
    paper_id: str
    status: str
    source_sha256: str
    fulltext_sha256: str
    pdf_sha256: str
    metadata_sha256: str
    assets_sha256: str
    quarantine_path: Optional[str]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text(element: ET.Element) -> str:
    return " ".join(" ".join(element.itertext()).split())


def _first_text(root: ET.Element, name: str) -> str:
    return next((_text(item) for item in root.iter() if _local_name(item.tag) == name), "")


def _jats_authors(root: ET.Element) -> list[str]:
    authors = []
    for contrib in root.iter():
        if _local_name(contrib.tag) != "contrib" or contrib.get("contrib-type") != "author":
            continue
        surname = _first_text(contrib, "surname")
        given = _first_text(contrib, "given-names")
        name = " ".join(part for part in (given, surname) if part)
        if name:
            authors.append(name)
    return authors


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    os.replace(temporary, path)


def _normalized_doi(value: object) -> str:
    return str(value or "").strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")


def repair_paper_identity_from_verified_jats(
    *,
    record_id: str,
    paper_dir: str | Path,
    canonical: Mapping[str, str],
    source: Mapping[str, str],
    acquisition: Mapping[str, str],
    quarantine_root: str | Path,
    pdf_audit: Optional[Mapping[str, str]] = None,
) -> IdentityRepairResult:
    """Repair only ``metadata.json`` and ``assets.json`` after strict identity checks.

    The PDF, plain text, and JATS files are immutable inputs. Existing metadata
    and assets are copied to a content-addressed quarantine directory before
    replacement, so an incorrect bibliographic merge remains auditable.
    """
    paper_dir = Path(paper_dir)
    paper_id = source.get("paper_id", "")
    expected_doi = _normalized_doi(canonical.get("doi"))
    if canonical.get("record_id") != record_id or source.get("record_id") != record_id:
        raise IdentityRepairError(f"{record_id}: record identity disagrees across manifests")
    if acquisition.get("record_id") != record_id:
        raise IdentityRepairError(f"{record_id}: acquisition record identity mismatch")
    if paper_dir.name != paper_id or slugify(canonical.get("title", "")) != paper_id:
        raise IdentityRepairError(f"{record_id}: canonical title/paper directory mismatch")
    if _normalized_doi(source.get("doi")) != expected_doi or _normalized_doi(
        acquisition.get("doi")
    ) != expected_doi:
        raise IdentityRepairError(f"{record_id}: DOI disagrees across manifests")
    if acquisition.get("status") not in {"downloaded", "existing_verified"}:
        raise IdentityRepairError(f"{record_id}: JATS acquisition is not verified")

    xml_path = paper_dir / "fulltext.xml"
    fulltext_path = paper_dir / "fulltext.txt"
    metadata_path = paper_dir / "metadata.json"
    assets_path = paper_dir / "assets.json"
    for path in (xml_path, fulltext_path, metadata_path, assets_path):
        if not path.is_file():
            raise IdentityRepairError(f"{record_id}: required local file is missing: {path.name}")

    xml_bytes = xml_path.read_bytes()
    source_hash = _sha256(xml_bytes)
    if source_hash != acquisition.get("source_sha256"):
        raise IdentityRepairError(f"{record_id}: JATS hash disagrees with acquisition report")
    verified = inspect_europe_pmc_jats(
        xml_bytes,
        pmcid=source.get("pmcid", ""),
        expected_doi=expected_doi,
        source_url=acquisition.get("source_url") or None,
    )
    if slugify(verified.article_title) != paper_id:
        raise IdentityRepairError(f"{record_id}: JATS title disagrees with canonical title")
    if verified.license_name != source.get("expected_license"):
        raise IdentityRepairError(f"{record_id}: JATS license disagrees with source manifest")

    fulltext_bytes = fulltext_path.read_bytes()
    fulltext = fulltext_bytes.decode("utf-8", errors="ignore")
    if expected_doi not in fulltext.lower():
        raise IdentityRepairError(f"{record_id}: plain text does not contain the canonical DOI")
    fulltext_hash = _sha256(fulltext_bytes)

    pdf_paths = sorted(paper_dir.glob("*.pdf"))
    if len(pdf_paths) > 1:
        raise IdentityRepairError(f"{record_id}: multiple PDFs require manual adjudication")
    pdf_hash = ""
    n_pages = 0
    if pdf_paths:
        if pdf_audit is None or pdf_audit.get("pdf_status") != "audited":
            raise IdentityRepairError(f"{record_id}: local PDF lacks a verified audit row")
        pdf_hash = _sha256(pdf_paths[0].read_bytes())
        if pdf_hash != pdf_audit.get("pdf_sha256"):
            raise IdentityRepairError(f"{record_id}: PDF hash disagrees with audit report")
        try:
            n_pages = int(pdf_audit.get("pages", ""))
        except ValueError as exc:
            raise IdentityRepairError(f"{record_id}: PDF audit page count is invalid") from exc

    old_metadata_bytes = metadata_path.read_bytes()
    old_assets_bytes = assets_path.read_bytes()
    try:
        old_metadata = PaperMetadata.model_validate_json(old_metadata_bytes)
        old_assets = json.loads(old_assets_bytes)
    except Exception as exc:
        raise IdentityRepairError(f"{record_id}: existing metadata/assets are not parseable") from exc

    root = ET.fromstring(xml_bytes)
    authors = _jats_authors(root)
    journal = _first_text(root, "journal-title") or None
    abstract = _first_text(root, "abstract") or None
    figures = sum(1 for item in root.iter() if _local_name(item.tag) == "fig")
    status = IngestStatus(
        has_pdf=bool(pdf_paths),
        has_fulltext=True,
        n_pages=n_pages,
        n_figures=figures,
        n_tables=verified.table_count,
        fulltext_chars=len(fulltext),
        text_extractor=old_metadata.status.text_extractor,
        has_structured_fulltext=True,
        structured_extractor="europe_pmc_jats",
        ingested_at=old_metadata.status.ingested_at,
        warnings=[
            warning for warning in old_metadata.status.warnings
            if "identity" not in warning.lower()
        ],
    )
    repaired_metadata = PaperMetadata(
        ref=PaperRef(
            paper_id=paper_id,
            title=canonical.get("title", verified.article_title),
            authors=authors,
            year=int(canonical["year"]),
            journal=journal,
            doi=expected_doi,
            url=canonical.get("url") or verified.source_url,
            abstract=abstract,
            pdf_path=old_metadata.ref.pdf_path,
        ),
        status=status,
        triage_category=old_metadata.triage_category,
    )
    repaired_assets = dict(old_assets)
    repaired_assets.update({
        "paper_id": paper_id,
        "fulltext": "fulltext.txt",
        "fulltext_xml": "fulltext.xml",
        "source_kind": "europe_pmc_open_access_jats",
        "source_url": verified.source_url,
        "license": verified.license_name,
        "license_url": verified.license_url,
        "source_sha256": verified.source_sha256,
    })
    metadata_bytes = repaired_metadata.model_dump_json(indent=2).encode("utf-8")
    assets_bytes = json.dumps(repaired_assets, indent=2, ensure_ascii=False).encode("utf-8")

    identity_matches = (
        old_metadata.ref.paper_id == paper_id
        and slugify(old_metadata.ref.title) == paper_id
        and _normalized_doi(old_metadata.ref.doi) == expected_doi
        and old_metadata.ref.year == int(canonical["year"])
        and old_metadata.ref.authors == authors
        and old_metadata.ref.journal == journal
        and old_metadata.ref.url == (canonical.get("url") or verified.source_url)
        and old_metadata.ref.abstract == abstract
        and old_metadata.status.has_pdf == bool(pdf_paths)
        and old_metadata.status.has_fulltext
        and old_metadata.status.n_pages == n_pages
        and old_metadata.status.n_figures == figures
        and old_metadata.status.n_tables == verified.table_count
        and old_metadata.status.fulltext_chars == len(fulltext)
        and old_metadata.status.has_structured_fulltext
        and old_metadata.status.structured_extractor == "europe_pmc_jats"
        and old_assets.get("paper_id") == paper_id
        and old_assets.get("source_kind") == "europe_pmc_open_access_jats"
        and old_assets.get("source_url") == verified.source_url
        and old_assets.get("license") == verified.license_name
        and old_assets.get("license_url") == verified.license_url
        and old_assets.get("source_sha256") == verified.source_sha256
    )
    if identity_matches:
        return IdentityRepairResult(
            record_id, paper_id, "already_verified", source_hash, fulltext_hash,
            pdf_hash, _sha256(old_metadata_bytes), _sha256(old_assets_bytes), None,
        )

    snapshot_id = _sha256(
        old_metadata_bytes + b"\0" + old_assets_bytes + b"\0" + xml_bytes
    )[:16]
    quarantine = Path(quarantine_root) / record_id / snapshot_id
    quarantine.mkdir(parents=True, exist_ok=True)
    snapshots = {
        "metadata.json": old_metadata_bytes,
        "assets.json": old_assets_bytes,
    }
    for name, payload in snapshots.items():
        target = quarantine / name
        if target.exists() and target.read_bytes() != payload:
            raise IdentityRepairError(f"{record_id}: quarantine collision for {name}")
        if not target.exists():
            _atomic_write(target, payload)
    audit = {
        "record_id": record_id,
        "paper_id": paper_id,
        "snapshot_id": snapshot_id,
        "source_sha256": source_hash,
        "fulltext_sha256": fulltext_hash,
        "pdf_sha256": pdf_hash,
        "original_metadata_sha256": _sha256(old_metadata_bytes),
        "original_assets_sha256": _sha256(old_assets_bytes),
        "observed_paper_id": old_metadata.ref.paper_id,
        "observed_doi": old_metadata.ref.doi,
        "expected_doi": expected_doi,
        "source_files_modified": False,
    }
    _atomic_write(
        quarantine / "repair_audit.json",
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    )

    try:
        _atomic_write(metadata_path, metadata_bytes)
        _atomic_write(assets_path, assets_bytes)
    except Exception:
        _atomic_write(metadata_path, old_metadata_bytes)
        _atomic_write(assets_path, old_assets_bytes)
        raise

    return IdentityRepairResult(
        record_id, paper_id, "repaired", source_hash, fulltext_hash, pdf_hash,
        _sha256(metadata_bytes), _sha256(assets_bytes), str(quarantine),
    )
