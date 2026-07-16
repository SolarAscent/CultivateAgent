import hashlib
import csv
from pathlib import Path

import pytest

from cultivate_agent.evaluate.scope_review import (
    normalized_paragraph_hash, validate_scope_review,
)
from cultivate_agent.schema import PaperParagraph, PaperSection, StructuredPaper


ROOT = Path(__file__).resolve().parents[1]


def _read_tsv(relative_path: str) -> list[dict[str, str]]:
    with (ROOT / relative_path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _fixture():
    texts = {
        "S1.p1": "Primary bovine satellite cells were isolated from muscle.",
        "S2.p1": "Cells received a dose-defined medium supplement.",
        "S3.p1": "The proliferation endpoint was measured after culture.",
    }
    paper = StructuredPaper(
        paper_id="EBC01",
        sections=[PaperSection(
            section_id="S1", title="Paper",
            paragraphs=[PaperParagraph(paragraph_id=key, text=value) for key, value in texts.items()],
        )],
    )
    review = [{
        "canary_id": "EBC01", "decision": "promote_core_context",
        "reason_code": "in_scope", "record_id": "R100", "review_id": "H100",
        "source_sha256": "a" * 64,
        "cell_locators": "S1.p1", "cell_hashes": normalized_paragraph_hash(texts["S1.p1"]),
        "intervention_locators": "S2.p1", "intervention_hashes": normalized_paragraph_hash(texts["S2.p1"]),
        "outcome_locators": "S3.p1", "outcome_hashes": normalized_paragraph_hash(texts["S3.p1"]),
        "scope_basis": "direct bovine medium study", "transfer_limit": "serum context",
    }]
    canary = [{"canary_id": "EBC01", "scope_role": "direct_medium_primary"}]
    verification = [{"canary_id": "EBC01", "status": "verified", "source_sha256": "a" * 64}]
    return review, canary, verification, {"EBC01": paper}


def test_scope_review_resolves_all_hash_bound_locator_groups():
    review, canary, verification, papers = _fixture()
    result = validate_scope_review(
        review, canary_rows=canary, verification_rows=verification,
        papers=papers, source_hashes={"EBC01": "a" * 64},
    )
    assert result.promoted_record_ids == ("R100",)
    assert result.decision_counts == (("promote_core_context", 1),)


def test_scope_review_rejects_locator_hash_drift():
    review, canary, verification, papers = _fixture()
    review[0]["cell_hashes"] = hashlib.sha256(b"wrong").hexdigest()
    with pytest.raises(ValueError, match="paragraph hash mismatch"):
        validate_scope_review(
            review, canary_rows=canary, verification_rows=verification,
            papers=papers, source_hashes={"EBC01": "a" * 64},
        )


def test_exclusion_cannot_reserve_canonical_ids():
    review, canary, verification, papers = _fixture()
    review[0]["decision"] = "exclude_wrong_cell_lineage"
    with pytest.raises(ValueError, match="must not reserve"):
        validate_scope_review(
            review, canary_rows=canary, verification_rows=verification,
            papers=papers, source_hashes={"EBC01": "a" * 64},
        )


def test_committed_scope_promotions_are_bound_to_canonical_open_records():
    reviews = _read_tsv("data/literature/zotero_epmc_bovine_scope_review.tsv")
    corpus = _read_tsv("data/literature/bovine_corpus_manifest.tsv")
    queue = _read_tsv("data/literature/bovine_human_review_queue.tsv")
    sources = _read_tsv("data/literature/bovine_jats_source_manifest.tsv")
    acquisition = _read_tsv("data/literature/bovine_jats_acquisition_R052_R056.tsv")
    canary = {
        row["canary_id"]: row
        for row in _read_tsv("data/literature/zotero_epmc_bovine_canary.tsv")
    }
    verification = {
        row["canary_id"]: row
        for row in _read_tsv("data/literature/zotero_epmc_bovine_canary_verification.tsv")
    }
    promoted = [row for row in reviews if row["decision"].startswith("promote_")]
    excluded_dois = {
        canary[row["canary_id"]]["doi"]
        for row in reviews if row["decision"].startswith("exclude_")
    }
    corpus_by_id = {row["record_id"]: row for row in corpus}
    queue_by_id = {row["review_id"]: row for row in queue}
    source_by_id = {row["record_id"]: row for row in sources}
    acquisition_by_id = {row["record_id"]: row for row in acquisition}

    assert len(reviews) == 7
    assert {row["record_id"] for row in promoted} == {f"R{number:03d}" for number in range(52, 57)}
    assert {row["review_id"] for row in promoted} == {f"H{number:03d}" for number in range(38, 43)}
    assert set(acquisition_by_id) == {row["record_id"] for row in promoted}
    for row in promoted:
        source = canary[row["canary_id"]]
        verified = verification[row["canary_id"]]
        assert corpus_by_id[row["record_id"]]["doi"] == source["doi"]
        assert queue_by_id[row["review_id"]]["source_record_id"] == row["record_id"]
        assert queue_by_id[row["review_id"]]["status"] == "open"
        assert source_by_id[row["record_id"]]["pmcid"] == source["pmcid"]
        assert acquisition_by_id[row["record_id"]]["source_sha256"] == verified["source_sha256"]
        assert acquisition_by_id[row["record_id"]]["status"] == "existing_verified"
    assert excluded_dois.isdisjoint(row["doi"] for row in corpus)
    assert excluded_dois.isdisjoint(row["doi"] for row in sources)
