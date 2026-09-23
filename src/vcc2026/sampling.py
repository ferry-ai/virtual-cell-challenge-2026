"""Turn predicted mean expression profiles into raw count matrices.

Scoring runs in counts space, so a model that predicts a mean profile is only
half done: it still has to emit 400 plausible cells per perturbation. That step
is not a formality. It sets the within-group variance, which is what every
differential-expression call is tested against, so the sampling model is itself
a tunable component of the score -- `fid`, `reach` and `jac` all move with it.

The default is Poisson draws against a library size resampled from the
context's own control cells, which reproduces the observed sparsity almost
exactly (~6,000 detected genes at ~20k UMIs). Real scRNA-seq is overdispersed
relative to Poisson, so `overdispersion` switches to Gamma-Poisson.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

__all__ = ["resample_library_sizes", "sample_counts", "fit_gene_dispersion"]


def fit_gene_dispersion(
    profile: np.ndarray,
    library_sizes: np.ndarray,
    zero_fraction: np.ndarray,
    *,
    n_cells: int = 2000,
    max_phi: float = 50.0,
    iterations: int = 30,
    block: int = 2048,
    seed: int = 0,
) -> np.ndarray:
    """Per-gene Gamma-Poisson dispersion that reproduces each gene's zero fraction.

    The pooled-profile sampler draws every cell from ONE composition scaled to its library
    size. Real cells also differ in composition, so a gene carries more zeros across real
    cells than Poisson around the pooled mean allows. The scorer's Wilcoxon test reads the
    missing zeros as an upward shift: on the t11 file, trial-01's generator called 543-764
    genes per target, 83-85% of them up (stage 83, 2026-09-23).

    For each gene, ``phi`` is found by bisection on ``log(phi)`` so that
    ``mean_c (1 + phi * lam_cg) ** (-1 / phi)`` equals the observed zero fraction, with
    ``lam_cg = L_c * p_g`` over ``n_cells`` library sizes drawn from the controls. A gene
    whose Poisson zero fraction already reaches the observed one gets ``phi = 0`` (Poisson).
    """
    profile = np.asarray(profile, dtype=np.float64)
    p = profile / profile.sum()
    rng = np.random.default_rng(seed)
    libs = rng.choice(np.asarray(library_sizes, dtype=np.float64), size=n_cells, replace=True)
    target = np.asarray(zero_fraction, dtype=np.float64)
    phi = np.zeros(p.size)
    for start in range(0, p.size, block):
        cols = np.arange(start, min(start + block, p.size))
        lam = libs[:, None] * p[None, cols]
        poisson_zero = np.exp(-lam).mean(axis=0)
        need = (p[cols] > 0) & (target[cols] > poisson_zero + 1e-6) & (target[cols] < 1.0)
        if not need.any():
            continue
        sub, goal = lam[:, need], target[cols][need]
        lo = np.full(goal.size, np.log(1e-4))
        hi = np.full(goal.size, np.log(max_phi))
        for _ in range(iterations):
            mid = 0.5 * (lo + hi)
            ph = np.exp(mid)
            zero = np.exp(-np.log1p(ph[None, :] * sub) / ph[None, :]).mean(axis=0)
            too_few = zero < goal
            lo = np.where(too_few, mid, lo)
            hi = np.where(too_few, hi, mid)
        phi[cols[need]] = np.exp(0.5 * (lo + hi))
    return phi


def resample_library_sizes(
    observed: np.ndarray, n_cells: int, rng: np.random.Generator
) -> np.ndarray:
    """Draw `n_cells` library sizes by resampling a context's control cells.

    Using the real distribution keeps predicted cells inside the depth range the
    scorer sees in the ground truth, instead of inventing a depth profile.
    """
    return rng.choice(observed, size=n_cells, replace=True).astype(np.int64)


def sample_counts(
    profile: np.ndarray,
    lib_sizes: np.ndarray,
    rng: np.random.Generator,
    *,
    max_stored_per_cell: int,
    max_counts_per_cell: int,
    overdispersion: float | None = None,
) -> sp.csr_matrix:
    """Sample integer counts for one perturbation in one context.

    Args:
        profile: non-negative mean expression over genes; normalized internally,
            so any scaling works (counts, CPM, or a bare relative profile).
        lib_sizes: total counts to draw for each cell.
        rng: source of randomness.
        max_stored_per_cell: hard cap on stored values per cell. The challenge
            budget is ~13,200; excess is trimmed by dropping the smallest counts.
        max_counts_per_cell: hard cap on a cell's total counts (1,000,000).
        overdispersion: if given, draw Gamma-Poisson with variance
            `mu + overdispersion * mu**2` instead of Poisson.

    Returns:
        A CSR matrix of shape (len(lib_sizes), len(profile)), float32, holding
        non-negative whole numbers with no explicitly stored zeros.
    """
    profile = np.asarray(profile, dtype=np.float64)
    if profile.ndim != 1:
        raise ValueError(f"profile must be 1-D, got shape {profile.shape}")
    if np.any(profile < 0):
        raise ValueError("profile must be non-negative")

    total = profile.sum()
    if total <= 0:
        raise ValueError("profile sums to zero -- nothing to sample")
    p = profile / total

    lib_sizes = np.minimum(np.asarray(lib_sizes, dtype=np.int64), max_counts_per_cell)
    lam = lib_sizes[:, None] * p[None, :]

    if overdispersion is not None and np.ndim(overdispersion) == 1:
        # per-gene dispersion (`fit_gene_dispersion`); phi = 0 keeps a gene Poisson
        phi = np.asarray(overdispersion, dtype=np.float64)
        if phi.shape != p.shape or (phi < 0).any():
            raise ValueError("per-gene overdispersion must be non-negative, one value per gene")
        over = np.flatnonzero(phi > 0)
        if over.size:
            lam[:, over] = rng.gamma(shape=1.0 / phi[over], scale=lam[:, over] * phi[over])
    elif overdispersion is not None:
        if overdispersion <= 0:
            raise ValueError("overdispersion must be positive")
        shape = 1.0 / overdispersion
        lam = rng.gamma(shape=shape, scale=lam * overdispersion)

    counts = rng.poisson(lam)

    counts = _enforce_count_cap(counts, max_counts_per_cell)
    counts = _enforce_storage_cap(counts, max_stored_per_cell)

    return sp.csr_matrix(counts.astype(np.float32))


def _enforce_count_cap(counts: np.ndarray, cap: int) -> np.ndarray:
    """Scale down any cell whose total counts exceed the cap."""
    totals = counts.sum(axis=1)
    hot = totals > cap
    if not hot.any():
        return counts
    factor = (cap / totals[hot])[:, None]
    counts[hot] = np.floor(counts[hot] * factor).astype(counts.dtype)
    return counts


def _enforce_storage_cap(counts: np.ndarray, cap: int) -> np.ndarray:
    """Keep at most `cap` non-zero genes per cell, dropping the smallest counts.

    Poisson draws at realistic depth land near 6,000 non-zeros, so this normally
    does nothing. It is a guard against a model emitting an unnaturally smooth
    profile, which would spread counts thin and blow the density limit.
    """
    nnz = (counts > 0).sum(axis=1)
    hot = np.flatnonzero(nnz > cap)
    if hot.size == 0:
        return counts
    for i in hot:
        row = counts[i]
        keep = np.argpartition(row, -cap)[-cap:]
        trimmed = np.zeros_like(row)
        trimmed[keep] = row[keep]
        counts[i] = trimmed
    return counts
