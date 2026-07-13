"""Tests for the versioned dual-review full-text gold workflow."""

from __future__ import annotations

import csv
import json


def _paper(tmp_path):
    paper = tmp_path / "data/papers/paper-one"
    paper.mkdir(parents=True)
    (paper / "metadata.json").write_text(
        json.dumps({"ref": {"paper_id": "paper-one", "title": "Paper One"}}),
        encoding="utf-8",
    )
    (paper / "fulltext.txt").write_text(
        "Methods\nBovine satellite cells were maintained in expansion medium.",
        encoding="utf-8",
    )
    return paper


def _create(tmp_path):
    from cultivate_agent.evaluate.gold_review import create_gold_review

    paper = _paper(tmp_path)
    manifest = tmp_path / "gold/manifest.json"
    worksheet = tmp_path / "gold/review.tsv"
    create_gold_review(
        [("R001", paper)],
        repo_root=tmp_path,
        benchmark_version="test-v1",
        manifest_path=manifest,
        worksheet_path=worksheet,
    )
    return paper, manifest, worksheet


def _read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return reader.fieldnames, list(reader)


def _write_rows(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_blank_gold_review_is_structurally_valid_but_not_ready(tmp_path):
    from cultivate_agent.evaluate.gold_review import validate_gold_review

    _paper_dir, manifest, worksheet = _create(tmp_path)
    result = validate_gold_review(manifest, worksheet, repo_root=tmp_path)

    assert result.rows == result.expected_rows
    assert result.expected_rows > 60
    assert result.issues == []
    assert result.adjudicated_completed == 0
    assert result.ready is False


def test_gold_review_cannot_be_ready_without_both_independent_reviews():
    from cultivate_agent.evaluate.gold_review import GoldValidation

    result = GoldValidation(
        rows=1,
        expected_rows=1,
        reviewer_1_completed=0,
        reviewer_2_completed=0,
        adjudicated_completed=1,
        issues=[],
    )

    assert result.ready is False


def test_gold_review_accepts_typed_grounded_reported_value(tmp_path):
    from cultivate_agent.evaluate.gold_review import validate_gold_review

    _paper_dir, manifest, worksheet = _create(tmp_path)
    fieldnames, rows = _read_rows(worksheet)
    row = next(r for r in rows if r["block"] == "D" and r["field"] == "culture_stage")
    row.update({
        "reviewer_1_decision": "reported",
        "reviewer_1_value_json": '["expansion"]',
        "reviewer_1_quote": "satellite cells were maintained in expansion medium",
        "reviewer_1_location": "Methods",
        "reviewer_1_reviewer": "reviewer-a",
        "reviewer_1_date": "2026-07-13",
    })
    _write_rows(worksheet, fieldnames, rows)

    result = validate_gold_review(manifest, worksheet, repo_root=tmp_path)

    assert result.reviewer_1_completed == 1
    assert result.issues == []


def test_gold_review_rejects_untyped_ungrounded_and_nonreported_values(tmp_path):
    from cultivate_agent.evaluate.gold_review import validate_gold_review

    _paper_dir, manifest, worksheet = _create(tmp_path)
    fieldnames, rows = _read_rows(worksheet)
    year = next(r for r in rows if r["block"] == "A" and r["field"] == "year")
    year.update({
        "reviewer_1_decision": "reported",
        "reviewer_1_value_json": '"not-a-year"',
        "reviewer_1_quote": "this quote is absent from the full text",
        "reviewer_1_location": "Methods",
        "reviewer_1_reviewer": "reviewer-a",
        "reviewer_1_date": "2026-07-13",
    })
    title = next(r for r in rows if r["block"] == "A" and r["field"] == "title")
    title.update({
        "reviewer_2_decision": "not_reported",
        "reviewer_2_value_json": '"Paper One"',
        "reviewer_2_reviewer": "reviewer-b",
        "reviewer_2_date": "2026-07-13",
    })
    _write_rows(worksheet, fieldnames, rows)

    issues = validate_gold_review(manifest, worksheet, repo_root=tmp_path).issues

    assert any("invalid reviewer_1 value_json" in issue for issue in issues)
    assert any("reviewer_1 quote is not grounded" in issue for issue in issues)
    assert any("non-reported reviewer_2 must not contain value_json" in issue for issue in issues)


def test_gold_review_rejects_source_hash_drift(tmp_path):
    from cultivate_agent.evaluate.gold_review import validate_gold_review

    paper, manifest, worksheet = _create(tmp_path)
    (paper / "fulltext.txt").write_text("changed source", encoding="utf-8")

    issues = validate_gold_review(manifest, worksheet, repo_root=tmp_path).issues

    assert any("source hash mismatch" in issue for issue in issues)


def test_independent_reviewer_sheets_merge_into_master(tmp_path):
    from cultivate_agent.evaluate.gold_review import (
        create_reviewer_template,
        merge_independent_reviews,
        validate_gold_review,
    )

    _paper_dir, manifest, master = _create(tmp_path)
    blank = create_reviewer_template(master, tmp_path / "gold/reviewer_blank.tsv")
    reviewer_1 = tmp_path / "gold/reviewer_1.tsv"
    reviewer_2 = tmp_path / "gold/reviewer_2.tsv"
    reviewer_1.write_bytes(blank.read_bytes())
    reviewer_2.write_bytes(blank.read_bytes())

    for path, reviewer, value in (
        (reviewer_1, "reviewer-a", '["expansion", "differentiation"]'),
        (reviewer_2, "reviewer-b", '["differentiation", "expansion"]'),
    ):
        fieldnames, rows = _read_rows(path)
        row = next(r for r in rows if r["block"] == "D" and r["field"] == "culture_stage")
        row.update({
            "decision": "reported",
            "value_json": value,
            "quote": "satellite cells were maintained in expansion medium",
            "location": "Methods",
            "reviewer": reviewer,
            "date": "2026-07-13",
        })
        _write_rows(path, fieldnames, rows)

    merged = merge_independent_reviews(master, reviewer_1, reviewer_2, master)
    result = validate_gold_review(manifest, merged, repo_root=tmp_path)

    assert result.reviewer_1_completed == 1
    assert result.reviewer_2_completed == 1
    assert result.double_reviewed == 1
    assert result.decision_exact_rate == 1.0
    assert result.decision_kappa is None  # one decision class makes kappa undefined
    assert result.reported_pairs == 1
    assert result.value_exact_rate == 1.0
    assert result.issues == []


def test_gold_review_supports_manifest_controlled_field_subset(tmp_path):
    import pytest

    from cultivate_agent.evaluate.gold_review import create_gold_review, validate_gold_review

    paper = _paper(tmp_path)
    manifest = tmp_path / "pilot/manifest.json"
    worksheet = tmp_path / "pilot/review.tsv"
    fields = ["B.species", "D.cell_type", "E.medium_type"]
    create_gold_review(
        [("R001", paper)],
        repo_root=tmp_path,
        benchmark_version="pilot-v1",
        manifest_path=manifest,
        worksheet_path=worksheet,
        field_paths=fields,
    )

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = validate_gold_review(manifest, worksheet, repo_root=tmp_path)

    assert payload["field_paths"] == fields
    assert result.rows == result.expected_rows == 3
    assert result.issues == []

    with pytest.raises(ValueError, match="unknown field path"):
        create_gold_review(
            [("R001", paper)],
            repo_root=tmp_path,
            benchmark_version="bad-v1",
            manifest_path=tmp_path / "bad/manifest.json",
            worksheet_path=tmp_path / "bad/review.tsv",
            field_paths=["Z.not_a_field"],
        )


def test_gold_review_passages_locate_without_mutating_worksheet(tmp_path):
    from cultivate_agent.evaluate.gold_review import create_gold_review, gold_review_passages

    paper = _paper(tmp_path)
    manifest = tmp_path / "pilot/manifest.json"
    worksheet = tmp_path / "pilot/review.tsv"
    create_gold_review(
        [("R001", paper)],
        repo_root=tmp_path,
        benchmark_version="pilot-v1",
        manifest_path=manifest,
        worksheet_path=worksheet,
        field_paths=["D.culture_stage"],
    )
    before = worksheet.read_bytes()

    rendered = gold_review_passages(
        manifest,
        repo_root=tmp_path,
        record_ids=["R001"],
        field_paths=["D.culture_stage"],
        max_hits=1,
    )

    assert "lexical review aid only" in rendered
    assert "chars " in rendered
    assert "expansion" in rendered
    assert worksheet.read_bytes() == before
