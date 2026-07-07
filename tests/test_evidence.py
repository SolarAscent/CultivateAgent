"""Tests for hierarchical evidence synthesis (offline, numpy + mock LLM)."""

from __future__ import annotations

import json

import pytest


def test_dersimonian_laird_identical_studies():
    from cultivate_agent.evidence import dersimonian_laird

    pooled, var, tau2, i2, Q = dersimonian_laird([0.5, 0.5, 0.5], [0.1, 0.1, 0.1])
    assert pooled == pytest.approx(0.5)
    assert tau2 == pytest.approx(0.0) and i2 == pytest.approx(0.0) and Q == pytest.approx(0.0)


def test_concordant_evidence_is_confident():
    from cultivate_agent.evidence import EvidenceItem, meta_analyze

    items = [EvidenceItem("FGF2", "proliferation", f"p{i}", effect=e, variance=0.05)
             for i, e in enumerate([0.8, 0.9, 0.75])]
    s = meta_analyze(items)
    assert s.method == "random_effects_DL"
    assert s.p_beneficial > 0.95
    assert s.i_squared is not None and s.i_squared < 0.5
    assert s.context_dependent is False
    assert s.ci_low > 0                      # CI excludes zero -> real signal


def test_conflicting_evidence_is_flagged_context_dependent():
    from cultivate_agent.evidence import EvidenceItem, meta_analyze

    items = [
        EvidenceItem("serum", "proliferation", "p1", effect=1.2, variance=0.05),
        EvidenceItem("serum", "proliferation", "p2", effect=-1.0, variance=0.05),
        EvidenceItem("serum", "proliferation", "p3", effect=1.1, variance=0.05),
        EvidenceItem("serum", "proliferation", "p4", effect=-0.9, variance=0.05),
    ]
    s = meta_analyze(items)
    assert s.i_squared > 0.5                 # substantial heterogeneity
    assert s.context_dependent is True
    assert 0.35 < s.p_beneficial < 0.65      # honest uncertainty, not a fake confident call
    assert s.ci_low < 0 < s.ci_high          # CI spans zero
    assert "context-dependent" in s.note


def test_beta_binomial_direction_only():
    from cultivate_agent.evidence import EvidenceItem, meta_analyze

    items = [EvidenceItem("soy-hydrolysate", "proliferation", f"p{i}", direction=d)
             for i, d in enumerate([1, 1, 1, -1])]
    s = meta_analyze(items)
    assert s.method == "beta_binomial"
    assert s.p_beneficial == pytest.approx(4 / 6, abs=1e-3)   # (1+3)/(2+4)


def test_synthesize_groups_and_ranks():
    from cultivate_agent.evidence import EvidenceItem, synthesize

    items = [
        EvidenceItem("FGF2", "proliferation", "p1", effect=0.9, variance=0.05),
        EvidenceItem("FGF2", "proliferation", "p2", effect=0.8, variance=0.05),
        EvidenceItem("IGF-1", "proliferation", "p1", direction=1),
    ]
    out = synthesize(items)
    comps = {s.component for s in out}
    assert comps == {"FGF2", "IGF-1"}
    # FGF2 (2 concordant quantitative studies) should rank above IGF-1 (1 direction vote)
    assert out[0].component == "FGF2"


def test_extract_effects_drops_ungrounded(monkeypatch):
    from cultivate_agent.evidence import extract_effects
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    text = "FGF2 at 20 ng/mL increased bovine satellite cell proliferation over 5 passages."
    payload = json.dumps({"evidence": [
        {"component": "FGF2", "direction": 1, "context": {"species": "bovine"},
         "quote": "FGF2 at 20 ng/mL increased bovine satellite cell proliferation"},   # grounded
        {"component": "IGF-1", "direction": 1, "context": {},
         "quote": "IGF-1 tripled the growth rate"},                                     # NOT in text -> dropped
    ]})
    client = get_client("mock", "m", responses=[payload])
    items = extract_effects(client, PaperRef(paper_id="p1", title="t"), text, "proliferation")
    comps = [it.component for it in items]
    assert comps == ["FGF2"]                 # ungrounded IGF-1 claim dropped
    assert items[0].context.get("species") == "bovine"
