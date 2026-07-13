"""Lawful, identifier-checked acquisition of Europe PMC Open Access JATS."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..schema.paper import PaperMetadata


EUROPE_PMC_REST = "https://www.ebi.ac.uk/europepmc/webservices/rest"
_PMCID_RE = re.compile(r"PMC\d+", re.I)
_CC_URL_RE = re.compile(
    r"https?://creativecommons\.org/(?:licenses|publicdomain)/[^\s\"'<>]+",
    re.I,
)


class EuropePMCError(RuntimeError):
    """Raised when remote JATS cannot be accepted safely."""


@dataclass(frozen=True)
class JATSAcquisition:
    pmcid: str
    doi: str
    source_url: str
    license_name: str
    license_url: str
    source_sha256: str
    table_count: int
    cell_count: int
    xml_bytes: bytes


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _normalize_doi(value: str) -> str:
    return value.strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")


def _classify_cc_license(license_text: str, license_url: str) -> str:
    value = f"{license_url} {license_text}".lower()
    for marker, name in (
        ("by-nc-nd/4.0", "CC-BY-NC-ND-4.0"),
        ("by-nc-sa/4.0", "CC-BY-NC-SA-4.0"),
        ("by-nc/4.0", "CC-BY-NC-4.0"),
        ("by-nd/4.0", "CC-BY-ND-4.0"),
        ("by-sa/4.0", "CC-BY-SA-4.0"),
        ("by/4.0", "CC-BY-4.0"),
        ("publicdomain/zero/1.0", "CC0-1.0"),
    ):
        if marker in value:
            return name
    if "creative commons attribution 4.0" in value:
        return "CC-BY-4.0"
    raise EuropePMCError("full-text XML lacks a recognized Creative Commons license")


def inspect_europe_pmc_jats(
    xml_bytes: bytes,
    *,
    pmcid: str,
    expected_doi: str,
    source_url: Optional[str] = None,
) -> JATSAcquisition:
    """Verify identity, license, and structural counts for one JATS document."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise EuropePMCError("response is not parseable XML") from exc
    if _local_name(root.tag) != "article":
        raise EuropePMCError("response root is not a JATS article")

    dois = {
        _normalize_doi(" ".join(element.itertext()))
        for element in root.iter()
        if _local_name(element.tag) == "article-id"
        and element.get("pub-id-type") == "doi"
    }
    expected = _normalize_doi(expected_doi)
    if expected not in dois:
        raise EuropePMCError(f"JATS DOI mismatch: expected {expected}, found {sorted(dois)}")

    license_elements = [element for element in root.iter() if _local_name(element.tag) == "license"]
    license_text = " ".join(
        " ".join(" ".join(element.itertext()).split()) for element in license_elements
    )
    hrefs = []
    for element in license_elements:
        for descendant in element.iter():
            hrefs.extend(value for key, value in descendant.attrib.items() if key.endswith("href"))
    url_match = _CC_URL_RE.search(" ".join(hrefs) + " " + license_text)
    license_url = url_match.group(0).rstrip(".,);]") if url_match else ""
    license_name = _classify_cc_license(license_text, license_url)

    table_count = sum(1 for element in root.iter() if _local_name(element.tag) == "table-wrap")
    cell_count = sum(1 for element in root.iter() if _local_name(element.tag) in {"td", "th"})
    normalized_pmcid = pmcid.upper()
    return JATSAcquisition(
        pmcid=normalized_pmcid,
        doi=expected,
        source_url=source_url or f"{EUROPE_PMC_REST}/{normalized_pmcid}/fullTextXML",
        license_name=license_name,
        license_url=license_url,
        source_sha256=hashlib.sha256(xml_bytes).hexdigest(),
        table_count=table_count,
        cell_count=cell_count,
        xml_bytes=xml_bytes,
    )


def _download(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CultivateAgent/0.1 lawful JATS acquisition"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000:
        raise EuropePMCError("JATS response exceeds the 20 MB safety limit")
    return data


def fetch_europe_pmc_jats(
    pmcid: str,
    expected_doi: str,
    *,
    timeout: int = 30,
    fetcher: Callable[[str, int], bytes] = _download,
) -> JATSAcquisition:
    normalized_pmcid = pmcid.upper()
    if not _PMCID_RE.fullmatch(normalized_pmcid):
        raise EuropePMCError(f"invalid PMCID: {pmcid}")
    source_url = f"{EUROPE_PMC_REST}/{normalized_pmcid}/fullTextXML"
    return inspect_europe_pmc_jats(
        fetcher(source_url, timeout),
        pmcid=normalized_pmcid,
        expected_doi=expected_doi,
        source_url=source_url,
    )


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    temporary.replace(path)


def acquire_europe_pmc_jats(
    paper_dir: str | Path,
    *,
    pmcid: str,
    expected_doi: str,
    expected_license: Optional[str] = None,
    timeout: int = 30,
    force: bool = False,
    fetcher: Callable[[str, int], bytes] = _download,
) -> tuple[JATSAcquisition, str]:
    """Acquire or verify ``fulltext.xml`` and merge its provenance into assets."""
    paper_dir = Path(paper_dir)
    xml_path = paper_dir / "fulltext.xml"
    if xml_path.exists() and not force:
        acquisition = inspect_europe_pmc_jats(
            xml_path.read_bytes(),
            pmcid=pmcid,
            expected_doi=expected_doi,
        )
        status = "existing_verified"
    else:
        acquisition = fetch_europe_pmc_jats(
            pmcid,
            expected_doi,
            timeout=timeout,
            fetcher=fetcher,
        )
        if expected_license and acquisition.license_name != expected_license:
            raise EuropePMCError(
                f"license mismatch: expected {expected_license}, "
                f"found {acquisition.license_name}"
            )
        if xml_path.exists() and not force:
            raise EuropePMCError(f"refusing to overwrite existing {xml_path}")
        _atomic_write(xml_path, acquisition.xml_bytes)
        status = "downloaded"

    if expected_license and acquisition.license_name != expected_license:
        raise EuropePMCError(
            f"license mismatch: expected {expected_license}, found {acquisition.license_name}"
        )

    assets_path = paper_dir / "assets.json"
    assets = json.loads(assets_path.read_text(encoding="utf-8")) if assets_path.exists() else {}
    assets.update({
        "fulltext_xml": "fulltext.xml",
        "source_kind": "europe_pmc_open_access_jats",
        "source_url": acquisition.source_url,
        "license": acquisition.license_name,
        "license_url": acquisition.license_url,
        "source_sha256": acquisition.source_sha256,
    })
    _atomic_write(assets_path, json.dumps(assets, indent=2, ensure_ascii=False).encode("utf-8"))

    metadata_path = paper_dir / "metadata.json"
    if metadata_path.exists():
        metadata = PaperMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        metadata.status.has_structured_fulltext = True
        metadata.status.structured_extractor = "europe_pmc_jats"
        metadata.ref.doi = metadata.ref.doi or acquisition.doi
        metadata.ref.url = metadata.ref.url or acquisition.source_url
        metadata.touch()
        _atomic_write(metadata_path, metadata.model_dump_json(indent=2).encode("utf-8"))
    return acquisition, status
