"""Mixed tier-1 (effect+variance) + tier-3 (direction) synthesis.

When Codex's table path produces tier-1 items alongside the existing prose
direction evidence, synthesis must (a) pool the tier-1 magnitudes via DL, and
(b) still flag context-dependence when the direction-only studies conflict — a
clear tier-1 signal must not mask a split of direction votes.
"""

from __future__ import annotations

from cultivate_agent.evidence.meta_analysis import EvidenceItem, meta_analyze


def _tier1(pid, effect=0.6, var=0.03):
    return EvidenceItem("C", "proliferation", pid, effect=effect, variance=var)


def _dir(pid, d):
    return EvidenceItem("C", "proliferation", pid, direction=d)


def test_mixed_tiers_pool_via_dl_and_count_all_papers():
    items = [_tier1("p0"), _tier1("p1")] + [_dir(f"p{i}", 1) for i in range(2, 8)]
    s = meta_analyze(items)
    assert s.method == "random_effects_DL"
    assert s.k == 8                       # every paper counted
    assert s.n_continuous == 2 and s.n_direction == 8
    assert 0.0 <= s.p_beneficial <= 1.0


def test_agreeing_directions_do_not_flag_context_dependent():
    items = [_tier1("p0"), _tier1("p1")] + [_dir(f"p{i}", 1) for i in range(2, 8)]
    assert meta_analyze(items).context_dependent is False


def test_split_directions_flag_context_dependent_even_with_tier1():
    # 2 positive tier-1 + a 3/3 split of direction-only studies must NOT be trusted.
    items = [_tier1("p0"), _tier1("p1")] + [
        _dir("p2", -1), _dir("p3", 1), _dir("p4", -1),
        _dir("p5", 1), _dir("p6", -1), _dir("p7", 1),
    ]
    s = meta_analyze(items)
    assert s.method == "random_effects_DL"
    assert s.context_dependent is True
    assert "conflict" in s.note.lower()


def test_pure_tier1_low_heterogeneity_stays_trusted():
    s = meta_analyze([_tier1("p0", 0.5, 0.02), _tier1("p1", 0.52, 0.02), _tier1("p2", 0.48, 0.02)])
    assert s.method == "random_effects_DL"
    assert s.context_dependent is False
