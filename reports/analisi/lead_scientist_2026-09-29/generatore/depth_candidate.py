"""Bench integration for the control-only depth-bin candidate.

Use DepthCandidate.fit(controls), then .sample(lfc_ln, observed, n, rng,
amplitude=1.0, generator='bins' or 'pooled'). No perturbation outcome is used
to select depth edges. See PROTOCOLLO_BANCO_BINS.md before interpreting scores.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from depth_bins import DepthBins
from vcc2026.config import challenge
from vcc2026.inference import predicted_profile, trial01_cells


TAIL_EDGES = [0, .01, .025, .05, .1, .25, .5, .75, 1]


@dataclass
class DepthCandidate:
    model: DepthBins
    selection: dict

    @classmethod
    def fit(cls, controls: sp.csr_matrix):
        """Choose uniform8 versus tail8 by expected control mean-CPM RMSE only."""
        controls = sp.csr_matrix(controls)
        library = np.asarray(controls.sum(axis=1, dtype=np.float64)).ravel()
        if (library <= 0).any():
            raise ValueError("Zero-library controls require explicit handling")
        cell_mean = np.zeros(controls.shape[1], dtype=np.float64)
        for start in range(0, controls.shape[0], 400):
            end = min(start + 400, controls.shape[0])
            lo, hi = controls.indptr[start], controls.indptr[end]
            lengths = np.diff(controls.indptr[start:end+1])
            normalized = controls.data[lo:hi].astype(np.float64) / np.repeat(library[start:end], lengths)
            cell_mean += np.bincount(controls.indices[lo:hi], weights=normalized, minlength=controls.shape[1])
        cell_mean /= controls.shape[0]
        keep = cell_mean > 5e-6
        if not keep.any():
            raise ValueError("No genes pass control mean CPM >5")
        models = {
            "uniform8": DepthBins.fit(controls, n_bins=8, support_smoothing=.01),
            "tail8": DepthBins.fit(controls, quantile_edges=TAIL_EDGES, support_smoothing=.01),
        }
        errors = {name: float(np.sqrt(np.mean((1e6 * ((model.cell_weights @ model.profiles)[keep] - cell_mean[keep]))**2)))
                  for name, model in models.items()}
        # Deterministic tie policy: uniform is first, and only strict wins replace it.
        chosen = min(errors, key=errors.get)
        summary = {"selected": chosen, "selection_metric": "expected control mean CPM RMSE on control genes >5 CPM",
                   "rmse": errors, "support_smoothing": .01, "control_cells": int(controls.shape[0]),
                   "genes_tested": int(keep.sum()), "n_bins": int(models[chosen].profiles.shape[0]),
                   "fit_uses_perturbation_outcomes": False}
        return cls(models[chosen], summary)

    def sample(self, lfc_ln: np.ndarray, observed: np.ndarray, n: int, rng: np.random.Generator,
               *, amplitude: float = 1.0, generator: str = "bins", max_stored_per_cell: int | None = None,
               max_counts_per_cell: int = 1000000):
        """Return (CSR counts, diagnostics), with phi fixed at zero in both arms."""
        if max_stored_per_cell is None:
            max_stored_per_cell = challenge().max_stored_per_cell
        scaled = amplitude * np.asarray(lfc_ln, dtype=np.float64)
        if generator == "pooled":
            counts, diagnostic = trial01_cells(self.model.pooled, scaled, observed,
                                              self.model.library_sizes, n, rng,
                                              max_stored_per_cell=max_stored_per_cell,
                                              max_counts_per_cell=max_counts_per_cell)
            return counts, diagnostic | {"generator": "pooled", "amplitude": amplitude}
        if generator != "bins":
            raise ValueError("generator must be pooled or bins")
        profile, diagnostic = predicted_profile(self.model.pooled, scaled / np.log(2.0), observed)
        counts, sampled = self.model.sample(profile, n, rng, phi=None,
                                           max_stored_per_cell=max_stored_per_cell,
                                           max_counts_per_cell=max_counts_per_cell)
        return counts, diagnostic | sampled | {"generator": "bins", "amplitude": amplitude,
                                               "control_fit": self.selection}
