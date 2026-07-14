from __future__ import annotations

import json

from cultivate_agent.evaluate.deepseek_alias_probe import (
    AliasGold,
    load_alias_gold,
    run_alias_probe,
    validate_mapping_response,
)


def test_alias_gold_is_unique_and_category_balanced(tmp_path):
    (tmp_path / "a.yaml").write_text(
        "- canonical: C1\n  aliases: [a1, shared]\n"
        "- canonical: C2\n  aliases: [a2]\n",
        encoding="utf-8",
    )
    (tmp_path / "b.yaml").write_text(
        "- canonical: C3\n  aliases: [b1, shared]\n",
        encoding="utf-8",
    )
    gold = load_alias_gold(tmp_path)

    assert [item.category for item in gold[:2]] == ["a", "b"]
    assert {item.surface for item in gold} == {"a1", "a2", "b1"}
    assert len({item.alias_id for item in gold}) == len(gold)


def test_response_validator_rejects_extra_keys_and_missing_ids():
    batch = [AliasGold("A001", "bFGF", "FGF2", "growth_factors")]
    mappings, issues = validate_mapping_response(
        '{"mappings":[{"id":"A001","canonical":"FGF2","relation":"alias","value":2}]}',
        batch,
        {"FGF2"},
    )
    assert mappings == {}
    assert any("invalid keys" in issue for issue in issues)
    assert any("missing 1" in issue for issue in issues)


def test_probe_is_resumable_and_gates_on_recall_and_consistency(tmp_path):
    gold = [
        AliasGold("A001", "bFGF", "FGF2", "growth_factors"),
        AliasGold("A002", "FCS", "FBS", "supplements"),
        AliasGold("A003", "D-MEM", "DMEM", "basal_media"),
        AliasGold("A004", "ROCKi", "Y-27632", "small_molecules"),
    ]
    calls = 0

    def caller(prompt, max_output_tokens):
        nonlocal calls
        calls += 1
        payload = json.loads(prompt.split("INPUT_JSON:\n", 1)[1])
        expected = {item.alias_id: item.canonical for item in gold}
        return json.dumps({"mappings": [
            {"id": item["id"], "canonical": expected[item["id"]], "relation": "alias"}
            for item in payload["surface_forms"]
        ]}), {"total_tokens": 100}

    kwargs = dict(
        checkpoint_dir=tmp_path / "checkpoints",
        model="deepseek-v4-flash",
        repeats=3,
        batch_size=2,
        max_requests=6,
        max_total_tokens=10000,
        max_output_tokens=200,
        caller=caller,
    )
    first = run_alias_probe(gold, **kwargs)
    second = run_alias_probe(gold, **kwargs)

    assert calls == 6
    assert first.repeat_recalls == (1.0, 1.0, 1.0)
    assert first.canonical_consistency == 1.0
    assert first.gate_pass is True
    assert first.mismatches == ()
    assert second.total_tokens == first.total_tokens
