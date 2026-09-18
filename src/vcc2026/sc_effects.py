"""Per-target effects estimated from single cells, with their own uncertainty.

A predicted effect reaches the scorer as a fold change applied to generated
cells, so what a source contributes is a vector of per-gene log fold changes and
a statement of how far to trust each one. Both are computed here from cells,
not from pseudobulk means:

* the effect is the log ratio of mean per-cell fractions (the functional the
  scorer's DE log2FC uses, up to the log base);
* its standard error comes from the between-cell variance of those fractions,
  so an overdispersed gene is not trusted as if it were Poisson;
* shrinkage is empirical Bayes per target: the spread of effects across genes,
  minus the sampling variance, is the prior variance, and each gene keeps the
  fraction ``tau^2 / (tau^2 + se^2)`` of its observed effect.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

__all__ = ["FractionStats", "fraction_stats", "log_effect", "eb_shrink"]


@dataclass
class FractionStats:
    mean: np.ndarray      # mean per-cell fraction, per gene
    var: np.ndarray       # between-cell variance of the fraction
    n: int                # cells

    @property
    def se(self) -> np.ndarray:
        return np.sqrt(self.var / max(self.n, 1))


def fraction_stats(counts: sp.csr_matrix) -> FractionStats:
    counts = sp.csr_matrix(counts, dtype=np.float64)
    lib = np.asarray(counts.sum(axis=1)).ravel()
    lib[lib == 0] = 1.0
    frac = sp.diags(1.0 / lib) @ counts
    mean = np.asarray(frac.mean(axis=0)).ravel()
    sq = frac.multiply(frac)
    var = np.asarray(sq.mean(axis=0)).ravel() - mean**2
    n = counts.shape[0]
    if n > 1:
        var *= n / (n - 1)
    return FractionStats(mean, np.maximum(var, 0.0), n)


def log_effect(target: FractionStats, control: FractionStats, *, floor: float = 1e-7):
    """Natural-log ratio of mean fractions and its delta-method standard error."""
    mt = np.maximum(target.mean, floor)
    mc = np.maximum(control.mean, floor)
    eff = np.log(mt) - np.log(mc)
    se = np.sqrt((target.se / mt) ** 2 + (control.se / mc) ** 2)
    return eff, se


def eb_shrink(eff: np.ndarray, se: np.ndarray, usable: np.ndarray) -> tuple[np.ndarray, float]:
    """Posterior-mean shrinkage with a normal prior fitted on the usable genes."""
    e, s = eff[usable], se[usable]
    tau2 = max(float(np.mean(e**2) - np.mean(s**2)), 1e-6)
    w = tau2 / (tau2 + se**2)
    out = np.where(usable, w * eff, 0.0)
    return out, tau2
