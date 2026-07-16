"""Resumable discovery of lawful full-text candidates from DOI metadata."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable


SCHEMA_VERSION = "zotero-oa-audit-v1"
EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CROSSREF_WORKS = "https://api.crossref.org/v1/works"
CC_LICENSE_RE = re.compile(
    r"^https?://creativecommons\.org/(?:licenses/(?:by(?:-nc)?(?:-nd|-sa)?|zero)/"
    r"[0-9.]+|publicdomain/zero/[0-9.]+)/?$",
    re.I,
)

OUTPUT_FIELDS = [
    "source_row", "year", "doi", "title", "why", "status",
    "epmc_pmcid", "epmc_is_open_access", "epmc_in_epmc", "epmc_source_url",
    "crossref_title", "crossref_cc_license_url", "crossref_license_version",
    "crossref_fulltext_url", "crossref_fulltext_content_type", "notes", "audit_schema",
]


class OAAuditError(RuntimeError):
    """Raised when an audit cannot continue without weakening its controls."""


@dataclass
class RequestBudget:
    limit: int
    used: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def consume(self) -> None:
        with self.lock:
            if self.used >= self.limit:
                raise OAAuditError(f"request budget exhausted ({self.used}/{self.limit})")
            self.used += 1


@dataclass(frozen=True)
class AuditResult:
    rows: tuple[dict[str, str], ...]
    status_counts: tuple[tuple[str, int], ...]
    source_sha256: str
    requests_used: int
    checkpoints_reused: int


Fetcher = Callable[[str, int], dict]


def normalize_doi(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip().lower()
    normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", normalized)
    return normalized.rstrip(" .;,")


def normalize_title(value: str) -> str:
    without_markup = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    normalized = unicodedata.normalize("NFKC", without_markup).casefold()
    return " ".join(re.sub(r"[\W_]+", " ", normalized).split())


def titles_compatible(left: str, right: str) -> bool:
    left_normalized = normalize_title(left)
    right_normalized = normalize_title(right)
    if not left_normalized or not right_normalized:
        return False
    return SequenceMatcher(None, left_normalized, right_normalized).ratio() >= 0.90


def _default_fetcher(url: str, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CultivateAgent/0.1 OA metadata audit"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(10_000_001)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"_http_status": 404}
        raise OAAuditError(f"metadata request failed with HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise OAAuditError(f"metadata request failed: {exc.reason}") from exc
    if len(data) > 10_000_000:
        raise OAAuditError("metadata response exceeds 10 MB safety limit")
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise OAAuditError("metadata response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise OAAuditError("metadata response root is not an object")
    return payload


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
    os.replace(temporary, path)


def _checkpoint_path(checkpoint_dir: Path, source: str, doi: str) -> Path:
    digest = hashlib.sha256(f"{source}\0{doi}".encode()).hexdigest()
    return checkpoint_dir / source / f"{digest}.json"


def _load_or_fetch(
    *,
    checkpoint_dir: Path,
    source: str,
    doi: str,
    url: str,
    timeout: int,
    delay_seconds: float,
    budget: RequestBudget,
    fetcher: Fetcher,
) -> tuple[dict, bool]:
    path = _checkpoint_path(checkpoint_dir, source, doi)
    if path.exists():
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if (
            envelope.get("schema_version") != SCHEMA_VERSION
            or envelope.get("source") != source
            or envelope.get("doi") != doi
            or not isinstance(envelope.get("result"), dict)
        ):
            raise OAAuditError(f"invalid checkpoint: {path}")
        return envelope["result"], True

    budget.consume()
    result = fetcher(url, timeout)
    if not isinstance(result, dict):
        raise OAAuditError(f"{source} fetcher returned a non-object")
    normalized = _normalize_source_result(source, doi, result)
    _atomic_json(path, {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "doi": doi,
        "result": normalized,
    })
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    return normalized, False


def _normalize_source_result(source: str, doi: str, payload: dict) -> dict:
    if source == "europe_pmc":
        results = payload.get("resultList", {}).get("result", [])
        exact = [item for item in results if normalize_doi(item.get("doi", "")) == doi]
        if len(exact) > 1:
            raise OAAuditError(f"Europe PMC returned multiple exact DOI matches for {doi}")
        if not exact:
            return {"found": False}
        item = exact[0]
        return {
            "found": True,
            "doi": doi,
            "title": str(item.get("title", "")),
            "pmcid": str(item.get("pmcid", "")),
            "is_open_access": str(item.get("isOpenAccess", "")),
            "in_epmc": str(item.get("inEPMC", "")),
        }
    if source == "crossref":
        if payload.get("_http_status") == 404:
            return {"found": False}
        item = payload.get("message")
        if not isinstance(item, dict):
            raise OAAuditError(f"Crossref response lacks a work record for {doi}")
        returned_doi = normalize_doi(str(item.get("DOI", "")))
        if returned_doi != doi:
            raise OAAuditError(f"Crossref DOI mismatch: expected {doi}, found {returned_doi}")
        titles = item.get("title") or []
        licenses = []
        for license_item in item.get("license") or []:
            if isinstance(license_item, dict):
                licenses.append({
                    "url": str(license_item.get("URL", "")),
                    "version": str(license_item.get("content-version", "")),
                    "delay_days": str(license_item.get("delay-in-days", "")),
                })
        links = []
        for link in item.get("link") or []:
            if isinstance(link, dict):
                links.append({
                    "url": str(link.get("URL", "")),
                    "content_type": str(link.get("content-type", "")),
                    "version": str(link.get("content-version", "")),
                    "application": str(link.get("intended-application", "")),
                })
        return {
            "found": True,
            "doi": doi,
            "title": str(titles[0]) if titles else "",
            "licenses": licenses,
            "links": links,
        }
    raise OAAuditError(f"unknown metadata source: {source}")


def _epmc_url(doi: str) -> str:
    return EUROPE_PMC_SEARCH + "?" + urllib.parse.urlencode({
        "query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": "5",
    })


def _crossref_url(doi: str) -> str:
    return f"{CROSSREF_WORKS}/{urllib.parse.quote(doi, safe='')}"


def _is_yes(value: str) -> bool:
    return value.strip().lower() in {"y", "yes", "true", "1"}


def _classify(row: dict[str, str], epmc: dict, crossref: dict) -> dict[str, str]:
    doi = normalize_doi(row.get("doi", ""))
    source_title = row.get("title", "")
    notes: list[str] = []
    identity_conflict = False
    for source, record in (("Europe PMC", epmc), ("Crossref", crossref)):
        title = record.get("title", "") if record.get("found") else ""
        if title and not titles_compatible(title, source_title):
            identity_conflict = True
            notes.append(f"{source} title mismatch")

    epmc_candidate = (
        epmc.get("found") and epmc.get("pmcid")
        and _is_yes(epmc.get("is_open_access", ""))
        and _is_yes(epmc.get("in_epmc", ""))
    )
    cc_licenses = [
        item for item in crossref.get("licenses", [])
        if CC_LICENSE_RE.fullmatch(item.get("url", "").strip())
    ]
    vor_licenses = [item for item in cc_licenses if item.get("version", "").lower() == "vor"]
    chosen_license = (vor_licenses or cc_licenses or [{}])[0]
    links = crossref.get("links", [])
    vor_links = [item for item in links if item.get("version", "").lower() == "vor"]
    chosen_link = (vor_links or links or [{}])[0]

    if identity_conflict:
        status = "identity_conflict"
    elif epmc_candidate:
        status = "epmc_jats_candidate"
    elif vor_licenses:
        status = "crossref_cc_vor_candidate"
    elif cc_licenses:
        status = "crossref_cc_other_candidate"
    elif epmc.get("found") or crossref.get("found"):
        status = "metadata_only_license_unverified"
    else:
        status = "metadata_not_found"

    pmcid = epmc.get("pmcid", "")
    return {
        "source_row": row.get("source_row", ""),
        "year": row.get("year", ""),
        "doi": doi,
        "title": source_title,
        "why": row.get("why", ""),
        "status": status,
        "epmc_pmcid": pmcid,
        "epmc_is_open_access": epmc.get("is_open_access", ""),
        "epmc_in_epmc": epmc.get("in_epmc", ""),
        "epmc_source_url": (
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            if pmcid else ""
        ),
        "crossref_title": crossref.get("title", ""),
        "crossref_cc_license_url": chosen_license.get("url", ""),
        "crossref_license_version": chosen_license.get("version", ""),
        "crossref_fulltext_url": chosen_link.get("url", ""),
        "crossref_fulltext_content_type": chosen_link.get("content_type", ""),
        "notes": "; ".join(notes),
        "audit_schema": SCHEMA_VERSION,
    }


def audit_rows(
    rows: Iterable[dict[str, str]],
    *,
    source_sha256: str,
    checkpoint_dir: Path,
    max_requests: int,
    timeout: int = 30,
    delay_seconds: float = 0.05,
    workers: int = 1,
    fetcher: Fetcher = _default_fetcher,
) -> AuditResult:
    if workers < 1:
        raise OAAuditError("workers must be at least 1")
    budget = RequestBudget(max_requests)
    indexed_rows = list(enumerate(rows, start=2))

    def process(indexed: tuple[int, dict[str, str]]) -> tuple[dict[str, str], int]:
        source_row, original = indexed
        row = {**original, "source_row": str(source_row)}
        doi = normalize_doi(row.get("doi", ""))
        if not doi:
            return ({
                **{field: row.get(field, "") for field in OUTPUT_FIELDS},
                "status": "missing_doi",
                "audit_schema": SCHEMA_VERSION,
            }, 0)
        epmc, hit = _load_or_fetch(
            checkpoint_dir=checkpoint_dir, source="europe_pmc", doi=doi,
            url=_epmc_url(doi), timeout=timeout, delay_seconds=delay_seconds,
            budget=budget, fetcher=fetcher,
        )
        reused = int(hit)
        crossref, hit = _load_or_fetch(
            checkpoint_dir=checkpoint_dir, source="crossref", doi=doi,
            url=_crossref_url(doi), timeout=timeout, delay_seconds=delay_seconds,
            budget=budget, fetcher=fetcher,
        )
        reused += int(hit)
        return _classify(row, epmc, crossref), reused

    if workers == 1:
        processed = [process(item) for item in indexed_rows]
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="oa-audit") as executor:
            processed = list(executor.map(process, indexed_rows))
    output = [row for row, _ in processed]
    reused = sum(count for _, count in processed)
    counts = Counter(row["status"] for row in output)
    return AuditResult(
        rows=tuple(output), status_counts=tuple(sorted(counts.items())),
        source_sha256=source_sha256, requests_used=budget.used,
        checkpoints_reused=reused,
    )
