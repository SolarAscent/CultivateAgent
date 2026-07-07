"""Tests for operator-decomposition extraction (offline, mock LLM)."""

from __future__ import annotations

import json

import pytest

TEXT = (
    "Abstract\nWe developed a serum-free medium for bovine satellite cells.\n\n"
    "Methods\nBasal medium was DMEM/F12 with FGF2 at 20 ng/mL and recombinant albumin. "
    "Cells were bovine satellite cells expanded serum-free.\n\n"
    "Results\nProliferation was measured by cell counting; doubling time was 39 h. "
    "MYOD and MYOG expression confirmed myogenicity."
)


def _handler(msgs):
    u = msgs[-1].content
    if "Operator: context" in u:
        return json.dumps({"fields": {"B.main_track": "medium", "B.species": ["bovine"],
                                      "D.cell_type": ["satellite cells"]},
                           "evidence": {"B.species": {"quote": "bovine satellite cells",
                                                      "location": "Methods", "confidence": "high"}}})
    if "Operator: medium" in u:
        return json.dumps({"fields": {"E.basal_medium": ["DMEM/F12"], "E.serum_free_status": "serum-free",
                                      "E.growth_factors": ["FGF2", "recombinant albumin"]},
                           "evidence": {"E.basal_medium": {"quote": "Basal medium was DMEM/F12",
                                                           "location": "Methods", "confidence": "high"}}})
    if "Operator: dose" in u:
        return json.dumps({"fields": {"J.has_extractable_quant_data": "yes"},
                           "evidence": {}})
    if "Operator: endpoints" in u:
        return json.dumps({"fields": {"I.proliferation_metrics": ["cell counting", "doubling time"]},
                           "evidence": {}})
    if "Operator: findings" in u:
        return json.dumps({"fields": {"M.recommended_action": "must_extract_now"}, "evidence": {}})
    return "{}"


def test_operator_fields_are_disjoint():
    from cultivate_agent.extract import OPERATORS

    seen = set()
    for op in OPERATORS:
        for f in op.fields:
            assert f not in seen, f"field {f} owned by >1 operator"
            seen.add(f)


def test_operator_extractor_merges_and_grounds():
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    client = get_client("mock", "m", handler=_handler)
    ext = OperatorExtractor(client).extract(
        PaperRef(paper_id="p1", title="Serum-free bovine medium", year=2022), TEXT)

    assert ext.medium_info.serum_free_status == "serum-free"
    assert ext.medium_info.basal_medium == ["DMEM/F12"]
    assert ext.fast_triage.species == ["bovine"]
    assert ext.quant_data.has_extractable_quant_data == "yes"
    assert ext.final_judgment.recommended_action == "must_extract_now"

    meta = ext.extraction_meta
    assert meta["mode"] == "operators"
    assert len(meta["operators"]) == 5
    assert all(o["status"] == "ok" for o in meta["operators"])
    # grounded evidence (verified quotes) present
    assert "E.basal_medium" in ext.evidence
    assert "B.species" in ext.evidence


def test_operator_failure_is_diagnosable():
    """A single failing operator must not crash extraction; its status is recorded."""
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    def handler(msgs):
        u = msgs[-1].content
        if "Operator: medium" in u:
            return "not json at all"          # parse_error
        if "Operator: dose" in u:
            return json.dumps({"fields": {}})  # empty
        return _handler(msgs)

    client = get_client("mock", "m", handler=handler)
    ext = OperatorExtractor(client).extract(PaperRef(paper_id="p2", title="t"), TEXT)
    statuses = {o["operator"]: o["status"] for o in ext.extraction_meta["operators"]}
    assert statuses["medium"] == "parse_error"
    assert statuses["dose"] == "empty"
    assert statuses["context"] == "ok"        # other operators still succeed
    assert ext.fast_triage.species == ["bovine"]


def test_operator_flags_unverified_quote():
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    def handler(msgs):
        if "Operator: medium" in msgs[-1].content:
            return json.dumps({"fields": {"E.serum_free_status": "serum-free"},
                               "evidence": {"E.serum_free_status": {
                                   "quote": "this exact phrase is absent from the source text",
                                   "location": "Methods", "confidence": "high"}}})
        return "{}"

    client = get_client("mock", "m", handler=handler)
    ext = OperatorExtractor(client).extract(PaperRef(paper_id="p3", title="t"), TEXT)
    ev = ext.evidence["E.serum_free_status"]
    assert "UNVERIFIED" in (ev.location or "")
