"""Direction-only heterogeneity: conflicting votes -> context-dependent flag."""

from __future__ import annotations


def _items(component, dirs):
    from cultivate_agent.evidence import EvidenceItem
    return [EvidenceItem(component, "proliferation", f"p{i}", direction=d) for i, d in enumerate(dirs)]


def test_concordant_directions_not_flagged():
    from cultivate_agent.evidence import meta_analyze

    s = meta_analyze(_items("FGF2", [1, 1, 1, 1, 1]))
    assert s.method == "beta_binomial"
    assert s.context_dependent is False
    assert s.p_beneficial > 0.7


def test_conflicting_directions_flagged_context_dependent():
    from cultivate_agent.evidence import meta_analyze

    s = meta_analyze(_items("serum", [1, 1, 1, -1, -1, -1]))
    assert s.context_dependent is True                 # papers disagree -> test directly
    assert 0.35 < s.p_beneficial < 0.65
    assert "Conflicting directions" in s.note
