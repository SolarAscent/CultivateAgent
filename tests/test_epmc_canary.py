import csv
from pathlib import Path

from cultivate_agent.ingest.epmc_canary import (
    validate_canary_manifest, verify_canary,
)
from cultivate_agent.ingest.oa_audit import normalize_doi


def _jats(doi="10.1234/example", title="Example Bovine Paper", article_type="research-article"):
    return f'''<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="{article_type}">
      <front><article-meta>
        <article-id pub-id-type="doi">{doi}</article-id>
        <title-group><article-title>{title}</article-title></title-group>
        <permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/">
          <p>Creative Commons Attribution 4.0.</p></license></permissions>
      </article-meta></front>
      <body><table-wrap><table><tr><th>Group</th><td>2.0 ± 0.2</td></tr></table></table-wrap></body>
    </article>'''.encode()


def _rows():
    canary = [{
        "canary_id": "EBC01", "source_row": "2", "doi": "10.1234/example",
        "pmcid": "PMC123", "title": "Example Bovine Paper",
        "scope_role": "direct_medium_primary", "selection_reason": "explicit intervention",
    }]
    audit = [{
        "source_row": "2", "doi": "10.1234/example", "epmc_pmcid": "PMC123",
        "title": "Example Bovine Paper", "status": "epmc_jats_candidate",
    }]
    return canary, audit


def test_manifest_must_match_oa_audit():
    canary, audit = _rows()
    assert validate_canary_manifest(canary, audit) == tuple(canary)
    audit[0]["doi"] = "10.9999/wrong"
    try:
        validate_canary_manifest(canary, audit)
    except ValueError as exc:
        assert "DOI disagrees" in str(exc)
    else:
        raise AssertionError("DOI mismatch was accepted")


def test_verify_is_source_checked_and_checkpoint_resumable(tmp_path):
    canary, audit = _rows()
    rows = validate_canary_manifest(canary, audit)
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return _jats()

    first = verify_canary(
        rows, checkpoint_dir=tmp_path, max_downloads=1, timeout=7, fetcher=fetcher,
    )
    assert len(calls) == 1
    assert first.requests_used == 1
    assert first.rows[0]["status"] == "verified"
    assert first.rows[0]["article_type"] == "research-article"
    assert first.rows[0]["license"] == "CC-BY-4.0"
    assert first.rows[0]["table_count"] == "1"
    assert first.rows[0]["cell_count"] == "2"
    assert first.rows[0]["stat_candidate_cells"] == "1"

    second = verify_canary(
        rows, checkpoint_dir=tmp_path, max_downloads=0, timeout=1,
        fetcher=lambda *_: (_ for _ in ()).throw(AssertionError("network used")),
    )
    assert second.requests_used == 0
    assert second.checkpoints_reused == 1
    assert second.rows == first.rows


def test_budget_exhaustion_is_explicit_and_makes_no_request(tmp_path):
    canary, audit = _rows()
    result = verify_canary(
        validate_canary_manifest(canary, audit), checkpoint_dir=tmp_path,
        max_downloads=0, fetcher=lambda *_: (_ for _ in ()).throw(AssertionError("network used")),
    )
    assert result.requests_used == 0
    assert result.rows[0]["status"] == "not_run_budget_exhausted"
    assert "0/0" in result.rows[0]["error"]


def test_wrong_source_doi_fails_without_checkpoint(tmp_path):
    canary, audit = _rows()
    result = verify_canary(
        validate_canary_manifest(canary, audit), checkpoint_dir=tmp_path,
        max_downloads=1, fetcher=lambda *_: _jats(doi="10.9999/wrong"),
    )
    assert result.rows[0]["status"] == "failed"
    assert "DOI mismatch" in result.rows[0]["error"]
    assert not list(tmp_path.glob("*.xml"))


def test_wrong_source_title_fails_without_checkpoint(tmp_path):
    canary, audit = _rows()
    result = verify_canary(
        validate_canary_manifest(canary, audit), checkpoint_dir=tmp_path,
        max_downloads=1, fetcher=lambda *_: _jats(title="Unrelated Fish Scaffold Study"),
    )
    assert result.rows[0]["status"] == "failed"
    assert "title mismatch" in result.rows[0]["error"]
    assert not list(tmp_path.glob("*.xml"))


def test_non_research_article_fails_primary_canary_without_checkpoint(tmp_path):
    canary, audit = _rows()
    result = verify_canary(
        validate_canary_manifest(canary, audit), checkpoint_dir=tmp_path,
        max_downloads=1, fetcher=lambda *_: _jats(article_type="review-article"),
    )
    assert result.rows[0]["status"] == "failed"
    assert "not research-article" in result.rows[0]["error"]
    assert not list(tmp_path.glob("*.xml"))


def test_committed_canary_is_audited_scope_bound_and_source_hashed():
    root = Path(__file__).parents[1]

    def read(name):
        with (root / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    canary = read("data/literature/zotero_epmc_bovine_canary.tsv")
    audit = read("data/literature/zotero_oa_audit.tsv")
    verification = read("data/literature/zotero_epmc_bovine_canary_verification.tsv")
    scope_review = read("data/literature/zotero_epmc_bovine_scope_review.tsv")
    corpus = read("data/literature/bovine_corpus_manifest.tsv")
    assert len(validate_canary_manifest(canary, audit)) == 10
    assert sum(row["scope_role"] == "direct_medium_primary" for row in canary) == 7
    corpus_dois = {normalize_doi(row["doi"]) for row in corpus if row["doi"] != "NONE"}
    canary_by_id = {row["canary_id"]: row for row in canary}
    promoted_dois = {
        normalize_doi(canary_by_id[row["canary_id"]]["doi"])
        for row in scope_review if row["decision"].startswith("promote_")
    }
    held_dois = {
        normalize_doi(row["doi"]) for row in canary
    } - promoted_dois
    assert promoted_dois <= corpus_dois
    assert held_dois.isdisjoint(corpus_dois)
    assert [row["canary_id"] for row in verification] == [row["canary_id"] for row in canary]
    assert all(row["status"] == "verified" for row in verification)
    assert all(row["article_type"] == "research-article" for row in verification)
    assert all(len(row["source_sha256"]) == 64 for row in verification)
