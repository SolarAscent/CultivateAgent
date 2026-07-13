"""Hierarchical evidence synthesis for heterogeneous literature.

The project record's critique names outcome comparability as the deepest problem:
a "2x proliferation" and a "39 h doubling time" are not commensurable, so
cross-paper numbers cannot be pooled naively or used as training labels. This
module answers that with a standard, closed-form **random-effects meta-analysis**
(DerSimonian & Laird, *Control. Clin. Trials* 1986) plus a heterogeneity index
(Higgins & Thompson I^2, *Stat. Med.* 2002), and a Beta-Binomial fallback for
direction-only evidence.

Output per (component, outcome, context): a posterior belief that the component
is *beneficial*, with an explicit uncertainty and a heterogeneity flag. High
heterogeneity (I^2) is surfaced as "context-dependent — test directly" rather
than hidden inside a pooled point estimate. These posteriors feed the optimizer
as **priors over promising regions** (see ``optimize``), never as objective
values — keeping the honesty constraint.

Design notes
------------
* We DO NOT manufacture evidence from mere co-occurrence. Evidence items must be
  real, quoted directional/effect claims (produced by the effect-extraction
  operator, ``evidence.effect_operator``).
* Tiering (from the review): tier 1 = effect + variance (enters the continuous
  random-effects pool); tier 2 = effect without variance (contributes only its
  sign to the direction vote, to avoid fake precision); tier 3 = direction only.
* Everything is numpy-only and closed-form (no MCMC), so it always runs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

_SQRT2 = math.sqrt(2.0)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


@dataclass
class EvidenceItem:
    """One quoted directional/effect claim from one paper.

    ``effect`` sign convention: positive = beneficial for ``outcome``.
    """

    component: str
    outcome: str
    paper_id: str
    effect: Optional[float] = None       # standardized effect (SMD or log fold-change)
    variance: Optional[float] = None     # within-study variance of ``effect`` (tier 1 only)
    direction: Optional[int] = None      # +1 beneficial, -1 detrimental, 0 neutral
    context: Dict[str, str] = field(default_factory=dict)  # species, cell_type, stage, ...
    quote: str = ""

    @property
    def tier(self) -> int:
        if self.effect is not None and self.variance is not None:
            return 1
        if self.effect is not None:
            return 2
        return 3

    @property
    def sign(self) -> int:
        if self.direction is not None:
            return int(np.sign(self.direction))
        if self.effect is not None:
            return int(np.sign(self.effect))
        return 0


@dataclass
class EvidenceSummary:
    component: str
    outcome: str
    context_key: str
    k: int                               # number of contributing studies
    method: str                          # random_effects_DL | single_study | beta_binomial | insufficient
    p_beneficial: float                  # posterior P(effect beneficial), in [0, 1]
    pooled_effect: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    variance: Optional[float] = None
    i_squared: Optional[float] = None    # heterogeneity fraction in [0, 1]
    tau_squared: Optional[float] = None
    context_dependent: bool = False      # True when I^2 is high -> recommend direct test
    n_continuous: int = 0
    n_direction: int = 0
    paper_ids: List[str] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


# --------------------------------------------------------------------------- #
# Core estimators                                                             #
# --------------------------------------------------------------------------- #
def dersimonian_laird(y: List[float], v: List[float]) -> Tuple[float, float, float, float, float]:
    """Random-effects pooling. Returns (pooled, var_pooled, tau2, i2, Q)."""
    y = np.asarray(y, float)
    v = np.asarray(v, float)
    k = len(y)
    v = np.clip(v, 1e-9, None)
    w = 1.0 / v
    y_fe = float((w * y).sum() / w.sum())
    Q = float((w * (y - y_fe) ** 2).sum())
    if k > 1:
        c = w.sum() - (w ** 2).sum() / w.sum()
        tau2 = max(0.0, (Q - (k - 1)) / c) if c > 0 else 0.0
        i2 = max(0.0, (Q - (k - 1)) / Q) if Q > 0 else 0.0
    else:
        tau2, i2 = 0.0, 0.0
    w_re = 1.0 / (v + tau2)
    y_re = float((w_re * y).sum() / w_re.sum())
    var_re = float(1.0 / w_re.sum())
    return y_re, var_re, tau2, i2, Q


def beta_binomial_direction(directions: List[int], prior: Tuple[float, float] = (1.0, 1.0)
                            ) -> Tuple[float, float, float, float]:
    """Posterior P(beneficial) from direction votes. Returns (p, var, alpha, beta)."""
    helps = sum(1 for d in directions if d > 0)
    hurts = sum(1 for d in directions if d < 0)
    a = prior[0] + helps
    b = prior[1] + hurts
    p = a / (a + b)
    var = a * b / ((a + b) ** 2 * (a + b + 1))
    return p, var, a, b


# --------------------------------------------------------------------------- #
# Orchestration                                                              #
# --------------------------------------------------------------------------- #
def _direction_conflict(directions: List[int]) -> Optional[Tuple[int, int]]:
    """Return (helps, hurts) when direction votes conflict enough to be context-dependent.

    Same criterion as the direction-only path: at least 3 signed studies and the
    minority direction is at least 30% of them. Applied in the random-effects branch
    too, so a component with a clear tier-1 magnitude but a split of direction-only
    studies is still flagged for direct testing rather than blindly trusted.
    """
    helps = len([d for d in directions if d > 0])
    hurts = len([d for d in directions if d < 0])
    signed = helps + hurts
    if signed >= 3 and min(helps, hurts) / signed >= 0.3:
        return helps, hurts
    return None


def meta_analyze(items: List[EvidenceItem], *, high_i2: float = 0.5) -> EvidenceSummary:
    """Synthesize a list of evidence items for ONE (component, outcome, context)."""
    if not items:
        raise ValueError("no evidence items")
    component = items[0].component
    outcome = items[0].outcome
    context_key = _context_key(items[0].context)
    paper_ids = sorted({it.paper_id for it in items})
    quotes = [it.quote for it in items if it.quote]

    continuous = [(it.effect, it.variance) for it in items if it.tier == 1]
    directions = [it.sign for it in items if it.sign != 0]

    summ = EvidenceSummary(
        component=component, outcome=outcome, context_key=context_key,
        k=len(paper_ids), method="insufficient", p_beneficial=0.5,
        n_continuous=len(continuous), n_direction=len(directions),
        paper_ids=paper_ids, quotes=quotes,
    )

    if len(continuous) >= 2:
        y = [c[0] for c in continuous]
        v = [c[1] for c in continuous]
        pooled, var, tau2, i2, _Q = dersimonian_laird(y, v)
        se = math.sqrt(max(var, 1e-12))
        summ.method = "random_effects_DL"
        summ.pooled_effect = round(pooled, 4)
        summ.variance = round(var, 6)
        summ.ci_low = round(pooled - 1.96 * se, 4)
        summ.ci_high = round(pooled + 1.96 * se, 4)
        summ.tau_squared = round(tau2, 6)
        summ.i_squared = round(i2, 4)
        summ.p_beneficial = round(_norm_cdf(pooled / se), 4)
        summ.context_dependent = i2 >= high_i2
        if summ.context_dependent:
            summ.note = f"High heterogeneity (I^2={i2:.0%}); effect is context-dependent — test directly."
        conflict = _direction_conflict(directions)
        if conflict:
            helps, hurts = conflict
            summ.context_dependent = True
            extra = (f"Direction evidence conflicts ({helps} help / {hurts} hurt across "
                     f"{helps + hurts} signed studies); context-dependent — test directly.")
            summ.note = f"{summ.note} {extra}".strip()
    elif len(continuous) == 1:
        pooled, var = continuous[0]
        se = math.sqrt(max(var, 1e-12))
        summ.method = "single_study"
        summ.pooled_effect = round(pooled, 4)
        summ.variance = round(var, 6)
        summ.ci_low = round(pooled - 1.96 * se, 4)
        summ.ci_high = round(pooled + 1.96 * se, 4)
        summ.p_beneficial = round(_norm_cdf(pooled / se), 4)
        summ.note = "Single quantitative study; weak prior."
    elif directions:
        p, var, a, b = beta_binomial_direction(directions)
        se = math.sqrt(var)
        summ.method = "beta_binomial"
        summ.p_beneficial = round(p, 4)
        summ.variance = round(var, 6)
        summ.ci_low = round(max(0.0, p - 1.96 * se), 4)
        summ.ci_high = round(min(1.0, p + 1.96 * se), 4)
        summ.note = f"Direction-only evidence (helps~alpha={a:.0f}, hurts~beta={b:.0f}); no effect sizes."
        # Direction-only heterogeneity: when papers disagree (both directions well
        # represented) the effect is context-dependent, the same conclusion I^2
        # gives for continuous evidence. Flag it so the optimizer explores rather
        # than trusts a pooled ~0.5 posterior.
        helps, hurts = len([d for d in directions if d > 0]), len([d for d in directions if d < 0])
        signed = helps + hurts
        if signed >= 3 and min(helps, hurts) / signed >= 0.3:
            summ.context_dependent = True
            summ.note += (f" Conflicting directions ({helps} help / {hurts} hurt) across "
                          "studies; context-dependent — test directly.")
    else:
        summ.note = "No usable directional or quantitative evidence."
    return summ


def synthesize(items: List[EvidenceItem], *, by_context: bool = False, high_i2: float = 0.5
               ) -> List[EvidenceSummary]:
    """Group items by (component, outcome[, context]) and meta-analyze each group.

    Default pools across context (``by_context=False``): context (species, cell
    type, stage) is treated as a source of *heterogeneity* that I² surfaces,
    rather than a hard split. Splitting by context (``by_context=True``) yields
    mostly k=1 groups on real corpora and defeats pooling; a validated 50-paper
    DeepSeek run went from 0 to 5 components at k>1 (FGF2, FBS at k=5) by pooling
    across context. Use ``by_context=True`` only for deliberate subgroup analysis.
    """
    groups: Dict[Tuple, List[EvidenceItem]] = {}
    for it in items:
        key = (it.component, it.outcome, _context_key(it.context) if by_context else "*")
        groups.setdefault(key, []).append(it)
    out = [meta_analyze(g, high_i2=high_i2) for g in groups.values()]
    # Most confident, best-supported first.
    out.sort(key=lambda s: (-abs(s.p_beneficial - 0.5), -s.k))
    return out


def _context_key(context: Dict[str, str]) -> str:
    if not context:
        return "*"
    return ";".join(f"{k}={context[k]}" for k in sorted(context))
