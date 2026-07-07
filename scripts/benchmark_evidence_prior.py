#!/usr/bin/env python3
"""Benchmark: does the evidence prior improve sample efficiency, and is it robust?

Compares no-prior vs correct-prior vs wrong-prior MOBO on two regimes:
  * easy   — the saturating SyntheticMediumObjective (prior expected ~neutral),
  * sparse — few beneficial components among decoys (prior expected to help).

Reports normalized-hypervolume vs number of experiments, averaged over seeds.
Honest by construction: it also runs a WRONG prior to show the failure mode and
the πBO recovery. Offline, no API key.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cultivate_agent.evidence import EvidenceSummary  # noqa: E402
from cultivate_agent.optimize import (  # noqa: E402
    EvidencePrior, MultiObjectiveBO, SparseProliferationBenchmark,
    SyntheticMediumObjective, default_medium_space, hypervolume,
)


def _run(space, objectives, evaluate, make_prior, kind, seed, rounds, batch, init):
    m = MultiObjectiveBO(space, objectives, seed=seed)
    f = space.sample(init, seed=seed)
    m.tell(f, evaluate(f))
    prior = make_prior(kind)
    snaps = []
    for _ in range(rounds):
        b = m.ask(batch, pool_size=1200,
                  preference_weights={"proliferation": 0.7, "cost": 0.3}, evidence_prior=prior)
        forms = [s.formulation for s in b]
        m.tell(forms, evaluate(forms))
        snaps.append(np.array(m._Y))
    return snaps


def _bench(name, space, objectives, evaluate, make_prior, seeds=6, rounds=8, batch=4, init=5):
    runs = {k: [_run(space, objectives, evaluate, make_prior, k, s, rounds, batch, init)
                for s in range(seeds)] for k in ("none", "correct", "wrong")}
    allY = np.vstack([runs[k][s][-1] for k in runs for s in range(seeds)])
    lo, hi = allY.min(0), allY.max(0)
    span = np.where(hi > lo, hi - lo, 1)

    def nhv(Y):
        Yn = (Y - lo) / span
        return hypervolume(Yn * np.array([-1, 1]) + np.array([1, 0]), np.array([1.05, 1.05]))

    print(f"\n=== {name} ===")
    print(f"{'#exp':>5} {'no-prior':>10} {'correct':>10} {'wrong':>10}")
    for r in range(rounds):
        row = {k: np.mean([nhv(runs[k][s][r]) for s in range(seeds)]) for k in runs}
        print(f"{init + (r + 1) * batch:>5} {row['none']:>10.4f} {row['correct']:>10.4f} {row['wrong']:>10.4f}")


def main() -> int:
    # Easy regime.
    obj = SyntheticMediumObjective(noise=0.0)
    space = default_medium_space()

    def make_prior_easy(kind):
        if kind == "none":
            return None
        p = 0.97 if kind == "correct" else 0.03
        S = [EvidenceSummary(c, "proliferation", "*", k=3, method="random_effects_DL",
                             p_beneficial=p, i_squared=0.1)
             for c in ["FGF2", "IGF-1", "recombinant-albumin", "Y-27632"]]
        return EvidencePrior.from_summaries(space, S, beta=5.0)

    _bench("EASY (saturating objective; prior ~neutral)", space, obj.objectives,
           obj.evaluate_many, make_prior_easy)

    # Sparse regime.
    sb = SparseProliferationBenchmark(n_true=3, n_decoy=9, seed=0)
    print(f"\n(sparse: beneficial={sb.beneficial})")
    _bench("SPARSE (few components matter; prior helps when correct, hurts when wrong)",
           sb.space, sb.objectives, sb.evaluate_many, sb.make_prior)

    print("\nInterpretation: on easy objectives the directional prior is ~neutral; on sparse "
          "problems a correct prior accelerates the search and a wrong prior costs experiments "
          "(recovering via the πBO decay). This is why high-heterogeneity components get a flat "
          "prior and a 'test directly' flag rather than a confident bias.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
