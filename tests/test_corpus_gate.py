"""Tests for conservative bovine corpus Gate 1 auditing."""

from __future__ import annotations

import csv


FIELDS = [
    "record_id", "priority", "decision", "source_type", "title", "year", "doi", "url",
    "species", "cell_type", "stage", "medium_focus", "dose_or_quant", "endpoints",
    "why_included", "review_status",
]


def _row(index, *, source_type="review", bovine=False, dose=False, serum_free=False):
    return {
        "record_id": f"R{index:03d}",
        "priority": "P2",
        "decision": "context",
        "source_type": source_type,
        "title": f"Paper {index}",
        "year": "2024",
        "doi": f"10.1234/{index}",
        "url": f"https://example.org/{index}",
        "species": "bovine" if bovine else "multiple",
        "cell_type": "satellite cells" if bovine else "multiple",
        "stage": "expansion",
        "medium_focus": "serum-free medium" if serum_free else "culture medium",
        "dose_or_quant": "yes" if dose else "review-level",
        "endpoints": "proliferation",
        "why_included": "controlled test source",
        "review_status": "needs_full_text_check",
    }


def _write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_corpus_gate_passes_only_complete_human_curated_thresholds(tmp_path):
    from cultivate_agent.evaluate import audit_corpus_manifest

    rows = [_row(i, source_type="review") for i in range(1, 19)]
    for i in range(19, 36):
        bovine = i < 29
        rows.append(_row(
            i,
            source_type="primary",
            bovine=bovine,
            dose=i < 24,
            serum_free=i < 22,
        ))
    rows[18]["priority"] = "P1"
    rows[18]["decision"] = "core"
    rows[18]["review_status"] = "human_verified_included"
    manifest = tmp_path / "manifest.tsv"
    _write(manifest, rows)

    result = audit_corpus_manifest(manifest)

    assert result.metrics["peer_reviewed_sources"] == 35
    assert result.metrics["reviews"] == 18
    assert result.metrics["primary_papers"] == 17
    assert result.metrics["bovine_primary"] == 10
    assert result.metrics["dose_primary"] == 5
    assert result.metrics["serum_free_bovine_primary"] == 3
    assert result.gate_status == "PASS"


def test_corpus_gate_exposes_numeric_metadata_and_human_failures(tmp_path):
    from cultivate_agent.evaluate import audit_corpus_manifest

    row = _row(1, source_type="primary", bovine=True, dose=True, serum_free=True)
    row.update({
        "priority": "P1",
        "decision": "core",
        "doi": "UNKNOWN",
        "review_status": "needs_full_text_check",
    })
    deferred = [_row(i, source_type="review") for i in range(2, 36)]
    for item in deferred:
        item["decision"] = "defer"
    manifest = tmp_path / "manifest.tsv"
    _write(manifest, [row, *deferred])

    result = audit_corpus_manifest(manifest)

    assert result.gate_status == "FAIL"
    assert result.metrics["peer_reviewed_sources"] == 1
    assert result.checks["peer_reviewed_range"] is False
    assert result.checks["included_metadata_complete"] is False
    assert result.checks["p1_core_human_curated"] is False
    assert any(issue.category == "missing_metadata" for issue in result.issues)
    assert any(issue.category == "human_curation_pending" for issue in result.issues)


def test_corpus_gate_rejects_duplicate_record_ids_and_included_dois(tmp_path):
    from cultivate_agent.evaluate import audit_corpus_manifest

    first = _row(1, source_type="primary")
    second = _row(2, source_type="primary")
    second["record_id"] = first["record_id"]
    second["doi"] = first["doi"].upper()
    manifest = tmp_path / "manifest.tsv"
    _write(manifest, [first, second])

    result = audit_corpus_manifest(manifest)

    assert result.checks["unique_record_ids"] is False
    assert result.checks["unique_included_dois"] is False
    assert any(issue.category == "duplicate_record_id" for issue in result.issues)
    assert any(issue.category == "duplicate_doi" for issue in result.issues)
