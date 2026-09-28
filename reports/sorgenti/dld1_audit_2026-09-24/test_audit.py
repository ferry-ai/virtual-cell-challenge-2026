"""Numerical checks for the report's similarity and mismatched-target controls."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('dld_audit', Path(__file__).with_name('audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_scale_invariance_and_pair_orientation(self):
        x = np.array([[1., 0., -1.], [0., 2., 0.]])
        y = x[::-1] * 7
        np.testing.assert_allclose(audit.similarity(x, y), [[0, 1], [1, 0]], atol=1e-12)

    def test_pearson_removes_gene_axis_offset(self):
        x = np.array([[1., 3., 8.]])
        self.assertAlmostEqual(float(audit.similarity(x, x*2+100, True)[0, 0]), 1.)

    def test_zero_norm_is_missing(self):
        x = np.array([[0., 0., 0.]])
        self.assertTrue(np.isnan(audit.similarity(x, x)[0, 0]))

    def test_null_excludes_identity_and_handles_ties(self):
        rows = []
        result = audit.describe_pairs(np.eye(3), ['a', 'b', 'c'], 'test', rows)
        self.assertEqual(result['discrimination']['median'], 1.)
        self.assertEqual(result['mismatched_median_per_target']['median'], 0.)
        result = audit.describe_pairs(np.ones((3, 3)), ['a', 'b', 'c'], 'test', [])
        self.assertEqual(result['discrimination']['median'], .5)


if __name__ == '__main__':
    unittest.main()
