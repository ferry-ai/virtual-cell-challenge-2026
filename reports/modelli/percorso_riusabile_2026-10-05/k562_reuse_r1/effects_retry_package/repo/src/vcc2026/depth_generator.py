"""Independent-cell Poisson generation conditional on control library-depth bins.

The optional stage-45 generator keeps depth/composition covariance that pooled
sampling discards. It selects uniform or tail-focused bins using controls only,
then calibrates each target's population expected counts to the SAME pooled
profile stage 45 already computes with its observed mask. Finite sampled totals
are never pinned or post-adjusted to the desired profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp

from .sampling import _enforce_count_cap, _enforce_storage_cap

__all__ = ["DepthGenerator"]


@dataclass
class DepthGenerator:
    profiles: np.ndarray
    library_sizes: np.ndarray
    cell_bins: np.ndarray
    depth_weights: np.ndarray
    pooled: np.ndarray
    diagnostics: dict

    @classmethod
    def fit_h5ad(cls, path: Path | str, library_sizes: np.ndarray,
                 expected_profile: np.ndarray, *, block_rows: int = 256) -> "DepthGenerator":
        """One bounded pass over a control CSR, with the already-read basal totals.

        Both candidate grids use smoothing=0.01 toward the pooled profile.
        Select by population mean-per-cell CPM RMSE on control genes >5 CPM;
        tie -> uniform8. No perturbation outcome or generation RNG is read.
        """
        library_sizes = np.asarray(library_sizes, dtype=np.float64)
        expected_profile = np.asarray(expected_profile, dtype=np.float64)
        if (library_sizes.ndim != 1 or not library_sizes.size
                or not np.isfinite(library_sizes).all() or np.any(library_sizes <= 0)):
            raise ValueError("Depth bins require finite positive control library sizes")
        if (expected_profile.ndim != 1 or not np.isfinite(expected_profile).all()
                or np.any(expected_profile < 0) or expected_profile.sum() <= 0):
            raise ValueError("Depth bins require a finite nonnegative basal profile")
        if block_rows <= 0:
            raise ValueError("block_rows must be positive")
        grids = {"uniform8": np.linspace(0, 1, 9),
                 "tail8": np.array([0, .01, .025, .05, .1, .25, .5, .75, 1])}
        assignments, sums, edges = {}, {}, {}
        n_genes = expected_profile.size
        for name, quantiles in grids.items():
            edges[name] = np.unique(np.quantile(library_sizes, quantiles[1:-1]))
            raw_bins = np.searchsorted(edges[name], library_sizes, side="right")
            assignments[name] = np.searchsorted(np.unique(raw_bins), raw_bins)
            sums[name] = np.zeros((int(assignments[name].max()) + 1, n_genes))
        mean_cell = np.zeros(n_genes)
        with h5py.File(path, "r") as source:
            shape = tuple(int(v) for v in source["X"].attrs["shape"])
            if shape != (library_sizes.size, n_genes):
                raise ValueError(f"Depth-bin input shape {shape} disagrees with basal state")
            ptr = source["X/indptr"][:].astype(np.int64)
            for start in range(0, shape[0], block_rows):
                end = min(start + block_rows, shape[0])
                lo, hi = ptr[start], ptr[end]
                values = source["X/data"][lo:hi].astype(np.float64)
                indices = source["X/indices"][lo:hi]
                lengths = np.diff(ptr[start:end+1])
                if (lengths <= 0).any():
                    raise ValueError("Control CSR has an empty row despite positive library")
                actual_library = np.add.reduceat(values, ptr[start:end] - lo)
                if not np.array_equal(actual_library, library_sizes[start:end]):
                    raise ValueError("Control library sizes changed since the basal profile was read")
                normalized = values / np.repeat(library_sizes[start:end], lengths)
                mean_cell += np.bincount(indices, weights=normalized, minlength=n_genes)
                for name in grids:
                    bins = np.repeat(assignments[name][start:end], lengths)
                    sums[name] += np.bincount(bins * n_genes + indices, weights=values,
                                              minlength=sums[name].size).reshape(sums[name].shape)
        if not np.array_equal(sums["uniform8"].sum(axis=0), expected_profile):
            raise ValueError("Control pooled profile changed since the basal state was read")
        pooled = expected_profile / expected_profile.sum()
        mean_cell /= library_sizes.size
        keep = mean_cell > 5e-6
        if not keep.any():
            raise ValueError("No control genes pass mean per-cell CPM >5")
        models, errors = {}, {}
        for name in grids:
            mass = sums[name].sum(axis=1)
            profiles = .99 * (sums[name] / mass[:, None]) + .01 * pooled[None, :]
            depth_weights = mass / mass.sum()
            cell_weights = np.bincount(assignments[name], minlength=mass.size) / library_sizes.size
            errors[name] = float(np.sqrt(np.mean((1e6 * ((cell_weights @ profiles)[keep] - mean_cell[keep]))**2)))
            models[name] = (profiles, depth_weights)
        selected = min(errors, key=errors.get)
        profiles, weights = models[selected]
        diagnostics = {
            "selected": selected, "selection_metric": "control mean-per-cell CPM RMSE on genes >5 CPM",
            "candidate_rmse": errors, "support_smoothing": .01,
            "n_bins": int(profiles.shape[0]), "library_bin_edges": edges[selected].tolist(),
            "cells_per_bin": np.bincount(assignments[selected]).tolist(),
            "control_cells": int(library_sizes.size), "control_genes_above_5_cpm": int(keep.sum()),
            "max_null_pooled_error": float(np.max(np.abs(weights @ profiles - pooled))),
            "fit_uses_perturbation_outcomes": False,
            "expectation_note": "E[count_gene]/E[library] is matched; finite-sample ratios and log1p remain random",
        }
        return cls(profiles, library_sizes, assignments[selected], weights, pooled, diagnostics)

    def calibrated_profiles(self, desired_profile: np.ndarray, *, tolerance: float = 1e-12,
                            max_iterations: int = 1000) -> tuple[np.ndarray, dict]:
        """IPF matches desired gene margins, retaining the bins' library-mass margins."""
        target = np.asarray(desired_profile, dtype=np.float64)
        if (target.shape != self.pooled.shape or not np.isfinite(target).all()
                or np.any(target < 0) or target.sum() <= 0):
            raise ValueError("Invalid desired depth-bin profile")
        if np.any((target > 0) & (self.pooled == 0)):
            raise ValueError("Desired profile requires a gene absent from all controls")
        target = target / target.sum()
        matrix = self.depth_weights[:, None] * self.profiles
        for iteration in range(max_iterations):
            columns = matrix.sum(axis=0)
            matrix *= np.divide(target, columns, out=np.zeros_like(columns), where=columns > 0)[None, :]
            rows = matrix.sum(axis=1)
            if (rows <= 0).any():
                raise ValueError("Desired profile leaves an empty depth bin")
            matrix *= (self.depth_weights / rows)[:, None]
            residual = matrix.sum(axis=0) - target
            error = float(np.max(np.abs(residual)))
            if error <= tolerance:
                diagnostic = {
                    "max_absolute_pooled_error": error,
                    "max_relative_pooled_error": float(np.max(np.abs(residual) / np.maximum(target, 1e-15))),
                    "calibration_iterations": iteration + 1,
                }
                return matrix / self.depth_weights[:, None], diagnostic
        raise RuntimeError(f"Depth-bin calibration failed after {max_iterations} iterations: {error}")

    def sample(self, desired_profile: np.ndarray, n: int, rng: np.random.Generator, *,
               max_stored_per_cell: int, max_counts_per_cell: int) -> tuple[sp.csr_matrix, dict]:
        """Draw fresh independent cells; the caps are the same guards used by stage 45."""
        profiles, diagnostic = self.calibrated_profiles(desired_profile)
        pick = rng.integers(0, self.library_sizes.size, size=n)
        rates = profiles[self.cell_bins[pick]] * self.library_sizes[pick, None]
        counts = rng.poisson(rates)
        count_cap_cells = int(np.sum(counts.sum(axis=1) > max_counts_per_cell))
        counts = _enforce_count_cap(counts, max_counts_per_cell)
        storage_cap_cells = int(np.sum(np.count_nonzero(counts, axis=1) > max_stored_per_cell))
        counts = _enforce_storage_cap(counts, max_stored_per_cell)
        diagnostic.update({"count_cap_cells": count_cap_cells, "storage_cap_cells": storage_cap_cells})
        return sp.csr_matrix(counts.astype(np.float32)), diagnostic
