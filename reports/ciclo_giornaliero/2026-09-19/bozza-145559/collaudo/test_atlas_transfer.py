import unittest
import numpy as np
from scipy import sparse
from vcc2026.atlas_transfer import mix_effects, count_moments


class AtlasTransferAcceptance(unittest.TestCase):
    def test_missing_source_is_not_a_zero_vote(self):
        effects = np.array([[[2., np.nan, np.nan]], [[6., 8., np.nan]]])
        observed = np.isfinite(effects)
        out = mix_effects(effects, observed, np.array([[100.], [300.]]),
                          np.ones(2), np.zeros((2, 3)), gamma=0.)
        np.testing.assert_allclose(out['effects'], [[4.4, 8., 0.]])
        np.testing.assert_array_equal(out['observed'], [[True, True, False]])
        np.testing.assert_allclose(out['weight_sum'], [[1.25, .75, 0.]])

    def test_common_response_removed_before_source_average(self):
        out = mix_effects(np.array([[[4.]], [[8.]]]), np.ones((2,1,1), bool),
                          np.array([[100.], [100.]]), np.array([1.,3.]),
                          np.array([[4.], [0.]]), gamma=.75)
        np.testing.assert_allclose(out['effects'], [[6.25]])

    def test_unavailable_source_cannot_change_prediction(self):
        out = mix_effects(np.array([[[2.]], [[999.]]]), np.ones((2,1,1), bool),
                          np.array([[100.], [0.]]), np.ones(2),
                          np.zeros((2,1)), gamma=0.)
        np.testing.assert_allclose(out['effects'], [[2.]])

    def test_negative_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            mix_effects(np.ones((1,1,1)), np.ones((1,1,1), bool),
                        np.array([[-1.]]), np.ones(1), np.zeros((1,1)))

    def test_two_moments_are_distinct_and_sparse_safe(self):
        x = np.array([[9,1], [0,1], [0,0]])
        for counts in (x, sparse.csr_matrix(x)):
            out = count_moments(counts)
            np.testing.assert_allclose(out['mean_fraction'], [.45,.55])
            np.testing.assert_allclose(out['pooled_fraction'], [9/11,2/11])
            np.testing.assert_allclose(out['zero_fraction'], [2/3,1/3])
            self.assertEqual(out['n_cells'], 3)

    def test_invalid_counts_rejected(self):
        for counts in (np.zeros((2,2)), np.array([[1.,.5]]), np.array([[-1,2]])):
            with self.assertRaises(ValueError):
                count_moments(counts)


if __name__ == '__main__':
    unittest.main()
