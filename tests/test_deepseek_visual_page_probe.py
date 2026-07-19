import hashlib
import json

from cultivate_agent.evaluate.deepseek_locator_probe import run_locator_probe
from cultivate_agent.evaluate.deepseek_visual_page_probe import (
    PDF_HELDOUT_SELECTOR_VERSION,
    PROMPT_VERSION,
    build_visual_page_prompt,
    build_pdf_visual_heldout_manifest,
    audit_pdf_visual_shadow,
    build_visual_silver_manifest,
    deployment_gate_pass,
    load_visual_page_silver,
    result_manifest,
    validate_pdf_visual_shadow_audit,
    validate_result_manifest,
)


class _Page:
    def __init__(self, text):
        self.text = text

    def get_text(self, kind="text", sort=True):
        del sort
        if kind == "blocks":
            return [(0, 0, 0, 0, self.text)]
        return self.text


class _Document(list):
    def close(self):
        pass


class _Fitz:
    def __init__(self, pages):
        self.pages = pages

    def open(self, _path):
        return _Document(_Page(text) for text in self.pages)


def _fixture(tmp_path):
    paper_id = "paper"
    directory = tmp_path / "data/papers" / paper_id
    directory.mkdir(parents=True)
    caption = (
        "Cell proliferation in control and treatment medium. Data are mean and standard "
        "deviation from n = 3 independent replicates."
    )
    xml = directory / "fulltext.xml"
    xml.write_text(
        f"<article><fig id='F1'><caption><p>{caption}</p></caption></fig></article>",
        encoding="utf-8",
    )
    pdf = directory / "paper.pdf"
    pdf.write_bytes(b"pdf")
    pages = ["Introduction only.", caption, "Discussion only."]
    source = [{"record_id": "R1", "paper_id": paper_id}]
    acquisition = [{
        "record_id": "R1", "paper_id": paper_id,
        "source_sha256": hashlib.sha256(xml.read_bytes()).hexdigest(),
    }]
    audit = [{
        "record_id": "R1", "paper_id": paper_id,
        "pdf_path": str(pdf.relative_to(tmp_path)),
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
    }]
    return source, acquisition, audit, _Fitz(pages)


def test_build_and_load_visual_silver_uses_hash_bound_pointers_only(tmp_path):
    source, acquisition, audit, fitz = _fixture(tmp_path)
    payload = build_visual_silver_manifest(
        ["R1"], jats_sources=source, jats_acquisitions=acquisition, pdf_audits=audit,
        repo_root=tmp_path, fitz_module=fitz,
    )
    assert payload["candidates"][0]["pdf_page"] == 2
    assert "cell proliferation in control" not in json.dumps(payload).casefold()
    manifest = tmp_path / "silver.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    items = load_visual_page_silver(manifest, repo_root=tmp_path, fitz_module=fitz)
    assert len(items) == 3
    assert [item.pdf_page for item in items if item.positive] == [2]


def test_visual_gate_requires_recall_stability_and_work_reduction(tmp_path):
    source, acquisition, audit, fitz = _fixture(tmp_path)
    payload = build_visual_silver_manifest(
        ["R1"], jats_sources=source, jats_acquisitions=acquisition, pdf_audits=audit,
        repo_root=tmp_path, fitz_module=fitz,
    )
    manifest = tmp_path / "silver.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    items = load_visual_page_silver(manifest, repo_root=tmp_path, fitz_module=fitz)
    positive_id = next(item.item_id for item in items if item.positive)

    def caller(_prompt, _max_tokens):
        return json.dumps({"candidate_ids": [positive_id]}), {"total_tokens": 10}

    result = run_locator_probe(
        items, checkpoint_dir=tmp_path / "cp", model="test", repeats=3,
        batch_size=3, max_requests=3, max_total_tokens=1000, max_output_tokens=50,
        caller=caller, prompt_builder=build_visual_page_prompt,
        prompt_version=PROMPT_VERSION,
    )
    assert deployment_gate_pass(result, max_selected_fraction=0.60)
    output = result_manifest(result, items, model="test")
    assert validate_result_manifest(output, items) == []
    assert all(set(row) == {
        "candidate_id", "record_id", "pdf_page", "page_excerpt_sha256"
    } for repeat in output["repeat_selections"] for row in repeat)


def test_visual_gate_rejects_select_every_page(tmp_path):
    source, acquisition, audit, fitz = _fixture(tmp_path)
    payload = build_visual_silver_manifest(
        ["R1"], jats_sources=source, jats_acquisitions=acquisition, pdf_audits=audit,
        repo_root=tmp_path, fitz_module=fitz,
    )
    manifest = tmp_path / "silver.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    items = load_visual_page_silver(manifest, repo_root=tmp_path, fitz_module=fitz)

    def caller(_prompt, _max_tokens):
        return json.dumps({"candidate_ids": [item.item_id for item in items]}), {"total_tokens": 10}

    result = run_locator_probe(
        items, checkpoint_dir=tmp_path / "cp", model="test", repeats=3,
        batch_size=3, max_requests=3, max_total_tokens=1000, max_output_tokens=50,
        caller=caller, prompt_builder=build_visual_page_prompt,
        prompt_version=PROMPT_VERSION,
    )
    assert result.gate_pass
    assert not deployment_gate_pass(result, max_selected_fraction=0.60)


def test_visual_gate_requires_three_repeats_and_validator_recomputes_metrics(tmp_path):
    source, acquisition, audit, fitz = _fixture(tmp_path)
    payload = build_visual_silver_manifest(
        ["R1"], jats_sources=source, jats_acquisitions=acquisition, pdf_audits=audit,
        repo_root=tmp_path, fitz_module=fitz,
    )
    manifest = tmp_path / "silver.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    items = load_visual_page_silver(manifest, repo_root=tmp_path, fitz_module=fitz)
    positive_id = next(item.item_id for item in items if item.positive)
    result = run_locator_probe(
        items, checkpoint_dir=tmp_path / "cp", model="test", repeats=1,
        batch_size=3, max_requests=1, max_total_tokens=1000, max_output_tokens=50,
        caller=lambda *_: (json.dumps({"candidate_ids": [positive_id]}), {"total_tokens": 10}),
        prompt_builder=build_visual_page_prompt, prompt_version=PROMPT_VERSION,
    )
    assert result.gate_pass
    assert not deployment_gate_pass(result)
    output = result_manifest(result, items, model="test")
    assert validate_result_manifest(output, items) == []
    output["repeat_recalls"] = [1.0, 1.0, 1.0]
    assert "repeat recall mismatch" in validate_result_manifest(output, items)


def test_pdf_visual_heldout_freezes_strict_hash_bound_page_pointers(tmp_path):
    directory = tmp_path / "data/papers/paper"
    directory.mkdir(parents=True)
    pdf = directory / "paper.pdf"
    pdf.write_bytes(b"pdf-heldout")
    positive = (
        "Fig. 1. Cell proliferation in treatment and control media. Values are mean and "
        "standard deviation from n = 3 independent experiments."
    )
    fitz = _Fitz(["Introduction.", positive, "Discussion."])
    corpus = [{"record_id": "R1", "doi": "10.1/example"}]
    audits = [{
        "record_id": "R1", "paper_id": "paper", "pdf_status": "audited",
        "pdf_path": str(pdf.relative_to(tmp_path)),
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "pages": "3",
    }]
    payload = build_pdf_visual_heldout_manifest(
        ["R1"], corpus_rows=corpus, pdf_audits=audits, repo_root=tmp_path,
        fitz_module=fitz,
    )
    assert payload["selector_version"] == PDF_HELDOUT_SELECTOR_VERSION
    assert payload["candidates"][0]["pdf_page"] == 2
    assert set(payload["candidates"][0]["supporting_blocks"][0]) == {
        "block_index", "block_text_sha256",
    }
    assert "cell proliferation" not in json.dumps(payload).casefold()

    manifest = tmp_path / "heldout.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    items = load_visual_page_silver(manifest, repo_root=tmp_path, fitz_module=fitz)
    assert [item.pdf_page for item in items if item.positive] == [2]


def test_pdf_visual_heldout_rejects_source_hash_and_page_count_drift(tmp_path):
    directory = tmp_path / "data/papers/paper"
    directory.mkdir(parents=True)
    pdf = directory / "paper.pdf"
    pdf.write_bytes(b"pdf-heldout")
    rows = [{
        "record_id": "R1", "paper_id": "paper", "pdf_status": "audited",
        "pdf_path": str(pdf.relative_to(tmp_path)),
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "pages": "2",
    }]
    import pytest
    with pytest.raises(ValueError, match="page count mismatch"):
        build_pdf_visual_heldout_manifest(
            ["R1"], corpus_rows=[{"record_id": "R1", "doi": "10.1/example"}],
            pdf_audits=rows, repo_root=tmp_path,
            fitz_module=_Fitz(["one", "two", "three"]),
        )
    rows[0]["pdf_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        build_pdf_visual_heldout_manifest(
            ["R1"], corpus_rows=[{"record_id": "R1", "doi": "10.1/example"}],
            pdf_audits=rows, repo_root=tmp_path,
            fitz_module=_Fitz(["one", "two"]),
        )


def test_shadow_audit_blocks_production_on_broad_recall_miss(tmp_path):
    directory = tmp_path / "data/papers/paper"
    directory.mkdir(parents=True)
    pdf = directory / "paper.pdf"
    pdf.write_bytes(b"pdf-shadow")
    strict = (
        "Fig. 1. Cell proliferation in treatment and control media. Values are mean and "
        "standard deviation from n = 3 independent experiments."
    )
    broad_only = "Fig. 2. Cell proliferation in treatment and control media over time."
    fitz = _Fitz(["Introduction.", strict, broad_only])
    heldout = build_pdf_visual_heldout_manifest(
        ["R1"], corpus_rows=[{"record_id": "R1", "doi": "10.1/example"}],
        pdf_audits=[{
            "record_id": "R1", "paper_id": "paper", "pdf_status": "audited",
            "pdf_path": str(pdf.relative_to(tmp_path)),
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "pages": "3",
        }],
        repo_root=tmp_path, fitz_module=fitz,
    )
    heldout_path = tmp_path / "heldout.json"
    heldout_path.write_text(json.dumps(heldout), encoding="utf-8")
    items = load_visual_page_silver(heldout_path, repo_root=tmp_path, fitz_module=fitz)
    strict_id = next(item.item_id for item in items if item.positive)
    result = run_locator_probe(
        items, checkpoint_dir=tmp_path / "cp", model="test", repeats=3,
        batch_size=3, max_requests=3, max_total_tokens=1000, max_output_tokens=50,
        caller=lambda *_: (json.dumps({"candidate_ids": [strict_id]}), {"total_tokens": 10}),
        prompt_builder=build_visual_page_prompt, prompt_version=PROMPT_VERSION,
    )
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result_manifest(
        result, items, model="test", selector_version=PDF_HELDOUT_SELECTOR_VERSION,
    )), encoding="utf-8")
    audit = audit_pdf_visual_shadow(
        heldout_path, result_path, repo_root=tmp_path, fitz_module=fitz,
    )
    assert audit["broad_baseline_pages"] == 2
    assert audit["model_selected_pages"] == 1
    assert audit["broad_recall"] == 0.5
    assert audit["incremental_utility_pass"] is True
    assert audit["production_gate_pass"] is False
    assert validate_pdf_visual_shadow_audit(audit) == []
