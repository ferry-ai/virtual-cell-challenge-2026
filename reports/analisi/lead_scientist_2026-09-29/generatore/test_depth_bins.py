"""Small synthetic invariants; no real-data training or scoring."""
import unittest

import numpy as np
import scipy.sparse as sp

from depth_bins import DepthBins
from depth_candidate import DepthCandidate
from vcc2026.inference import trial01_cells


class DepthBinTests(unittest.TestCase):
    def setUp(self):
        # Depth correlates with composition; one pooled composition loses it.
        self.counts = sp.csr_matrix([[8, 1, 1], [8, 1, 1], [10, 40, 50], [10, 40, 50]])
        self.model = DepthBins.fit(self.counts, n_bins=2)

    def test_null_reconstructs_both_control_functionals(self):
        profiles, _ = self.model.calibrate(self.model.pooled)
        np.testing.assert_allclose(self.model.depth_weights @ profiles, self.model.pooled, atol=1e-12)
        observed_pc = np.array([.45, .25, .30])
        np.testing.assert_allclose(self.model.cell_weights @ profiles, observed_pc, atol=1e-12)
        self.assertGreater(np.max(np.abs(observed_pc - self.model.pooled)), .1)

    def test_effect_preserves_requested_pooled_profile(self):
        desired = self.model.pooled * np.array([.3, 2, .7])
        desired /= desired.sum()
        profiles, diagnostic = self.model.calibrate(desired)
        np.testing.assert_allclose(self.model.depth_weights @ profiles, desired, atol=1e-11)
        np.testing.assert_allclose(profiles.sum(axis=1), 1, atol=1e-12)
        self.assertLess(diagnostic["max_absolute_pooled_error"], 1e-12)

    def test_independent_sampling_has_fresh_uncorrected_group_totals(self):
        a, da = self.model.sample(self.model.pooled, 400, np.random.default_rng(2))
        b, db = self.model.sample(self.model.pooled, 400, np.random.default_rng(3))
        self.assertFalse(np.array_equal(np.asarray(a.sum(axis=0)), np.asarray(b.sum(axis=0))))
        self.assertTrue(np.equal(a.data, np.floor(a.data)).all())
        self.assertEqual(da["count_cap_cells"] + db["count_cap_cells"], 0)

    def test_tail_edges_and_support_smoothing_preserve_global_null(self):
        model = DepthBins.fit(self.counts, quantile_edges=[0, .01, .025, .05, .1, .25, .5, .75, 1], support_smoothing=.01)
        np.testing.assert_allclose(model.depth_weights @ model.profiles, model.pooled, atol=1e-12)

    def test_smoothing_makes_outside_original_support_margin_feasible(self):
        data = sp.csr_matrix([[10, 0], [0, 90]])
        desired = np.array([.8, .2])
        model = DepthBins.fit(data, n_bins=2, support_smoothing=.01)
        profiles, _ = model.calibrate(desired)
        np.testing.assert_allclose(model.depth_weights @ profiles, desired, atol=1e-11)

    def test_integration_pooled_arm_calls_production_generator(self):
        candidate = DepthCandidate.fit(self.counts)
        effect, observed = np.array([-.3, .1, .2]), np.array([True, True, False])
        actual, _ = candidate.sample(effect, observed, 20, np.random.default_rng(17), generator="pooled", max_stored_per_cell=3)
        expected, _ = trial01_cells(candidate.model.pooled, effect, observed, candidate.model.library_sizes,
                                   20, np.random.default_rng(17), max_stored_per_cell=3, max_counts_per_cell=1000000)
        np.testing.assert_array_equal(actual.toarray(), expected.toarray())
        self.assertFalse(candidate.selection["fit_uses_perturbation_outcomes"])

    def test_integration_bin_arm_reports_calibration(self):
        candidate = DepthCandidate.fit(self.counts)
        actual, info = candidate.sample(np.array([-.3, .1, .2]), np.ones(3, dtype=bool),
                                        20, np.random.default_rng(17), generator="bins", max_stored_per_cell=3)
        self.assertEqual(actual.shape, (20, 3))
        self.assertLess(info["max_absolute_pooled_error"], 1e-12)


if __name__ == "__main__":
    unittest.main()
