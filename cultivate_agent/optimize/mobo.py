"""Multi-objective Bayesian optimization over the medium design space.

Interface is the standard **ask / tell** loop used by self-driving labs:

    mobo.tell(formulations, measured_objectives)   # add wet-lab results
    next_batch = mobo.ask(batch_size=4)            # propose next experiments

Backends:
* ``"gp"``      — numpy GP + q-ParEGO (default, always available),
* ``"botorch"`` — BoTorch qNEHVI (optional; the production-grade path from
  Daulton et al., NeurIPS 2020/2021).
* ``"botorch-log"`` — BoTorch qLogNEHVI, a numerically improved qNEHVI variant
  when available in the installed BoTorch version.

Objectives carry a direction; maximization objectives are negated internally so
everything downstream is minimization (matching ``pareto.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import pareto
from .acquisition import propose_qparego
from .space import MediumDesignSpace


@dataclass
class Objective:
    name: str
    direction: str = "max"   # "max" | "min"


@dataclass
class Suggestion:
    formulation: Dict[str, object]
    source: str = "bo"                 # "bo" | "space-filling" | "llm"
    acq_score: Optional[float] = None
    note: str = ""


class MultiObjectiveBO:
    def __init__(
        self,
        space: MediumDesignSpace,
        objectives: List[Objective],
        *,
        backend: str = "gp",
        surrogate_backend: str = "gp",
        seed: int = 0,
    ):
        self.space = space
        self.objectives = objectives
        self.backend = backend
        self.surrogate_backend = surrogate_backend
        self.seed = seed
        self._X: List[np.ndarray] = []      # encoded formulations
        self._Y: List[np.ndarray] = []      # raw objective values (natural direction)

    # ------------------------------------------------------------------ #
    # Tell                                                               #
    # ------------------------------------------------------------------ #
    def tell(self, formulations: List[Dict[str, object]], values: List[Dict[str, float]]) -> None:
        for f, v in zip(formulations, values):
            self._X.append(self.space.encode(f))
            self._Y.append(np.array([float(v[o.name]) for o in self.objectives]))

    def tell_encoded(self, X: np.ndarray, Y: np.ndarray) -> None:
        for x, y in zip(np.asarray(X, float), np.asarray(Y, float)):
            self._X.append(x)
            self._Y.append(y)

    @property
    def n_observed(self) -> int:
        return len(self._X)

    # ------------------------------------------------------------------ #
    # Direction handling                                                 #
    # ------------------------------------------------------------------ #
    def _to_min(self, Y: np.ndarray) -> np.ndarray:
        Y = np.asarray(Y, float)
        signs = np.array([-1.0 if o.direction == "max" else 1.0 for o in self.objectives])
        return Y * signs

    # ------------------------------------------------------------------ #
    # Ask                                                                #
    # ------------------------------------------------------------------ #
    def ask(
        self,
        batch_size: int = 4,
        *,
        pool_size: int = 2000,
        preference_weights: Optional[Dict[str, float]] = None,
        extra_candidates: Optional[List[Dict[str, object]]] = None,
    ) -> List[Suggestion]:
        """Propose the next batch of formulations to test.

        ``extra_candidates`` (e.g. LLM-proposed formulations) are added to the
        candidate pool so the acquisition can score them alongside random
        exploration — this is the hook the LLM-guided loop uses.
        """
        # Cold start: not enough data to fit a surrogate -> space-filling design.
        if self.n_observed < max(2, len(self.objectives) + 1):
            samples = self.space.sample(batch_size, seed=self.seed)
            return [Suggestion(formulation=f, source="space-filling",
                               note="cold start: space-filling design") for f in samples]

        if self.backend in {"botorch", "botorch-log"}:
            return self._ask_botorch(batch_size, pool_size, preference_weights, extra_candidates)

        return self._ask_gp(batch_size, pool_size, preference_weights, extra_candidates)

    def _candidate_pool(self, pool_size: int, extra: Optional[List[Dict[str, object]]]):
        X_pool = self.space.sample_encoded(pool_size, seed=self.seed + self.n_observed)
        sources = ["bo"] * len(X_pool)
        if extra:
            X_extra = np.array([self.space.encode(f) for f in extra])
            X_pool = np.vstack([X_extra, X_pool])
            sources = ["llm"] * len(X_extra) + sources
        return X_pool, sources

    def _ask_gp(self, batch_size, pool_size, preference_weights, extra):
        X_obs = np.array(self._X)
        Y_min = self._to_min(np.array(self._Y))
        X_pool, sources = self._candidate_pool(pool_size, extra)

        pref = None
        if preference_weights:
            pref = np.array([preference_weights.get(o.name, 0.0) for o in self.objectives])
            if pref.sum() == 0:
                pref = None

        idx, scores = propose_qparego(
            X_obs, Y_min, X_pool, batch_size,
            surrogate_backend=self.surrogate_backend, preference_weights=pref, seed=self.seed,
        )
        out = []
        for i in idx:
            out.append(Suggestion(
                formulation=self.space.decode(X_pool[i]),
                source="llm" if sources[i] == "llm" else "bo",
                acq_score=float(scores[i]) if np.isfinite(scores[i]) else None,
                note="q-ParEGO expected improvement",
            ))
        return out

    def _ask_botorch(self, batch_size, pool_size, preference_weights, extra):  # pragma: no cover
        try:
            import torch  # type: ignore
            from botorch.models import SingleTaskGP  # type: ignore
            from botorch.fit import fit_gpytorch_mll  # type: ignore
            if self.backend == "botorch-log":
                from botorch.acquisition.multi_objective import (  # type: ignore
                    qLogNoisyExpectedHypervolumeImprovement as Acquisition,
                )
            else:
                from botorch.acquisition.multi_objective.monte_carlo import (  # type: ignore
                    qNoisyExpectedHypervolumeImprovement as Acquisition,
                )
            from gpytorch.mlls import ExactMarginalLogLikelihood  # type: ignore
        except ImportError as e:
            raise ImportError(
                f"{self.backend!r} backend requires torch + botorch + gpytorch"
                " with the requested acquisition available. Install/update them,"
                " or use backend='gp'."
            ) from e

        X = torch.tensor(np.array(self._X), dtype=torch.double)
        # BoTorch maximizes; negate our minimization matrix back to maximization.
        Ymin = self._to_min(np.array(self._Y))
        Ymax = torch.tensor(-Ymin, dtype=torch.double)

        model = SingleTaskGP(X, Ymax)
        mll = ExactMarginalLogLikelihood(model.likelihood, model)
        fit_gpytorch_mll(mll)

        ref = torch.tensor(-pareto.infer_reference_point(Ymin), dtype=torch.double)
        acqf = Acquisition(
            model=model, ref_point=ref.tolist(), X_baseline=X,
            prune_baseline=True,
        )
        X_pool, sources = self._candidate_pool(pool_size, extra)
        pool = torch.tensor(X_pool, dtype=torch.double).unsqueeze(1)
        with torch.no_grad():
            vals = acqf(pool)
        top = torch.topk(vals, batch_size).indices.tolist()
        pool_np = pool.squeeze(1).numpy()
        note = "qLogNEHVI" if self.backend == "botorch-log" else "qNEHVI"
        return [Suggestion(formulation=self.space.decode(pool_np[i]),
                           source="llm" if sources[i] == "llm" else "bo",
                           acq_score=float(vals[i]), note=note) for i in top]

    # ------------------------------------------------------------------ #
    # Reporting                                                          #
    # ------------------------------------------------------------------ #
    def pareto(self) -> List[Tuple[Dict[str, object], Dict[str, float]]]:
        """Current Pareto-optimal formulations with their objective values."""
        if self.n_observed == 0:
            return []
        Y_min = self._to_min(np.array(self._Y))
        idx = pareto.pareto_front(Y_min)
        out = []
        for i in idx:
            formulation = self.space.decode(self._X[i])
            vals = {o.name: float(self._Y[i][j]) for j, o in enumerate(self.objectives)}
            out.append((formulation, vals))
        return out

    def hypervolume(self) -> float:
        if self.n_observed == 0:
            return 0.0
        Y_min = self._to_min(np.array(self._Y))
        ref = pareto.infer_reference_point(Y_min)
        return pareto.hypervolume(Y_min, ref)
