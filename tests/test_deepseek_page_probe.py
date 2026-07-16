import hashlib
import json

from cultivate_agent.evaluate.deepseek_locator_probe import (
    LocatorItem, run_locator_probe, run_shadow_localization,
)
from cultivate_agent.evaluate.deepseek_page_probe import (
    PROMPT_VERSION, build_page_prompt, load_page_shadow_pool, load_page_silver,
    page_shadow_manifest, validate_page_shadow_manifest,
)


class _Page:
    def __init__(self, text):
        self.text = text

    def get_text(self, _kind, sort=True):
        del sort
        return [(0, 0, 0, 0, self.text)]


class _Document(list):
    def close(self):
        pass


class _Fitz:
    def __init__(self, pages):
        self.pages = pages

    def open(self, _path):
        return _Document(_Page(text) for text in self.pages)


def _fixture(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"fixture-pdf")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    manifest = {
        "sources": [{"record_id": "R001", "pdf_path": "paper.pdf", "pdf_sha256": digest}],
        "candidates": [{"record_id": "R001", "pdf_page": 2}],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    pages = [
        "Background and references without experimental comparison.",
        "Cells in medium showed proliferation; error bars indicate SEM and n = 3.",
        "General discussion without a measured outcome.",
    ]
    return pdf, digest, path, _Fitz(pages)


def test_page_prompt_forbids_values_and_accepts_only_ids():
    prompt = build_page_prompt([])
    assert "candidate_ids" in prompt
    assert "Return no excerpts, numbers" in prompt


def test_page_probe_reuses_gold_and_is_checkpoint_resumable(tmp_path):
    _pdf, _digest, manifest, fitz = _fixture(tmp_path)
    items = load_page_silver(
        manifest, repo_root=tmp_path, fitz_module=fitz,
    )
    positives = {item.item_id for item in items if item.positive}
    assert positives

    def caller(prompt, _max_tokens):
        selected = sorted(item_id for item_id in positives if f'"id": "{item_id}"' in prompt)
        return __import__("json").dumps({"candidate_ids": selected}), {"total_tokens": 10}

    kwargs = dict(
        checkpoint_dir=tmp_path / "cp", model="test-model", repeats=3,
        batch_size=8, max_requests=30, max_total_tokens=10000,
        max_output_tokens=100, prompt_builder=build_page_prompt,
        prompt_version=PROMPT_VERSION,
    )
    first = run_locator_probe(items, caller=caller, **kwargs)
    assert first.gate_pass
    second = run_locator_probe(
        items, caller=lambda *_: (_ for _ in ()).throw(AssertionError("provider called")),
        **kwargs,
    )
    assert second == first


def test_unlabeled_shadow_manifest_contains_only_validated_pointers(tmp_path):
    _pdf, digest, _manifest, fitz = _fixture(tmp_path)
    source_rows = [{
        "record_id": "R001", "doi": "10.1/example", "pdf_path": "paper.pdf",
        "pdf_sha256": digest,
    }]
    corpus_rows = [{"record_id": "R001", "doi": "10.1/example"}]
    items, sources = load_page_shadow_pool(
        source_rows, corpus_rows=corpus_rows, repo_root=tmp_path, fitz_module=fitz,
    )

    def caller(prompt, _max_tokens):
        ids = [item.item_id for item in items if f'"id": "{item.item_id}"' in prompt]
        return json.dumps({"candidate_ids": ids[:1]}), {"total_tokens": 5}

    result = run_shadow_localization(
        items, checkpoint_dir=tmp_path / "shadow", model="test", repeats=3,
        batch_size=3, max_requests=3, max_total_tokens=100,
        max_output_tokens=20, caller=caller, prompt_builder=build_page_prompt,
        prompt_version=PROMPT_VERSION,
    )
    payload = page_shadow_manifest(result, sources=sources, model="test")
    assert validate_page_shadow_manifest(payload, items=items, sources=sources) == []
    assert payload["selected_pages"] == 1
    assert payload["selected_excerpt_chars"] < payload["input_excerpt_chars"]
    assert set(payload["candidates"][0]) == {
        "candidate_id", "record_id", "pdf_page", "page_excerpt_sha256", "source_pdf_sha256",
    }


def test_shadow_validator_suppresses_failed_output(tmp_path):
    _pdf, digest, _manifest, fitz = _fixture(tmp_path)
    items, sources = load_page_shadow_pool(
        [{"record_id": "R001", "doi": "10.1/example", "pdf_path": "paper.pdf",
          "pdf_sha256": digest}],
        corpus_rows=[{"record_id": "R001", "doi": "10.1/example"}],
        repo_root=tmp_path, fitz_module=fitz,
    )
    payload = {
        "format_version": 1, "status": "failed_unstable_no_output", "model": "test",
        "prompt_version": PROMPT_VERSION, "repeats": 3, "selection_consistency": 0.5,
        "total_tokens": 0, "input_pages": len(items), "selected_pages": 1,
        "input_excerpt_chars": 0, "selected_excerpt_chars": 0,
        "excerpt_reduction_fraction": 0.0,
        "sources": [], "candidates": [{"numeric_value": 9}], "limitations": [],
    }
    issues = validate_page_shadow_manifest(payload, items=items, sources=sources)
    assert any("schema mismatch" in issue for issue in issues)
    assert any("suppress" in issue for issue in issues)


def test_shadow_validator_rejects_source_hash_drift(tmp_path):
    _pdf, digest, _manifest, fitz = _fixture(tmp_path)
    items, sources = load_page_shadow_pool(
        [{"record_id": "R001", "doi": "10.1/example", "pdf_path": "paper.pdf",
          "pdf_sha256": digest}],
        corpus_rows=[{"record_id": "R001", "doi": "10.1/example"}],
        repo_root=tmp_path, fitz_module=fitz,
    )
    result = run_shadow_localization(
        items, checkpoint_dir=tmp_path / "empty", model="test", repeats=3,
        batch_size=3, max_requests=3, max_total_tokens=100, max_output_tokens=20,
        caller=lambda *_: ('{"candidate_ids":[]}', {"total_tokens": 1}),
        prompt_builder=build_page_prompt, prompt_version=PROMPT_VERSION,
    )
    payload = page_shadow_manifest(result, sources=sources, model="test")
    payload["sources"][0]["pdf_sha256"] = "0" * 64
    issues = validate_page_shadow_manifest(payload, items=items, sources=sources)
    assert "source R001 metadata mismatch" in issues


def test_page_probe_rejects_nonpositive_wall_budget(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="positive"):
        run_locator_probe(
            [LocatorItem("P001", "text", True, "R001", 1, -1, "a" * 64)],
            checkpoint_dir=tmp_path, model="test", repeats=1, batch_size=1,
            max_requests=1, max_total_tokens=100, max_output_tokens=10,
            caller=lambda *_: ('{"candidate_ids":[]}', {"total_tokens": 1}),
            max_wall_seconds=0,
        )
