"""Validate source-hash and paragraph-locator support for scope decisions."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

from ..schema import StructuredPaper


DECISIONS = {"promote_core", "promote_core_context", "exclude_wrong_cell_lineage"}
PROMOTE_DECISIONS = {"promote_core", "promote_core_context"}
REQUIRED_FIELDS = {
    "canary_id", "decision", "reason_code", "record_id", "review_id",
    "source_sha256", "cell_locators", "cell_hashes", "intervention_locators",
    "intervention_hashes", "outcome_locators", "outcome_hashes", "scope_basis",
    "transfer_limit",
}


@dataclass(frozen=True)
class ScopeReviewResult:
    rows: tuple[dict[str, str], ...]
    decision_counts: tuple[tuple[str, int], ...]
    promoted_record_ids: tuple[str, ...]
    excluded_canary_ids: tuple[str, ...]


def normalized_paragraph_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def _paragraphs(paper: StructuredPaper) -> dict[str, str]:
    return {
        paragraph.paragraph_id: paragraph.text
        for section in paper.sections
        for paragraph in section.paragraphs
    }


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def _validate_locator_group(
    row: dict[str, str], paragraphs: Mapping[str, str], locator_field: str, hash_field: str,
) -> None:
    locators = _split(row[locator_field])
    hashes = _split(row[hash_field])
    if not locators or len(locators) != len(hashes):
        raise ValueError(f"{row['canary_id']} has unpaired {locator_field}/{hash_field}")
    for locator, expected_hash in zip(locators, hashes):
        text = paragraphs.get(locator)
        if text is None:
            raise ValueError(f"{row['canary_id']} locator is absent: {locator}")
        actual_hash = normalized_paragraph_hash(text)
        if actual_hash != expected_hash:
            raise ValueError(
                f"{row['canary_id']} paragraph hash mismatch for {locator}: "
                f"{actual_hash} != {expected_hash}"
            )


def validate_scope_review(
    review_rows: Iterable[dict[str, str]],
    *,
    canary_rows: Iterable[dict[str, str]],
    verification_rows: Iterable[dict[str, str]],
    papers: Mapping[str, StructuredPaper],
    source_hashes: Mapping[str, str],
    existing_record_ids: set[str] | None = None,
    existing_review_ids: set[str] | None = None,
) -> ScopeReviewResult:
    rows = tuple(review_rows)
    if not rows:
        raise ValueError("scope review is empty")
    if REQUIRED_FIELDS - set(rows[0]):
        raise ValueError("scope review is missing required columns")
    canary = {row["canary_id"]: row for row in canary_rows}
    verification = {row["canary_id"]: row for row in verification_rows}
    expected_ids = {
        canary_id for canary_id, row in canary.items()
        if row.get("scope_role") == "direct_medium_primary"
    }
    reviewed_ids = [row["canary_id"] for row in rows]
    if len(reviewed_ids) != len(set(reviewed_ids)):
        raise ValueError("scope review contains duplicate canary IDs")
    if set(reviewed_ids) != expected_ids:
        raise ValueError("scope review must cover every direct-medium canary exactly once")

    record_ids: list[str] = []
    review_ids: list[str] = []
    excluded: list[str] = []
    counts: Counter[str] = Counter()
    for row in rows:
        canary_id = row["canary_id"]
        decision = row["decision"]
        if decision not in DECISIONS:
            raise ValueError(f"{canary_id} has unsupported decision: {decision}")
        if not row["reason_code"] or not row["scope_basis"] or not row["transfer_limit"]:
            raise ValueError(f"{canary_id} lacks a decision rationale")
        source = canary[canary_id]
        verified = verification.get(canary_id, {})
        if verified.get("status") != "verified":
            raise ValueError(f"{canary_id} is not source-verified")
        expected_source_hash = verified.get("source_sha256", "")
        if row["source_sha256"] != expected_source_hash:
            raise ValueError(f"{canary_id} review source hash disagrees with verification")
        if source_hashes.get(canary_id) != expected_source_hash:
            raise ValueError(f"{canary_id} local JATS hash disagrees with verification")
        paper = papers.get(canary_id)
        if paper is None:
            raise ValueError(f"{canary_id} local structured paper is missing")
        paragraphs = _paragraphs(paper)
        for locator_field, hash_field in (
            ("cell_locators", "cell_hashes"),
            ("intervention_locators", "intervention_hashes"),
            ("outcome_locators", "outcome_hashes"),
        ):
            _validate_locator_group(row, paragraphs, locator_field, hash_field)

        if decision in PROMOTE_DECISIONS:
            if not row["record_id"].startswith("R") or not row["review_id"].startswith("H"):
                raise ValueError(f"{canary_id} promotion lacks canonical IDs")
            record_ids.append(row["record_id"])
            review_ids.append(row["review_id"])
        else:
            if row["record_id"] != "-" or row["review_id"] != "-":
                raise ValueError(f"{canary_id} exclusion must not reserve canonical IDs")
            excluded.append(canary_id)
        counts[decision] += 1

    if len(record_ids) != len(set(record_ids)) or len(review_ids) != len(set(review_ids)):
        raise ValueError("scope review contains duplicate promotion IDs")
    if set(record_ids) & (existing_record_ids or set()):
        raise ValueError("scope review reuses an existing corpus record ID")
    if set(review_ids) & (existing_review_ids or set()):
        raise ValueError("scope review reuses an existing human-review ID")
    return ScopeReviewResult(
        rows=rows,
        decision_counts=tuple(sorted(counts.items())),
        promoted_record_ids=tuple(record_ids),
        excluded_canary_ids=tuple(excluded),
    )
