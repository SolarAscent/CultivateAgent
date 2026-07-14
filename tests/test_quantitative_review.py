from __future__ import annotations

import csv
import json

from cultivate_agent.evaluate.quantitative_review import (
    COLUMNS,
    compare_quantitative_reviews,
    create_quantitative_review,
    validate_quantitative_review,
)


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self, kind, sort=True):
        assert kind == "blocks"
        assert sort is True
        return [(10.0, 20.0, 200.0, 80.0, self.text)]


class FakeDocument:
    def __init__(self, pages):
        self.pages = pages
        self.page_count = len(pages)

    def __iter__(self):
        return iter(self.pages)

    def __getitem__(self, index):
        return self.pages[index]

    def close(self):
        return None


class FakeFitz:
    pages = []

    @classmethod
    def open(cls, path):
        return FakeDocument([FakePage(text) for text in cls.pages])


def _write_tsv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path, target=2):
    paper_id = "example-paper"
    paper_dir = tmp_path / "data/papers" / paper_id
    paper_dir.mkdir(parents=True)
    (paper_dir / f"{paper_id}.pdf").write_bytes(b"source-pdf")
    corpus = tmp_path / "data/literature/corpus.tsv"
    _write_tsv(
        corpus,
        ["record_id", "title", "year", "doi"],
        [{"record_id": "R001", "title": "Example Paper", "year": "2025", "doi": "10.1/a"}],
    )
    source_spec = tmp_path / "gold/source_spec.tsv"
    _write_tsv(
        source_spec,
        ["record_id", "target_count"],
        [{"record_id": "R001", "target_count": target}],
    )
    FakeFitz.pages = [
        f"Figure {index}. Mean proliferation in medium; error bars indicate SD, n = 4."
        for index in range(1, target + 1)
    ]
    manifest = tmp_path / "gold/manifest.json"
    template = tmp_path / "gold/reviewer_blank.tsv"
    create_quantitative_review(
        source_spec,
        corpus_manifest_path=corpus,
        papers_dir=tmp_path / "data/papers",
        repo_root=tmp_path,
        benchmark_version="quant-test-v1",
        manifest_path=manifest,
        reviewer_template_path=template,
        fitz_module=FakeFitz,
    )
    return manifest, template


def _read_tsv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return reader.fieldnames, list(reader)


def _complete(path, reviewer):
    fields, rows = _read_tsv(path)
    for row in rows:
        row.update({
            "decision": "tier1_ready",
            "source_kind": "caption",
            "treatment_label": "treatment group",
            "control_label": "control group",
            "outcome": "proliferation",
            "timepoint": "reported source timepoint",
            "treatment_mean_pointer": "candidate block, treatment mark",
            "control_mean_pointer": "candidate block, control mark",
            "treatment_dispersion_pointer": "candidate block, treatment error bar",
            "control_dispersion_pointer": "candidate block, control error bar",
            "dispersion_type": "sd",
            "treatment_n_pointer": "candidate block, n statement",
            "control_n_pointer": "candidate block, n statement",
            "sample_size_status": "exact_shared",
            "replicate_type": "biological",
            "same_comparison": "yes",
            "reviewer": reviewer,
            "date": "2026-07-15",
        })
    _write_tsv(path, fields, rows)


def test_create_quantitative_review_is_bounded_pointer_only_and_hash_validated(tmp_path):
    manifest, template = _fixture(tmp_path, target=2)
    payload = json.loads(manifest.read_text())

    assert len(payload["candidates"]) == 2
    assert [row["candidate_id"] for row in payload["candidates"]] == ["Q001", "Q002"]
    assert "treatment_mean_value" not in COLUMNS
    result = validate_quantitative_review(
        manifest, template, repo_root=tmp_path, fitz_module=FakeFitz
    )
    assert result.rows == result.expected_rows == 2
    assert result.completed == 0
    assert result.issues == []

    payload["candidates"][0]["block_text_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    issues = validate_quantitative_review(
        manifest, template, repo_root=tmp_path, fitz_module=FakeFitz
    ).issues
    assert any("block text hash mismatch" in issue for issue in issues)


def test_completed_blind_reviews_report_agreement_and_tier1_gate(tmp_path):
    manifest, template = _fixture(tmp_path, target=10)
    reviewer_a = tmp_path / "reviews/a.tsv"
    reviewer_b = tmp_path / "reviews/b.tsv"
    reviewer_a.parent.mkdir()
    reviewer_a.write_bytes(template.read_bytes())
    reviewer_b.write_bytes(template.read_bytes())
    _complete(reviewer_a, "reviewer-a")
    _complete(reviewer_b, "reviewer-b")

    result = compare_quantitative_reviews(
        manifest,
        reviewer_a,
        reviewer_b,
        repo_root=tmp_path,
        fitz_module=FakeFitz,
    )

    assert result.issues == []
    assert result.decision_exact_rate == 1.0
    assert result.decision_kappa is None
    assert result.agreed_tier1 == 10
    assert result.gate_pass is True


def test_tier1_review_requires_all_role_pointers(tmp_path):
    manifest, template = _fixture(tmp_path, target=1)
    fields, rows = _read_tsv(template)
    rows[0].update({
        "decision": "tier1_ready",
        "source_kind": "caption",
        "outcome": "proliferation",
        "dispersion_type": "sd",
        "sample_size_status": "exact_shared",
        "replicate_type": "biological",
        "same_comparison": "yes",
        "reviewer": "reviewer-a",
        "date": "2026-07-15",
    })
    _write_tsv(template, fields, rows)

    issues = validate_quantitative_review(
        manifest, template, repo_root=tmp_path, fitz_module=FakeFitz
    ).issues

    assert any("requires treatment_mean_pointer" in issue for issue in issues)
    assert any("requires control_n_pointer" in issue for issue in issues)
