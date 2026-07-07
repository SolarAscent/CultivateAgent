"""A synthetic ground-truth objective for offline testing and demonstration.

Real objectives come from wet-lab experiments; this stand-in lets the ask/tell
loop, convergence, and the LLM-guided integration be tested with no lab and no
API key. It encodes a realistic *conflict*: growth factors and albumin raise
proliferation with saturating returns but raise cost linearly, so there is a
genuine proliferation/cost Pareto trade-off.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .mobo import Objective
from .space import MediumDesignSpace


def _sat(x: float, k: float) -> float:
    return x / (x + k) if (x + k) > 0 else 0.0


class SyntheticMediumObjective:
    """Deterministic (optionally noisy) proliferation/cost objective."""

    def __init__(self, *, noise: float = 0.0, seed: int = 0):
        self.noise = noise
        self.rng = np.random.default_rng(seed)

    @property
    def objectives(self) -> List[Objective]:
        return [Objective("proliferation", "max"), Objective("cost", "min")]

    def evaluate(self, f: Dict[str, object]) -> Dict[str, float]:
        fgf = float(f.get("FGF2", 0) or 0)
        igf = float(f.get("IGF-1", 0) or 0)
        alb = float(f.get("recombinant-albumin", 0) or 0)
        fbs = float(f.get("FBS", 0) or 0)
        y27 = float(f.get("Y-27632", 0) or 0)

        prolif = (_sat(fgf, 20) + 0.6 * _sat(igf, 15) + 0.5 * _sat(alb, 1.0)
                  + 0.4 * _sat(fbs, 5) + 0.2 * _sat(y27, 3)) / 2.5
        cost = 0.05 * fgf + 0.06 * igf + 8.0 * alb + 0.5 * fbs + 0.3 * y27 + 1.0

        if self.noise:
            prolif += self.rng.normal(0, self.noise)
            cost += self.rng.normal(0, self.noise * cost)
        return {"proliferation": round(prolif, 4), "cost": round(cost, 4)}

    def evaluate_many(self, formulations: List[Dict[str, object]]) -> List[Dict[str, float]]:
        return [self.evaluate(f) for f in formulations]
