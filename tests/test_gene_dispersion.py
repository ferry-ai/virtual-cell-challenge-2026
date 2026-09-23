"""Tests for `sampling.fit_gene_dispersion` and the per-gene path of `sample_counts`.

They pin two ways the dispersion fix could fail silently:

* a fitted phi that does not reproduce the zeros it was fitted to (the whole point);
* a per-gene phi applied to the wrong genes, or a gene with phi = 0 losing its Poisson law.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.sampling import fit_gene_dispersion, sample_counts  # noqa: E402


class GeneDispersionTests(unittest.TestCase):
    def test_recovers_known_dispersion_from_zero_fractions(self):
        rng = np.random.default_rng(0)
        g = 60
        p = rng.gamma(2.0, 1.0, g)
        p /= p.sum()
        libs = rng.integers(5000, 30000, size=6000).astype(float)
        true_phi = np.where(np.arange(g) % 3 == 0, 0.0, rng.uniform(0.2, 2.0, g))
        lam = libs[:, None] * p[None, :] * 0.02            # low counts: zeros carry the shape
        draw = lam.copy()
        over = true_phi > 0
        draw[:, over] = rng.gamma(1 / true_phi[over], lam[:, over] * true_phi[over])
        counts = rng.poisson(draw)
        zero = (counts == 0).mean(axis=0)
        fitted = fit_gene_dispersion(counts.sum(axis=0), counts.sum(axis=1), zero, n_cells=6000)
        ok = over & (zero > 0.05) & (zero < 0.95)
        np.testing.assert_allclose(fitted[ok], true_phi[ok], rtol=0.35)
        self.assertTrue((fitted[~over] < 0.1).all())       # Poisson genes stay (near) Poisson

    def test_per_gene_sampling_respects_each_gene(self):
        rng = np.random.default_rng(1)
        profile = np.array([1.0, 1.0])
        libs = np.full(20000, 20)
        out = sample_counts(profile, libs, rng, max_stored_per_cell=10, max_counts_per_cell=10**6,
                            overdispersion=np.array([0.0, 1.0])).toarray()
        mean = out.mean(axis=0)
        var = out.var(axis=0)
        self.assertAlmostEqual(var[0] / mean[0], 1.0, delta=0.05)          # Poisson
        self.assertAlmostEqual(var[1], mean[1] + mean[1] ** 2, delta=0.1 * (mean[1] + mean[1] ** 2))

    def test_rejects_wrong_shape(self):
        with self.assertRaises(ValueError):
            sample_counts(np.ones(3), np.array([10]), np.random.default_rng(0), max_stored_per_cell=10,
                          max_counts_per_cell=10**6, overdispersion=np.ones(2))


if __name__ == "__main__":
    unittest.main()
