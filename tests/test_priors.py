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


def test_correct_prior_beats_wrong_prior_on_sparse_benchmark():
    """On a sparse problem a correct prior should outperform a wrong one, and be
    no worse than no prior at a modest experiment budget (sample efficiency)."""
    from cultivate_agent.optimize import (
        MultiObjectiveBO, SparseProliferationBenchmark, hypervolume,
    )

    bench = SparseProliferationBenchmark(n_true=3, n_decoy=9, seed=0)
    seeds, rounds, batch, init = 5, 3, 4, 5

    def run(kind, seed):
        m = MultiObjectiveBO(bench.space, bench.objectives, seed=seed)
        f = bench.space.sample(init, seed=seed)
        m.tell(f, bench.evaluate_many(f))
        prior = bench.make_prior(kind)
        for _ in range(rounds):
            b = m.ask(batch, pool_size=800,
                      preference_weights={"proliferation": 0.7, "cost": 0.3}, evidence_prior=prior)
            forms = [s.formulation for s in b]
            m.tell(forms, bench.evaluate_many(forms))
        return np.array(m._Y)

    runs = {k: [run(k, s) for s in range(seeds)] for k in ("none", "correct", "wrong")}
    allY = np.vstack([runs[k][s] for k in runs for s in range(seeds)])
    lo, hi = allY.min(0), allY.max(0)
    span = np.where(hi > lo, hi - lo, 1)

    def nhv(Y):
        Yn = (Y - lo) / span
        return hypervolume(Yn * np.array([-1, 1]) + np.array([1, 0]), np.array([1.05, 1.05]))

    mean = {k: float(np.mean([nhv(runs[k][s]) for s in range(seeds)])) for k in runs}
    assert mean["correct"] > mean["wrong"]              # knowing the right knobs beats the wrong ones
    assert mean["correct"] >= mean["none"] - 0.02       # correct prior is not worse than no prior
