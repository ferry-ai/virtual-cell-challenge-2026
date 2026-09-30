import importlib.util
from pathlib import Path
import unittest
import numpy as np
import scipy.sparse as sp

spec = importlib.util.spec_from_file_location('split_risk', Path(__file__).with_name('split_and_risk.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SplitRiskTest(unittest.TestCase):
    def test_reserved_cells_never_train_and_mixed_partitions_excluded(self):
        guides = ['fit_t', 'test_t', 'test_u', 'cal_v', 'fit_w']
        plan = {'channel_role': {'train': 'fit', 'test': 'test'},
                'guide_role': dict(zip(guides, ['fit', 'test', 'test', 'calibration', 'fit'])),
                'guide_target': dict(zip(guides, ['t', 't', 'u', 'v', 'w']))}
        matrix = sp.csr_matrix([[0, 1, 0, 0, 1], [1, 1, 0, 0, 0],
                                [0, 1, 1, 0, 0], [0, 1, 0, 1, 0], [1, 0, 0, 0, 1]])
        train = m.assign_cells(plan, 'train', np.arange(5), guides, matrix)
        np.testing.assert_array_equal(train['training'], [False, False, False, False, True])
        test = m.assign_cells(plan, 'test', np.arange(5), guides, matrix)
        self.assertEqual(test['focal_guide_index'][0], 1)
        self.assertEqual(test['focal_guide_index'][1], -1)
        self.assertIn(test['focal_guide_index'][2], [1, 2])
        self.assertEqual(test['focal_guide_index'][3], -1)
        self.assertEqual(test['counts']['evaluation_kept'], 2)

    def test_equal_guide_weight_then_target_and_mask(self):
        risk = m.PredictionRisk()
        n = 101
        observed = np.zeros((n, 2))
        baseline = np.ones((n, 2))
        candidate = np.zeros((n, 2))
        candidate[-1, 0] = 2
        candidate[:, 1] = 999  # unmeasured values must not contribute
        mask = np.tile([True, False], (n, 1))
        risk.add(['0'] * n, ['target'] * n, ['guide1'] * 100 + ['guide2'],
                 observed, baseline, candidate, mask)
        self.assertIsNone(risk.finish()['macro_gain'])
        risk.add(['1'] * n, ['target'] * n, ['guide1'] * 100 + ['guide2'],
                 observed, baseline, candidate, mask)
        # Guide gains +1 and -3 => macro -1, not the cell-weighted positive value.
        self.assertEqual(risk.finish()['macro_gain'], -1)
        with self.assertRaises(ValueError):
            risk.add(['state'], ['t'], ['g'], [[0]], [[0]], [[0]], [[False]])


if __name__ == '__main__':
    unittest.main()
