"""Original masked ridge baseline inspired by GenePert, not its implementation.

Frozen biological features -> fold-admissible response effects. No context claim:
this is a target-only alternative, with a separately fitted generic baseline.
All supplied rows must already pass the owner's fold and modality policy.
"""
from __future__ import annotations

import numpy as np


class MaskedRidge:
    def __init__(self, alpha=1.0):
        if not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("positive finite regularization required")
        self.alpha = float(alpha)

    def fit(self, features, effects, mask, *, row_contexts, row_targets,
            excluded_contexts, excluded_targets, sample_weight=None):
        x = np.asarray(features, dtype=np.float64)
        y = np.asarray(effects, dtype=np.float64)
        m = np.asarray(mask)
        if x.ndim != 2 or y.ndim != 2 or y.shape != m.shape or len(x) != len(y):
            raise ValueError("incompatible row/feature/response axes")
        if m.dtype != bool or not np.isfinite(x).all() or not np.isfinite(y[m]).all():
            raise ValueError("invalid mask or observed values")
        if len(row_contexts) != len(x) or len(row_targets) != len(x):
            raise ValueError("row metadata mismatch")
        # Refuse forbidden rows instead of silently filtering an upstream error.
        if set(row_contexts) & set(excluded_contexts) or set(row_targets) & set(excluded_targets):
            raise ValueError("excluded labels reached fit")
        w = np.ones(len(x)) if sample_weight is None else np.asarray(sample_weight, dtype=float)
        if w.shape != (len(x),) or not np.isfinite(w).all() or np.any(w <= 0):
            raise ValueError("positive finite row weights required")
        if not len(x):
            raise ValueError("no training rows")
        self.feature_mean = np.average(x, axis=0, weights=w)
        self.feature_scale = np.sqrt(np.average((x-self.feature_mean)**2, axis=0, weights=w))
        self.feature_scale[self.feature_scale < 1e-12] = 1.0
        x = (x-self.feature_mean)/self.feature_scale
        self.coef = np.zeros((x.shape[1], y.shape[1]))
        self.intercept = np.zeros(y.shape[1])
        self.generic = np.zeros(y.shape[1])
        self.support = np.any(m, axis=0)
        # Group genes by identical masks to avoid repeating the matrix factorization.
        groups = {}
        for j in range(y.shape[1]):
            groups.setdefault(m[:, j].tobytes(), []).append(j)
        for columns in groups.values():
            observed = m[:, columns[0]]
            if not observed.any():
                continue
            xg, wg = x[observed], w[observed]
            yg = y[np.ix_(observed, columns)]
            xm = np.average(xg, axis=0, weights=wg)
            ym = np.average(yg, axis=0, weights=wg)
            xc, yc = xg-xm, yg-ym
            root = np.sqrt(wg / wg.sum())[:, None]
            a, b = xc*root, yc*root
            if a.shape[0] < a.shape[1]:
                coef = a.T @ np.linalg.solve(a@a.T + self.alpha*np.eye(a.shape[0]), b)
            else:
                coef = np.linalg.solve(a.T@a + self.alpha*np.eye(a.shape[1]), a.T@b)
            self.coef[:, columns] = coef
            self.intercept[columns] = ym-xm@coef
            self.generic[columns] = ym
        self.receipt = {"rows_read": len(x), "contexts_read": sorted(set(row_contexts)),
                        "targets_read": sorted(set(row_targets)),
                        "observed_per_gene": m.sum(axis=0).tolist(),
                        "weighted_observations_per_gene": (m*w[:, None]).sum(axis=0).tolist(),
                        "alpha": self.alpha, "uses_context": False}
        return self

    def predict(self, features, available=None):
        x = np.asarray(features, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != len(self.feature_mean):
            raise ValueError("feature axis mismatch")
        available = np.ones(len(x), dtype=bool) if available is None else np.asarray(available)
        if available.dtype != bool or available.shape != (len(x),):
            raise ValueError("feature availability mask mismatch")
        if not np.isfinite(x[available]).all():
            raise ValueError("nonfinite available features")
        result = np.full((len(x), len(self.support)), np.nan)
        result[available] = ((x[available]-self.feature_mean)/self.feature_scale)@self.coef+self.intercept
        mask = available[:, None] & self.support[None, :]
        result[~mask] = np.nan
        return result, mask
