import hashlib
import json

from cultivate_agent.evaluate.deepseek_locator_probe import run_locator_probe
from cultivate_agent.evaluate.deepseek_visual_page_probe import (
    PROMPT_VERSION,
    build_visual_page_prompt,
    build_visual_silver_manifest,
    deployment_gate_pass,
    load_visual_page_silver,
    result_manifest,
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
