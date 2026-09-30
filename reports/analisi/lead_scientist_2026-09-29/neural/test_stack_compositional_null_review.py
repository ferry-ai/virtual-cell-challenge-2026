"""Independent review regressions; no checkpoint, source data, training or scoring."""
import unittest

import numpy as np
import scipy.sparse as sp

from stack_pilot import corrected_profile, predicted_profile


class CompositionalNullReviewTest(unittest.TestCase):
    genes = ['A', 'B', 'C']
    shared = {'A', 'B'}
    synthetic = sp.csr_matrix([[1., 2., 9.], [3., 4., 2.]])

    def test_null_with_different_shared_mass_keeps_inherited_offset(self):
        basal = np.array([10., 20., 7.])
        baseline = np.array([15., 17., 5.])
        out, detail = corrected_profile(basal, baseline, self.genes, self.genes,
                                        self.shared, self.synthetic, self.synthetic)
        np.testing.assert_allclose(out, [32. / 3., 64. / 3., 5.], rtol=1e-14)
        self.assertEqual(detail['shared_lfc_rms'], 0.)
        self.assertEqual(out[2], baseline[2])
        self.assertAlmostEqual(out.sum(), baseline.sum())
        expected = np.log2((baseline[:2].sum() / baseline.sum()) /
                           (basal[:2].sum() / basal.sum()))
        actual = np.log2((out[:2] / out.sum()) / (basal[:2] / basal.sum()))
        np.testing.assert_allclose(actual, expected, rtol=1e-14)
        self.assertGreater(expected, 0.)

    def test_normalized_shift_is_independent_of_input_units(self):
        basal = np.array([10., 20., 7.])
        baseline = np.array([15., 17., 5.])
        first, _ = corrected_profile(basal, baseline, self.genes, self.genes,
                                     self.shared, self.synthetic, self.synthetic)
        # Inputs need not use identical absolute scales; compare compositions.
        other, detail = corrected_profile(100 * basal, 3 * baseline, self.genes, self.genes,
                                          self.shared, self.synthetic, self.synthetic)
        np.testing.assert_allclose(other / other.sum(), first / first.sum(), rtol=1e-14)
        self.assertEqual(detail['shared_lfc_rms'], 0.)
        expected = np.log2((baseline[:2].sum() / baseline.sum()) /
                           (basal[:2].sum() / basal.sum()))
        self.assertNotAlmostEqual(expected, np.log2((3 * baseline[:2]).sum() / (100 * basal[:2]).sum()))

    def test_production_profile_has_same_total_but_can_change_shared_mass(self):
        basal = np.array([10., 20., 7.])
        baseline, _ = predicted_profile(basal, np.array([1., 0., -1.]), np.ones(3, dtype=bool))
        self.assertAlmostEqual(baseline.sum(), basal.sum())
        self.assertNotAlmostEqual(baseline[:2].sum(), basal[:2].sum())
        out, detail = corrected_profile(basal, baseline, self.genes, self.genes,
                                        self.shared, self.synthetic, self.synthetic)
        self.assertEqual(detail['shared_lfc_rms'], 0.)
        inherited_shift = np.log2(baseline[:2].sum() / basal[:2].sum())
        np.testing.assert_allclose(np.log2(out[:2] / basal[:2]), inherited_shift, rtol=1e-14)
        self.assertEqual(out[2], baseline[2])


if __name__ == '__main__':
    unittest.main()
