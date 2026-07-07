"""Acquisition functions for multi-objective Bayesian optimization.

Default is **q-ParEGO**: each batch member draws a random weight vector, collapses
the objectives with an augmented-Chebyshev scalarization, fits a GP to that
scalar, and maximizes Expected Improvement. Averaged over random weights this
targets the whole Pareto front, is cheap, and needs no gradients — a good match
for the numpy GP. (The BoTorch path in ``mobo.py`` offers qNEHVI instead, which
optimizes hypervolume improvement directly.)

All objectives are minimization here (the caller negates maximization ones).
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np

from .surrogate import make_surrogate

_erf = np.vectorize(math.erf)


def _norm_cdf(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + _erf(z / math.sqrt(2.0)))


def _norm_pdf(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z**2) / math.sqrt(2.0 * math.pi)


def expected_improvement(mu: np.ndarray, sigma: np.ndarray, best: float,
                         xi: float = 0.01) -> np.ndarray:
    """EI for MINIMIZATION over a candidate pool."""
    sigma = np.maximum(sigma, 1e-9)
    imp = best - mu - xi
    z = imp / sigma
    ei = imp * _norm_cdf(z) + sigma * _norm_pdf(z)
    return np.maximum(ei, 0.0)


def random_simplex_weights(m: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform sample on the (m-1)-simplex (Dirichlet(1,...,1))."""
    w = rng.random(m)
    return w / w.sum()


def _normalize_objectives(Y: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    lo = Y.min(axis=0)
    span = np.ptp(Y, axis=0)
    span[span == 0] = 1.0
    return (Y - lo) / span, lo, span


def augmented_chebyshev(Yn: np.ndarray, weights: np.ndarray, rho: float = 0.05) -> np.ndarray:
    """Augmented Chebyshev scalarization (minimization); Yn normalized to [0,1]."""
    wz = weights * Yn
    return wz.max(axis=1) + rho * wz.sum(axis=1)


def propose_qparego(
    X_obs: np.ndarray,
    Y_obs: np.ndarray,
    X_pool: np.ndarray,
    batch_size: int,
    *,
    surrogate_backend: str = "gp",
    preference_weights: Optional[np.ndarray] = None,
    seed: int = 0,
) -> Tuple[List[int], np.ndarray]:
    """Select ``batch_size`` pool rows via q-ParEGO.

    ``preference_weights`` (optional) biases the random weight draws toward the
    user's objective weights, so the acquisition explores the part of the Pareto
    front the user actually cares about. Returns ``(pool_indices, acq_scores)``.
    """
    rng = np.random.default_rng(seed)
    Yn, _, _ = _normalize_objectives(np.asarray(Y_obs, float))
    m = Yn.shape[1]
    chosen: List[int] = []
    last_scores = np.zeros(len(X_pool))

    for _ in range(min(batch_size, len(X_pool))):
        w = random_simplex_weights(m, rng)
        if preference_weights is not None:
            pref = np.asarray(preference_weights, float)
            pref = pref / (pref.sum() or 1.0)
            w = 0.5 * w + 0.5 * pref          # blend exploration with preference
            w = w / w.sum()

        g = augmented_chebyshev(Yn, w)
        gp = make_surrogate(surrogate_backend).fit(X_obs, g)
        mu, sigma = gp.predict(X_pool)
        ei = expected_improvement(mu, sigma, best=float(g.min()))
        if chosen:
            ei[chosen] = -np.inf   # sample batch without replacement
        idx = int(np.argmax(ei))
        chosen.append(idx)
        last_scores = ei
    return chosen, last_scores
