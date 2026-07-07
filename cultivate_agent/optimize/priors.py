"""Evidence-derived priors over the design space (πBO-style).

Turns :class:`~cultivate_agent.evidence.meta_analysis.EvidenceSummary` posteriors
into a prior ``π(x)`` over medium formulations, injected into the acquisition
function following πBO (Hvarfner et al., *πBO: Augmenting Acquisition Functions
with User Beliefs for Bayesian Optimization*, ICLR 2022):

    α_πBO(x) = α(x) · π(x)^(β / (1 + n))

so the literature prior dominates early (small ``n``) and the wet-lab data takes
over as observations accumulate. A component the literature supports biases the
optimizer toward including it; a component with **high heterogeneity (I²)** gets a
**flat** prior, so the optimizer explores it rather than trusting a pooled belief
that does not transfer across contexts.

Priors bias *where the optimizer looks*; they never become objective values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from .space import MediumDesignSpace


@dataclass
class ComponentBelief:
    parameter: str            # design-space parameter name
    direction: int            # +1 beneficial, -1 detrimental, 0 flat (neutral / context-dependent)
    strength: float           # in [0, 1]; 0 => no influence
    p_beneficial: float
    context_dependent: bool
    outcome: str = ""


class EvidencePrior:
    """Log-linear prior over the encoded [0,1] design space."""

    def __init__(self, space: MediumDesignSpace, beliefs: List[ComponentBelief], *, beta: float = 3.0):
        self.space = space
        self.beliefs = [b for b in beliefs if b.direction != 0 and b.strength > 0]
        self.beta = beta
        # map parameter name -> encoded offset (continuous/binary occupy 1 slot)
        self._offset: Dict[str, int] = {}
        for p, off in zip(space.parameters, space._offsets):
            if p.kind in ("continuous", "binary"):
                self._offset[p.name] = off

    def log_prior(self, X: np.ndarray) -> np.ndarray:
        """Unnormalized log π(x) for each encoded row (higher = more preferred)."""
        X = np.atleast_2d(np.asarray(X, float))
        lp = np.zeros(len(X))
        for b in self.beliefs:
            off = self._offset.get(b.parameter)
            if off is None:
                continue
            # x_off in [0,1]; centered to [-1,1]. Beneficial -> reward high values.
            centered = 2.0 * X[:, off] - 1.0
            lp += b.strength * b.direction * centered
        return lp

    def decayed_weight(self, n_observed: int) -> float:
        """πBO schedule β/(1+n): strong prior early, vanishing as data accrues."""
        return self.beta / (1.0 + max(0, n_observed))

    @property
    def flagged_context_dependent(self) -> List[str]:
        return sorted({b.parameter for b in self.raw_beliefs if b.context_dependent})

    # keep the full (unfiltered) list for reporting
    raw_beliefs: List[ComponentBelief] = []

    @classmethod
    def from_summaries(
        cls,
        space: MediumDesignSpace,
        summaries: List,
        *,
        beta: float = 3.0,
        min_strength: float = 0.1,
    ) -> "EvidencePrior":
        """Build a prior from evidence summaries, mapping components to parameters."""
        param_names = {p.name for p in space.parameters}
        beliefs: List[ComponentBelief] = []
        for s in summaries:
            if s.component not in param_names:
                continue
            strength = round(2.0 * abs(s.p_beneficial - 0.5), 4)   # 0 at p=0.5, 1 at p in {0,1}
            direction = 1 if s.p_beneficial > 0.5 else (-1 if s.p_beneficial < 0.5 else 0)
            if s.context_dependent:
                direction = 0          # flat prior -> explore, do not bias
            b = ComponentBelief(
                parameter=s.component, direction=direction, strength=strength,
                p_beneficial=s.p_beneficial, context_dependent=s.context_dependent,
                outcome=s.outcome,
            )
            if b.strength >= min_strength or b.context_dependent:
                beliefs.append(b)
        prior = cls(space, beliefs, beta=beta)
        prior.raw_beliefs = beliefs
        return prior

    def describe(self) -> str:
        if not self.raw_beliefs:
            return "(no evidence-derived beliefs)"
        lines = []
        for b in sorted(self.raw_beliefs, key=lambda x: -x.strength):
            tag = "context-dependent(flat)" if b.context_dependent else (
                "beneficial" if b.direction > 0 else "detrimental")
            lines.append(f"  {b.parameter}: {tag}, p_beneficial={b.p_beneficial}, strength={b.strength}")
        return "\n".join(lines)
