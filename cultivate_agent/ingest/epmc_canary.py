"""Source-level verification of a bounded Europe PMC candidate canary."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .europe_pmc import JATSAcquisition, fetch_europe_pmc_jats, inspect_europe_pmc_jats
from .oa_audit import normalize_doi, titles_compatible


SCHEMA_VERSION = "epmc-bovine-canary-v1"
SCOPE_ROLES = {"direct_medium_primary", "bovine_expansion_context"}
STAT_RE = re.compile(r"(?:±|\+/-|\b(?:SD|SEM|standard deviation|standard error)\b|\bn\s*=)", re.I)
REPORT_FIELDS = [
    "canary_id", "source_row", "doi", "pmcid", "title", "scope_role",
    "selection_reason", "status", "article_title", "article_type", "license", "license_url",
    "source_url", "source_sha256", "table_count", "cell_count",
    "stat_candidate_cells", "error", "verification_schema",
]


@dataclass(frozen=True)
class CanaryResult:
    rows: tuple[dict[str, str], ...]
    status_counts: tuple[tuple[str, int], ...]
    requests_used: int
    checkpoints_reused: int


Fetcher = Callable[[str, int], bytes]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _checkpoint_path(checkpoint_dir: Path, doi: str, pmcid: str) -> Path:
    key = f"{SCHEMA_VERSION}\0{normalize_doi(doi)}\0{pmcid.upper()}"
    return checkpoint_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.xml"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    os.replace(temporary, path)


def validate_canary_manifest(
    canary_rows: Iterable[dict[str, str]], audit_rows: Iterable[dict[str, str]],
) -> tuple[dict[str, str], ...]:
    rows = tuple(canary_rows)
    audits = {row.get("source_row", ""): row for row in audit_rows}
    ids = [row.get("canary_id", "") for row in rows]
    if not rows:
        raise ValueError("canary manifest is empty")
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("canary_id values must be non-empty and unique")
    identities = []
    for row in rows:
        missing = {
            field for field in (
                "source_row", "doi", "pmcid", "title", "scope_role", "selection_reason"
            ) if not row.get(field, "").strip()
        }
        if missing:
            raise ValueError(f"{row['canary_id']} missing fields: {', '.join(sorted(missing))}")
        if row["scope_role"] not in SCOPE_ROLES:
            raise ValueError(f"{row['canary_id']} has unsupported scope_role")
        audit = audits.get(row["source_row"])
        if audit is None:
            raise ValueError(f"{row['canary_id']} source_row is absent from OA audit")
        if audit.get("status") != "epmc_jats_candidate":
            raise ValueError(f"{row['canary_id']} is not an Europe PMC JATS candidate")
        if normalize_doi(audit.get("doi", "")) != normalize_doi(row["doi"]):
            raise ValueError(f"{row['canary_id']} DOI disagrees with OA audit")
        if audit.get("epmc_pmcid", "").upper() != row["pmcid"].upper():
            raise ValueError(f"{row['canary_id']} PMCID disagrees with OA audit")
        if not titles_compatible(audit.get("title", ""), row["title"]):
            raise ValueError(f"{row['canary_id']} title disagrees with OA audit")
        identities.append((normalize_doi(row["doi"]), row["pmcid"].upper()))
    if len(identities) != len(set(identities)):
        raise ValueError("canary manifest contains duplicate DOI/PMCID identities")
    return rows


def _jats_structure(xml_bytes: bytes) -> tuple[str, int]:
    root = ET.fromstring(xml_bytes)
    article_type = root.get("article-type", "")
    stat_candidate_cells = sum(
        1 for element in root.iter()
        if _local_name(element.tag) in {"td", "th"}
        and STAT_RE.search(" ".join(" ".join(element.itertext()).split()))
    )
    return article_type, stat_candidate_cells


def _verified_row(row: dict[str, str], acquisition: JATSAcquisition) -> dict[str, str]:
    if not titles_compatible(row["title"], acquisition.article_title):
        raise ValueError(
            f"JATS title mismatch: expected {row['title']!r}, found {acquisition.article_title!r}"
        )
    article_type, stat_candidate_cells = _jats_structure(acquisition.xml_bytes)
    if article_type != "research-article":
        raise ValueError(f"JATS article type is not research-article: {article_type or 'missing'}")
    return {
        **{field: row.get(field, "") for field in REPORT_FIELDS},
        "status": "verified",
        "article_title": acquisition.article_title,
        "article_type": article_type,
        "license": acquisition.license_name,
        "license_url": acquisition.license_url,
        "source_url": acquisition.source_url,
        "source_sha256": acquisition.source_sha256,
        "table_count": str(acquisition.table_count),
        "cell_count": str(acquisition.cell_count),
        "stat_candidate_cells": str(stat_candidate_cells),
        "error": "-",
        "verification_schema": SCHEMA_VERSION,
    }


def verify_canary(
    canary_rows: Iterable[dict[str, str]],
    *,
    checkpoint_dir: Path,
    max_downloads: int,
    timeout: int = 30,
    fetcher: Fetcher | None = None,
) -> CanaryResult:
    requests = 0
    reused = 0
    output: list[dict[str, str]] = []
    for row in canary_rows:
        path = _checkpoint_path(checkpoint_dir, row["doi"], row["pmcid"])
        try:
            downloaded = False
            if path.exists():
                acquisition = inspect_europe_pmc_jats(
                    path.read_bytes(), pmcid=row["pmcid"], expected_doi=row["doi"],
                )
                reused += 1
            elif requests >= max_downloads:
                output.append({
                    **{field: row.get(field, "") for field in REPORT_FIELDS},
                    "status": "not_run_budget_exhausted",
                    "error": f"download budget exhausted ({requests}/{max_downloads})",
                    "verification_schema": SCHEMA_VERSION,
                })
                continue
            else:
                requests += 1
                kwargs = {"timeout": timeout}
                if fetcher is not None:
                    kwargs["fetcher"] = fetcher
                acquisition = fetch_europe_pmc_jats(
                    row["pmcid"], row["doi"], **kwargs,
                )
                downloaded = True
            verified = _verified_row(row, acquisition)
            if downloaded:
                _atomic_write(path, acquisition.xml_bytes)
            output.append(verified)
        except Exception as exc:
            output.append({
                **{field: row.get(field, "") for field in REPORT_FIELDS},
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "verification_schema": SCHEMA_VERSION,
            })
    counts = Counter(row["status"] for row in output)
    return CanaryResult(
        rows=tuple(output), status_counts=tuple(sorted(counts.items())),
        requests_used=requests, checkpoints_reused=reused,
    )
