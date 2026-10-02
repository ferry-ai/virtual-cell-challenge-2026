"""Synthetic checks of the route B arms (run from this folder: python -m unittest test_arms)."""
import unittest

import numpy as np

import arms


def sources(rng, T=40, G=300, K=3, shared=None):
    """K sources: target t shares a common profile with weight shared[t], plus independent noise."""
    shared = np.linspace(0, 1, T) if shared is None else shared
    base = rng.normal(size=(T, G))
    S = np.stack([shared[:, None] * base + (1 - shared[:, None]) * rng.normal(size=(T, G)) for _ in range(K)])
    S[1, :, :50] = np.nan                     # source 1 did not measure 50 genes
    return S


class Arms(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(0)
        self.S = sources(self.rng)
        self.M = np.nanmean(self.S, axis=0)
        self.genes = np.ones(self.S.shape[2], bool)

    def test_agreement_tracks_the_shared_part(self):
        A = arms.agreement(self.S, self.genes)
        self.assertTrue(np.all(np.isfinite(A)))
        self.assertGreater(np.corrcoef(A, np.linspace(0, 1, len(A)))[0, 1], 0.9)
        self.assertLess(abs(A[0]), 0.15)

    def test_agreement_needs_two_sources(self):
        S = self.S.copy()
        S[1:, 3] = np.nan
        self.assertTrue(np.isnan(arms.agreement(S, self.genes)[3]))

    def test_alloc_keeps_energy_and_favours_agreeing_targets(self):
        f, info = arms.alloc_factors(self.S, self.M, self.genes)
        e = (self.M ** 2).sum(1)
        self.assertAlmostEqual(float((f ** 2 * e).sum()), float(e.sum()), places=6)
        self.assertGreater(f[-5:].mean(), f[:5].mean())
        ratio = f / np.median(f)
        self.assertLessEqual(ratio.max() / ratio.min(), (arms.HIGH / arms.LOW) * 1.0001)

    def test_normrest_keeps_energy_and_lifts_shrunk_targets(self):
        f, _ = arms.normrest_factors(self.S, self.M, self.genes)
        e = (self.M ** 2).sum(1)
        self.assertAlmostEqual(float((f ** 2 * e).sum()), float(e.sum()), places=6)
        self.assertGreater(f[:5].mean(), f[-5:].mean())   # averaging shrinks disagreeing targets most

    def test_keep_energy_on_a_gene_subset(self):
        genes = np.zeros(self.S.shape[2], bool)
        genes[100:] = True
        f = arms.keep_energy(self.M, np.linspace(1, 2, self.M.shape[0]), genes)
        e = (self.M[:, genes] ** 2).sum(1)
        self.assertAlmostEqual(float((f ** 2 * e).sum()), float(e.sum()), places=6)

    def test_cis_dose(self):
        np.testing.assert_array_equal(arms.cis_scale(np.array([0, 4999, 5000, 49999])), [2, 2, 1, 1])


if __name__ == "__main__":
    unittest.main()
