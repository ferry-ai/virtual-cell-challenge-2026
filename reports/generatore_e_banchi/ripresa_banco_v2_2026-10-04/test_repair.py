import unittest
import numpy as np
from export_effects_r2 import validate_coverage

class CoverageTest(unittest.TestCase):
    def test_no_transfer_target_is_retained_and_named(self):
        raw = np.array([[np.nan, np.nan], [1., 2.]])
        for arm in ('prod', 'prod_wR'):
            self.assertEqual(validate_coverage(arm, raw, raw, ['missing', 'present']), ['missing'])

    def test_missing_supported_target_or_all_arm_still_fails(self):
        raw = np.array([[np.nan, np.nan]])
        with self.assertRaises(ValueError):
            validate_coverage('prod_wR', raw, np.ones((1, 2)), ['x'])
        with self.assertRaises(ValueError):
            validate_coverage('all', raw, raw, ['x'])

if __name__ == '__main__':
    unittest.main()
