from cultivate_agent.evaluate.deepseek_locator_probe import LocatorItem, run_locator_probe
from cultivate_agent.evaluate.deepseek_page_probe import (
    PROMPT_VERSION, build_page_prompt, load_page_silver,
)


def test_page_prompt_forbids_values_and_accepts_only_ids():
    prompt = build_page_prompt([])
    assert "candidate_ids" in prompt
    assert "Return no excerpts, numbers" in prompt


def test_page_probe_reuses_gold_and_is_checkpoint_resumable(tmp_path):
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    items = load_page_silver(
        root / "data/evaluation/gold/quantitative-pilot-v1/manifest.json",
        repo_root=root,
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
