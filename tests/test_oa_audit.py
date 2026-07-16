import json

import pytest

from cultivate_agent.ingest.oa_audit import OAAuditError, audit_rows


ROWS = [{
    "year": "2025", "doi": "10.1234/example", "title": "Example Paper", "why": "test",
}, {
    "year": "2024", "doi": "", "title": "No DOI", "why": "test",
}]


def _fetcher(calls):
    def fetch(url, timeout):
        calls.append((url, timeout))
        if "europepmc" in url:
            return {"resultList": {"result": [{
                "doi": "10.1234/example", "title": "Example Paper",
                "pmcid": "PMC123", "isOpenAccess": "Y", "inEPMC": "Y",
            }]}}
        return {"message": {
            "DOI": "10.1234/example", "title": ["Example Paper"],
            "license": [{
                "URL": "https://creativecommons.org/licenses/by/4.0/",
                "content-version": "vor", "delay-in-days": 0,
            }],
            "link": [{
                "URL": "https://example.org/full.xml", "content-type": "text/xml",
                "content-version": "vor", "intended-application": "text-mining",
            }],
        }}
    return fetch


def test_audit_prefers_epmc_candidate_and_reuses_checkpoints(tmp_path):
    calls = []
    first = audit_rows(
        ROWS, source_sha256="abc", checkpoint_dir=tmp_path,
        max_requests=2, delay_seconds=0, fetcher=_fetcher(calls),
    )
    assert len(calls) == 2
    assert first.requests_used == 2
    assert first.rows[0]["status"] == "epmc_jats_candidate"
    assert first.rows[0]["epmc_source_url"].endswith("PMC123/fullTextXML")
    assert first.rows[0]["crossref_cc_license_url"].endswith("/by/4.0/")
    assert first.rows[1]["status"] == "missing_doi"
    assert all(row["audit_schema"] == "zotero-oa-audit-v1" for row in first.rows)

    second = audit_rows(
        ROWS, source_sha256="abc", checkpoint_dir=tmp_path,
        max_requests=0, delay_seconds=0, workers=2, fetcher=_fetcher(calls),
    )
    assert len(calls) == 2
    assert second.requests_used == 0
    assert second.checkpoints_reused == 2
    assert second.rows == first.rows


def test_crossref_cc_vor_is_only_a_candidate(tmp_path):
    calls = []
    fetch = _fetcher(calls)

    def without_epmc(url, timeout):
        if "europepmc" in url:
            calls.append((url, timeout))
            return {"resultList": {"result": []}}
        return fetch(url, timeout)

    result = audit_rows(
        ROWS[:1], source_sha256="abc", checkpoint_dir=tmp_path,
        max_requests=2, delay_seconds=0, fetcher=without_epmc,
    )
    assert result.rows[0]["status"] == "crossref_cc_vor_candidate"
    assert result.rows[0]["crossref_fulltext_url"] == "https://example.org/full.xml"


def test_budget_stops_before_extra_request_and_checkpoint_is_atomic(tmp_path):
    calls = []
    with pytest.raises(OAAuditError, match="budget exhausted"):
        audit_rows(
            ROWS[:1], source_sha256="abc", checkpoint_dir=tmp_path,
            max_requests=1, delay_seconds=0, fetcher=_fetcher(calls),
        )
    assert len(calls) == 1
    checkpoints = list(tmp_path.rglob("*.json"))
    assert len(checkpoints) == 1
    assert json.loads(checkpoints[0].read_text())["source"] == "europe_pmc"


def test_title_mismatch_is_quarantined(tmp_path):
    def fetch(url, timeout):
        if "europepmc" in url:
            return {"resultList": {"result": []}}
        return {"message": {
            "DOI": "10.1234/example", "title": ["Different Paper"],
            "license": [], "link": [],
        }}

    result = audit_rows(
        ROWS[:1], source_sha256="abc", checkpoint_dir=tmp_path,
        max_requests=2, delay_seconds=0, fetcher=fetch,
    )
    assert result.rows[0]["status"] == "identity_conflict"
    assert result.rows[0]["notes"] == "Crossref title mismatch"


def test_title_markup_and_minor_encoding_variants_do_not_create_conflicts(tmp_path):
    row = [{
        "year": "2025", "doi": "10.1234/example",
        "title": "Naringin targeting GSK3(3 for muscle cells", "why": "test",
    }]

    def fetch(url, timeout):
        title = "Naringin targeting <i>GSK3β</i> for muscle cells."
        if "europepmc" in url:
            return {"resultList": {"result": [{
                "doi": "10.1234/example", "title": title,
                "pmcid": "PMC123", "isOpenAccess": "Y", "inEPMC": "Y",
            }]}}
        return {"message": {
            "DOI": "10.1234/example", "title": [title], "license": [], "link": [],
        }}

    result = audit_rows(
        row, source_sha256="abc", checkpoint_dir=tmp_path,
        max_requests=2, delay_seconds=0, fetcher=fetch,
    )
    assert result.rows[0]["status"] == "epmc_jats_candidate"


def test_crossref_doi_mismatch_is_rejected(tmp_path):
    def fetch(url, timeout):
        if "europepmc" in url:
            return {"resultList": {"result": []}}
        return {"message": {"DOI": "10.9999/wrong", "title": ["Example Paper"]}}

    with pytest.raises(OAAuditError, match="DOI mismatch"):
        audit_rows(
            ROWS[:1], source_sha256="abc", checkpoint_dir=tmp_path,
            max_requests=2, delay_seconds=0, fetcher=fetch,
        )
