import json

import pytest

from cultivate_agent.ingest.europe_pmc import (
    EuropePMCError,
    acquire_europe_pmc_jats,
    fetch_europe_pmc_jats,
    inspect_europe_pmc_jats,
)


def _jats(doi="10.1234/example", license_url="https://creativecommons.org/licenses/by/4.0/"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<article xmlns:xlink="http://www.w3.org/1999/xlink">
  <front><article-meta>
    <article-id pub-id-type="doi">{doi}</article-id>
    <permissions><license xlink:href="{license_url}"><p>Creative Commons license.</p></license></permissions>
  </article-meta></front>
  <body><table-wrap><table><tr><th>Group</th><td>2.0</td></tr></table></table-wrap></body>
</article>""".encode()


def test_inspect_jats_requires_exact_doi_and_recognized_license():
    result = inspect_europe_pmc_jats(
        _jats(), pmcid="PMC123", expected_doi="10.1234/EXAMPLE"
    )
    assert result.doi == "10.1234/example"
    assert result.license_name == "CC-BY-4.0"
    assert result.table_count == 1
    assert result.cell_count == 2

    with pytest.raises(EuropePMCError, match="DOI mismatch"):
        inspect_europe_pmc_jats(_jats(), pmcid="PMC123", expected_doi="10.9999/wrong")
    with pytest.raises(EuropePMCError, match="recognized Creative Commons"):
        inspect_europe_pmc_jats(
            _jats(license_url="https://example.com/custom"),
            pmcid="PMC123",
            expected_doi="10.1234/example",
        )


def test_fetch_validates_pmcid_and_uses_bounded_injected_fetcher():
    seen = {}

    def fetcher(url, timeout):
        seen.update(url=url, timeout=timeout)
        return _jats()

    result = fetch_europe_pmc_jats("pmc123", "10.1234/example", timeout=7, fetcher=fetcher)
    assert seen == {
        "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC123/fullTextXML",
        "timeout": 7,
    }
    assert result.pmcid == "PMC123"
    with pytest.raises(EuropePMCError, match="invalid PMCID"):
        fetch_europe_pmc_jats("123", "10.1234/example", fetcher=fetcher)


def test_acquire_is_atomic_resumable_and_merges_provenance(tmp_path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "assets.json").write_text(json.dumps({"paper_id": "p1", "fulltext": "fulltext.txt"}))
    calls = 0

    def fetcher(url, timeout):
        nonlocal calls
        calls += 1
        return _jats()

    first, first_status = acquire_europe_pmc_jats(
        paper_dir, pmcid="PMC123", expected_doi="10.1234/example", fetcher=fetcher
    )
    second, second_status = acquire_europe_pmc_jats(
        paper_dir, pmcid="PMC123", expected_doi="10.1234/example", fetcher=fetcher
    )

    assert calls == 1
    assert first_status == "downloaded"
    assert second_status == "existing_verified"
    assert first.source_sha256 == second.source_sha256
    assets = json.loads((paper_dir / "assets.json").read_text())
    assert assets["paper_id"] == "p1"
    assert assets["source_kind"] == "europe_pmc_open_access_jats"
    assert assets["license"] == "CC-BY-4.0"


def test_existing_mismatched_xml_fails_without_overwrite(tmp_path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "fulltext.xml").write_bytes(_jats(doi="10.1234/other"))

    with pytest.raises(EuropePMCError, match="DOI mismatch"):
        acquire_europe_pmc_jats(
            paper_dir,
            pmcid="PMC123",
            expected_doi="10.1234/example",
            fetcher=lambda *_: _jats(),
        )


def test_expected_license_mismatch_fails_before_any_file_is_written(tmp_path):
    paper_dir = tmp_path / "paper"
    with pytest.raises(EuropePMCError, match="license mismatch"):
        acquire_europe_pmc_jats(
            paper_dir,
            pmcid="PMC123",
            expected_doi="10.1234/example",
            expected_license="CC-BY-NC-4.0",
            fetcher=lambda *_: _jats(),
        )
    assert not (paper_dir / "fulltext.xml").exists()
    assert not (paper_dir / "assets.json").exists()
