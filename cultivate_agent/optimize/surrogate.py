"""Surrogate models for Bayesian optimization.

Default is a dependency-free RBF Gaussian Process (numpy + Cholesky). It is
deliberately simple — median-heuristic lengthscale, standardized targets, small
fixed noise — which is enough for the low-data regime medium optimization lives
in (tens of experiments). For production, ``make_surrogate("sklearn")`` swaps in
scikit-learn's GaussianProcessRegressor, and the BoTorch path (see
``mobo.py``) uses a fully-tuned GP with qNEHVI.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


class GaussianProcess:
    """Zero-mean RBF GP regressor (single output), numpy-only."""

    def __init__(self, *, noise: float = 1e-3, lengthscale: Optional[float] = None,
                 signal_var: float = 1.0):
        self.noise = noise
        self.lengthscale = lengthscale
        self.signal_var = signal_var
        self._X: Optional[np.ndarray] = None
        self._y_mean = 0.0
        self._y_std = 1.0
        self._alpha: Optional[np.ndarray] = None
        self._L: Optional[np.ndarray] = None

    def _rbf(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        # squared euclidean distances
        d2 = (A**2).sum(1)[:, None] + (B**2).sum(1)[None, :] - 2 * A @ B.T
        d2 = np.maximum(d2, 0.0)
        return self.signal_var * np.exp(-0.5 * d2 / (self.lengthscale**2))

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GaussianProcess":
        X = np.asarray(X, float)
        y = np.asarray(y, float).ravel()
        self._X = X
        self._y_mean, self._y_std = float(y.mean()), float(y.std() or 1.0)
        yn = (y - self._y_mean) / self._y_std

        if self.lengthscale is None:
            self.lengthscale = _median_lengthscale(X)

        K = self._rbf(X, X) + self.noise * np.eye(len(X))
        self._L = np.linalg.cholesky(K + 1e-8 * np.eye(len(X)))
        self._alpha = np.linalg.solve(self._L.T, np.linalg.solve(self._L, yn))
        return self

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) in the ORIGINAL target scale."""
        X = np.asarray(X, float)
        if self._X is None:
            return np.zeros(len(X)), np.ones(len(X)) * self._y_std
        Ks = self._rbf(X, self._X)
        mean_n = Ks @ self._alpha
        v = np.linalg.solve(self._L, Ks.T)
        var_n = np.maximum(self.signal_var - (v**2).sum(0), 0.0)
        mean = mean_n * self._y_std + self._y_mean
        std = np.sqrt(var_n) * self._y_std
        return mean, std


def _median_lengthscale(X: np.ndarray) -> float:
    if len(X) < 2:
        return 1.0
    # subsample for speed on large candidate sets
    idx = np.arange(len(X))
    if len(X) > 200:
        idx = np.random.default_rng(0).choice(len(X), 200, replace=False)
    A = X[idx]
    d2 = (A**2).sum(1)[:, None] + (A**2).sum(1)[None, :] - 2 * A @ A.T
    d = np.sqrt(np.maximum(d2, 0.0))
    med = np.median(d[d > 0]) if np.any(d > 0) else 1.0
    return float(med) or 1.0


class SklearnGP:
    """Optional scikit-learn GP backend (better hyperparameter fitting)."""

    def __init__(self, **kwargs):
        try:
            from sklearn.gaussian_process import GaussianProcessRegressor  # type: ignore
            from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError("scikit-learn not installed. `pip install scikit-learn`") from e
        kernel = ConstantKernel(1.0) * RBF(1.0) + WhiteKernel(1e-3)
        self._gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=2)

    def fit(self, X, y):
        self._gp.fit(np.asarray(X, float), np.asarray(y, float).ravel())
        return self

    def predict(self, X):
        mean, std = self._gp.predict(np.asarray(X, float), return_std=True)
        return mean, std


def make_surrogate(backend: str = "gp", **kwargs):
    """Factory: ``"gp"`` (numpy, default) or ``"sklearn"``."""
    if backend in ("gp", "numpy"):
        return GaussianProcess(**kwargs)
    if backend == "sklearn":
        return SklearnGP(**kwargs)
    raise ValueError(f"unknown surrogate backend: {backend!r}")
