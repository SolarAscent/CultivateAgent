"""Pareto-dominance and hypervolume utilities (numpy only).

All functions use the **minimization** convention internally: objective vectors
are compared with "smaller is better". Maximization objectives are negated by
the caller (see :mod:`cultivate_agent.optimize.mobo`). Hypervolume is the
standard multi-objective quality indicator maximized by qEHVI-style acquisition
(Daulton et al., NeurIPS 2020).
"""

from __future__ import annotations

from typing import Optional

import numpy as np


def dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """True if ``a`` Pareto-dominates ``b`` (minimization)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return bool(np.all(a <= b) and np.any(a < b))


def non_dominated_mask(Y: np.ndarray) -> np.ndarray:
    """Boolean mask of Pareto-non-dominated rows of ``Y`` (n, m), minimization."""
    Y = np.asarray(Y, float)
    n = Y.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        # Any other point that dominates i knocks it out.
        for j in range(n):
            if i == j or not mask[j]:
                continue
            if np.all(Y[j] <= Y[i]) and np.any(Y[j] < Y[i]):
                mask[i] = False
                break
    return mask


def pareto_front(Y: np.ndarray) -> np.ndarray:
    """Indices of the Pareto-optimal rows of ``Y`` (minimization)."""
    return np.where(non_dominated_mask(Y))[0]


def _hv_2d_min(front: np.ndarray, ref: np.ndarray) -> float:
    """Exact 2-D hypervolume dominated by ``front`` up to ``ref`` (minimization)."""
    pts = front[np.argsort(front[:, 0])]  # x ascending  => y descending
    hv = 0.0
    prev_x = ref[0]
    for i in range(len(pts) - 1, -1, -1):
        x, y = pts[i]
        if x >= ref[0] or y >= ref[1]:
            continue
        hv += (prev_x - x) * (ref[1] - y)
        prev_x = x
    return float(hv)


def hypervolume(Y: np.ndarray, ref: np.ndarray, *, mc_samples: int = 200_000,
                seed: int = 0) -> float:
    """Dominated hypervolume of point set ``Y`` w.r.t. reference ``ref``.

    Minimization: ``ref`` must be an upper bound (worse than every point on the
    dimensions that matter). Exact for 2 objectives; Monte-Carlo estimate for 3+.
    """
    Y = np.asarray(Y, float)
    ref = np.asarray(ref, float)
    if Y.ndim != 2 or Y.shape[0] == 0:
        return 0.0
    front = Y[non_dominated_mask(Y)]
    front = front[np.all(front < ref, axis=1)]  # only points strictly inside the box
    if front.shape[0] == 0:
        return 0.0
    m = front.shape[1]
    if m == 1:
        return float(ref[0] - front[:, 0].min())
    if m == 2:
        return _hv_2d_min(front, ref)

    # Monte-Carlo for m >= 3.
    rng = np.random.default_rng(seed)
    lo = front.min(axis=0)
    box = ref - lo
    if np.any(box <= 0):
        return 0.0
    samples = lo + rng.random((mc_samples, m)) * box
    # A sample is dominated if some front point is <= it on all dims.
    dominated = np.zeros(mc_samples, dtype=bool)
    for p in front:
        dominated |= np.all(p <= samples, axis=1)
    return float(dominated.mean() * np.prod(box))


def hypervolume_improvement(Y_obs: np.ndarray, candidate_Y: np.ndarray,
                            ref: np.ndarray) -> float:
    """HV gain from adding ``candidate_Y`` to the observed set ``Y_obs``."""
    base = hypervolume(Y_obs, ref) if len(Y_obs) else 0.0
    aug = np.vstack([Y_obs, candidate_Y[None, :]]) if len(Y_obs) else candidate_Y[None, :]
    return hypervolume(aug, ref) - base


def infer_reference_point(Y: np.ndarray, *, margin: float = 0.1) -> np.ndarray:
    """A reasonable reference point: worst observed value per objective + margin."""
    Y = np.asarray(Y, float)
    worst = Y.max(axis=0)
    span = np.ptp(Y, axis=0)
    span[span == 0] = 1.0
    return worst + margin * span
