"""Tests for evidence-derived πBO priors and their effect on the optimizer."""

from __future__ import annotations

import numpy as np
import pytest


def _summaries():
    from cultivate_agent.evidence import EvidenceSummary
    return [
        EvidenceSummary("FGF2", "proliferation", "*", k=3, method="random_effects_DL",
                        p_beneficial=0.99, i_squared=0.1),
        EvidenceSummary("FBS", "proliferation", "*", k=3, method="random_effects_DL",
                        p_beneficial=0.03, i_squared=0.1),
        EvidenceSummary("Y-27632", "proliferation", "*", k=4, method="random_effects_DL",
                        p_beneficial=0.55, i_squared=0.9, context_dependent=True),
    ]


def test_prior_from_summaries_directions_and_flags():
    from cultivate_agent.optimize import EvidencePrior, default_medium_space

    prior = EvidencePrior.from_summaries(default_medium_space(), _summaries(), beta=4.0)
    by = {b.parameter: b for b in prior.raw_beliefs}
    assert by["FGF2"].direction == 1 and by["FGF2"].strength > 0.9
    assert by["FBS"].direction == -1
    assert by["Y-27632"].direction == 0                 # context-dependent -> flat
    assert prior.flagged_context_dependent == ["Y-27632"]


def test_prior_log_prefers_beneficial_high_detrimental_low():
    from cultivate_agent.optimize import EvidencePrior, default_medium_space

    space = default_medium_space()
    prior = EvidencePrior.from_summaries(space, _summaries(), beta=4.0)
    good = space.encode({"FGF2": 100.0, "FBS": 0.0})     # high beneficial, low detrimental
    bad = space.encode({"FGF2": 0.0, "FBS": 20.0})       # low beneficial, high detrimental
    assert prior.log_prior(good)[0] > prior.log_prior(bad)[0]


def test_prior_weight_decays_with_observations():
    from cultivate_agent.optimize import EvidencePrior, default_medium_space

    prior = EvidencePrior.from_summaries(default_medium_space(), _summaries(), beta=4.0)
    assert prior.decayed_weight(0) > prior.decayed_weight(10) > prior.decayed_weight(100)


def test_prior_steers_optimizer_toward_evidence():
    from cultivate_agent.optimize import (
        EvidencePrior, MultiObjectiveBO, SyntheticMediumObjective, default_medium_space,
    )

    space = default_medium_space()
    obj = SyntheticMediumObjective(noise=0.0)
    prior = EvidencePrior.from_summaries(space, _summaries(), beta=5.0)

    def mean_fgf(use_prior, reps=6):
        vals = []
        for s in range(reps):
            m = MultiObjectiveBO(space, obj.objectives, seed=s)
            init = space.sample(6, seed=s)
            m.tell(init, obj.evaluate_many(init))
            batch = m.ask(6, pool_size=800,
                          preference_weights={"proliferation": 0.7, "cost": 0.3},
                          evidence_prior=prior if use_prior else None)
            vals += [b.formulation["FGF2"] for b in batch]
        return float(np.mean(vals))

    # A strong beneficial prior on FGF2 should raise the FGF2 levels the batch explores.
    assert mean_fgf(True) > mean_fgf(False)
