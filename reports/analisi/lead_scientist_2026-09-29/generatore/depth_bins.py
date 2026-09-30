"""Experimental independent-cell generator conditional on library-depth bins.

No raw control row is emitted. The ratio of population expected counts equals
the requested target profile after matrix scaling. This fixes a population mean,
never a sampled group's totals: each synthetic cell is an independent draw.
Finite-sample ratios and log1p transforms need not be unbiased for that profile.
It is not production code and has not been selected by a scoring experiment.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp


@dataclass
class DepthBins:
    profiles: np.ndarray
    library_sizes: np.ndarray
    cell_bins: np.ndarray
    depth_weights: np.ndarray
    cell_weights: np.ndarray
    pooled: np.ndarray

    @classmethod
    def fit(cls, counts: sp.csr_matrix, *, n_bins: int = 8,
            quantile_edges: list[float] | None = None, support_smoothing: float = 0.0):
        counts = sp.csr_matrix(counts)
        libraries = np.asarray(counts.sum(axis=1, dtype=np.float64)).ravel()
        if (libraries <= 0).any():
            raise ValueError("Zero-library controls require explicit handling")
        quantiles = np.linspace(0, 1, n_bins + 1) if quantile_edges is None else np.asarray(quantile_edges)
        if (quantiles[0] != 0 or quantiles[-1] != 1 or np.any(np.diff(quantiles) <= 0)):
            raise ValueError("Quantile edges must strictly increase from 0 to 1")
        edges = np.unique(np.quantile(libraries, quantiles[1:-1]))
        assignments = np.searchsorted(edges, libraries, side="right")
        active = np.unique(assignments)
        assignments = np.searchsorted(active, assignments)
        sums = np.vstack([np.asarray(counts[assignments == b].sum(axis=0, dtype=np.float64)).ravel()
                          for b in range(active.size)])
        return cls.from_sums(sums, libraries, assignments, support_smoothing=support_smoothing)

    @classmethod
    def from_sums(cls, sums: np.ndarray, libraries: np.ndarray, assignments: np.ndarray,
                  *, support_smoothing: float = 0.0):
        """Construct from streaming bin sums; smoothing preserves the pooled mean."""
        if not 0 <= support_smoothing < 1:
            raise ValueError("Support smoothing must lie in [0,1)")
        mass = sums.sum(axis=1)
        profiles = sums / mass[:, None]
        depth_weights = mass / mass.sum()
        pooled = sums.sum(axis=0) / sums.sum()
        profiles = (1 - support_smoothing) * profiles + support_smoothing * pooled[None, :]
        cell_weights = np.bincount(assignments, minlength=sums.shape[0]) / libraries.size
        return cls(profiles, libraries, assignments, depth_weights, cell_weights,
                   pooled)

    def calibrate(self, desired_profile: np.ndarray, *, tolerance: float = 1e-12,
                  max_iterations: int = 1000) -> tuple[np.ndarray, dict]:
        """IPF retains depth-bin contrasts while matching the desired pooled mean.

        Matrix rows have margins depth_weights; columns have margins desired.
        The multiplicative row/column solution is a gene tilt followed by each
        bin's renormalization. No generated cell or group is post-adjusted.
        """
        target = np.asarray(desired_profile, dtype=np.float64)
        if target.shape != self.pooled.shape or not np.isfinite(target).all() or (target < 0).any():
            raise ValueError("Invalid desired profile")
        if target.sum() <= 0 or np.any((target > 0) & (self.pooled == 0)):
            raise ValueError("Desired profile requires unsupported genes or has zero mass")
        target = target / target.sum()
        matrix = self.depth_weights[:, None] * self.profiles
        for iteration in range(max_iterations):
            col = matrix.sum(axis=0)
            matrix *= np.divide(target, col, out=np.zeros_like(col), where=col > 0)[None, :]
            row = matrix.sum(axis=1)
            if (row <= 0).any():
                raise ValueError("Target distribution empties a depth bin")
            matrix *= (self.depth_weights / row)[:, None]
            error = float(np.max(np.abs(matrix.sum(axis=0) - target)))
            if error <= tolerance:
                return matrix / self.depth_weights[:, None], {
                    "max_absolute_pooled_error": error, "iterations": iteration + 1,
                    "n_bins": int(self.profiles.shape[0])}
        raise RuntimeError(f"Depth-bin mean calibration failed: residual {error}")

    def sample(self, desired_profile: np.ndarray, n: int, rng: np.random.Generator,
               *, phi: np.ndarray | None = None, max_stored_per_cell: int = 13200,
               max_counts_per_cell: int = 1000000) -> tuple[sp.csr_matrix, dict]:
        profiles, diagnostics = self.calibrate(desired_profile)
        pick = rng.integers(0, self.library_sizes.size, size=n)
        rates = profiles[self.cell_bins[pick]] * self.library_sizes[pick, None]
        if phi is not None:
            phi = np.asarray(phi, dtype=float)
            if phi.shape != self.pooled.shape or (phi < 0).any():
                raise ValueError("Invalid dispersion")
            over = phi > 0
            rates[:, over] = rng.gamma(1 / phi[over], rates[:, over] * phi[over])
        counts = rng.poisson(rates)
        # Same hard format guards as production. Their intervention changes the
        # expected mean and is reported, so the IPF guarantee is never overstated.
        totals = counts.sum(axis=1)
        hot_count = totals > max_counts_per_cell
        if hot_count.any():
            counts[hot_count] = np.floor(counts[hot_count] * (max_counts_per_cell / totals[hot_count])[:, None])
        hot_storage = np.flatnonzero((counts > 0).sum(axis=1) > max_stored_per_cell)
        for i in hot_storage:
            keep = np.argpartition(counts[i], -max_stored_per_cell)[-max_stored_per_cell:]
            trimmed = np.zeros_like(counts[i])
            trimmed[keep] = counts[i, keep]
            counts[i] = trimmed
        diagnostics.update({"count_cap_cells": int(hot_count.sum()), "storage_cap_cells": int(hot_storage.size)})
        return sp.csr_matrix(counts.astype(np.float32)), diagnostics
