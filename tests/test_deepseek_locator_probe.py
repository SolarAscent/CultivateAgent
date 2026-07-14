from __future__ import annotations

import hashlib
import json

from cultivate_agent.evaluate.deepseek_locator_probe import (
    LocatorItem,
    load_locator_silver,
    run_shadow_localization,
    run_locator_probe,
    shadow_manifest,
    validate_shadow_manifest,
    validate_candidate_response,
)


class FakePage:
    def __init__(self, texts):
        self.texts = texts

    def get_text(self, kind, sort=True):
        assert (kind, sort) == ("blocks", True)
        return [(0, 0, 100, 20, text) for text in self.texts]


class FakeDocument:
    def __init__(self, pages):
        self.pages = [FakePage(page) for page in pages]

    def __iter__(self):
        return iter(self.pages)

    def __getitem__(self, index):
        return self.pages[index]

    def close(self):
        return None


class FakeFitz:
    documents = {}

    @classmethod
    def open(cls, path):
        return FakeDocument(cls.documents[path.name])


def _hash(text):
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def test_silver_loader_verifies_hashes_and_builds_opaque_balanced_items(tmp_path):
    sources = []
    candidates = []
    FakeFitz.documents = {}
    for record_id in ("R017", "R047"):
        path = tmp_path / f"{record_id}.pdf"
        path.write_bytes(record_id.encode())
        positive = "Figure. Mean proliferation in serum-free medium, error bars are SD, n = 4."
        decoys = [
            f"Background passage {index} describes unrelated laboratory history and general context "
            "without reporting any experimental comparison or measurement at all."
            for index in range(8)
        ]
        FakeFitz.documents[path.name] = [[positive] + decoys]
        sources.append({
            "record_id": record_id, "pdf_path": path.name,
            "pdf_sha256": hashlib.sha256(record_id.encode()).hexdigest(),
        })
        for index in range(4):
            candidates.append({
                "candidate_id": f"{record_id}-{index}", "record_id": record_id,
                "pdf_page": 1, "block_index": 0, "block_text_sha256": _hash(positive),
            })
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": sources, "candidates": candidates}))

    items = load_locator_silver(
        manifest, repo_root=tmp_path, negatives_per_positive=1, fitz_module=FakeFitz
    )

    assert len(items) == 16
    assert sum(item.positive for item in items) == 8
    assert [item.item_id for item in items] == [f"L{i:03d}" for i in range(1, 17)]


def test_response_validator_rejects_extra_keys_duplicates_and_unknown_ids():
    batch = [LocatorItem("L001", "text", True, "R017", 1, 1, "a" * 64)]
    assert validate_candidate_response('{"candidate_ids":["L001"],"reason":"x"}', batch)[1]
    assert validate_candidate_response('{"candidate_ids":["L001","L001"]}', batch)[1]
    assert validate_candidate_response('{"candidate_ids":["L999"]}', batch)[1]


def test_probe_repeats_resumes_and_gates_on_recall_not_precision(tmp_path):
    items = [
        LocatorItem(f"L{i:03d}", f"text {i}", i <= 2, "R017", 1, i, str(i) * 64)
        for i in range(1, 5)
    ]
    calls = 0

    def caller(prompt, max_output_tokens):
        nonlocal calls
        calls += 1
        payload = json.loads(prompt.split("INPUT_JSON:\n", 1)[1])
        return json.dumps({"candidate_ids": [row["id"] for row in payload["blocks"]]}), {
            "total_tokens": 50
        }

    kwargs = dict(
        checkpoint_dir=tmp_path / "checkpoints", model="deepseek-v4-flash",
        repeats=3, batch_size=2, max_requests=6, max_total_tokens=2000,
        max_output_tokens=100, caller=caller,
    )
    first = run_locator_probe(items, **kwargs)
    second = run_locator_probe(items, **kwargs)

    assert calls == 6
    assert first.repeat_recalls == (1.0, 1.0, 1.0)
    assert first.repeat_precisions == (0.5, 0.5, 0.5)
    assert first.selection_consistency == 1.0
    assert first.gate_pass is True
    assert second.total_tokens == first.total_tokens


def test_shadow_run_retains_only_unanimous_pointers(tmp_path):
    items = [
        LocatorItem(f"S{i:03d}", f"text {i}", False, "R018", 1, i, str(i) * 64)
        for i in range(1, 4)
    ]
    calls = 0

    def caller(prompt, max_output_tokens):
        nonlocal calls
        calls += 1
        selected = ["S001", "S002"] if calls < 3 else ["S001"]
        return json.dumps({"candidate_ids": selected}), {"total_tokens": 30}

    result = run_shadow_localization(
        items, checkpoint_dir=tmp_path / "cp", model="deepseek-v4-flash",
        repeats=3, batch_size=3, max_requests=3, max_total_tokens=1000,
        max_output_tokens=100, caller=caller,
    )
    payload = shadow_manifest(result, model="deepseek-v4-flash")

    assert result.selected_ids == ("S001",)
    assert result.selection_consistency == 0.6667
    assert result.gate_pass is False
    assert payload["candidates"] == []
    assert validate_shadow_manifest(payload, items) == []
