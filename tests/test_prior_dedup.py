"""EvidencePrior.from_summaries dedupes duplicate component summaries."""

from __future__ import annotations


def test_from_summaries_dedupes_by_component_keeping_highest_k():
    from cultivate_agent.evidence import EvidenceSummary
    from cultivate_agent.optimize import EvidencePrior, default_medium_space

    space = default_medium_space()
    # Same component appears 3x (e.g. stale context-keyed KB rows); best-supported wins.
    summaries = [
        EvidenceSummary("FGF2", "proliferation", "species=bovine", k=8, method="beta_binomial", p_beneficial=0.70),
        EvidenceSummary("FGF2", "proliferation", "species=human", k=2, method="beta_binomial", p_beneficial=0.55),
        EvidenceSummary("FGF2", "proliferation", "*", k=3, method="beta_binomial", p_beneficial=0.67),
    ]
    prior = EvidencePrior.from_summaries(space, summaries)
    fgf2 = [b for b in prior.raw_beliefs if b.parameter == "FGF2"]
    assert len(fgf2) == 1                         # deduped, not counted 3x
    assert fgf2[0].p_beneficial == 0.70           # the k=8 summary won
