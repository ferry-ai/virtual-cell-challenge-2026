import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))
from vcc2026.multisource import effects_from_pseudobulk
from adapter import prepare, estimate, CALL


class AdapterTest(unittest.TestCase):
    def data(self):
        rows = pd.DataFrame([
            dict(study='s', context='iPSC', donor_or_clone=d, condition='c',
                 modality='CRISPRi', chemistry=chem, line_group='iPSC', target=t, n=n)
            for chem in ('v2', 'v3')
            for d, t, n in [('d1', 'NTC', 100), ('d1', 'alias', 30),
                             ('d2', 'NTC', 80), ('d2', 'alias', 60),
                             ('d3', 'NTC', 120), ('d1', 'secret', 20)]])
        x = np.tile([[100., 900.], [80., 220.], [700., 100.],
                     [450., 150.], [50., 1150.], [1., 199.]], (2, 1))
        return rows, x, np.ones(x.shape, bool)

    def run_adapter(self, **kw):
        rows, x, mask = self.data()
        return prepare(rows, x, mask, ['g1', 'g2'], ['T'],
                       {'alias': ('T', ('T',)), 'secret': ('Q', ('hidden',))},
                       hidden_targets=['hidden'], unit='hipsci', **kw)

    def test_original_estimator_and_all_controls(self):
        blocks, inv = self.run_adapter()
        self.assertEqual(len(blocks), 2)  # Chemistry remains separate.
        self.assertEqual(len(inv), 2)
        for b in blocks:
            self.assertEqual(set(b['obs'].donor), {'d1', 'd2', 'd3'})
            self.assertEqual(len(b['bank_rows']), 5)
            actual = estimate(b, effects_from_pseudobulk)
            x = np.array([[100., 900.], [80., 220.], [700., 100.],
                          [450., 150.], [50., 1150.]])
            obs = pd.DataFrame(dict(target=['non-targeting', 'T', 'non-targeting', 'T', 'non-targeting'],
                                    donor=['d1', 'd1', 'd2', 'd2', 'd3'],
                                    condition=['c']*5, n_cells=[100, 30, 80, 60, 120]))
            expected = effects_from_pseudobulk(x, obs, ['g1','g2'], targets=['T'], **CALL)
            for name in ('raw', 'se', 'shrunk', 'n_cells', 'control_mean'):
                np.testing.assert_array_equal(getattr(actual, name), getattr(expected, name))

    def test_global_hidden_before_statistics(self):
        rows, x, mask = self.data()
        x[rows.target == 'secret'] = np.nan
        blocks, _ = prepare(rows, x, mask, ['g1','g2'], ['T'],
            {'alias': ('T', ('T',)), 'secret': ('Q', ('hidden',))},
            hidden_targets=['hidden'], unit='hipsci')
        self.assertTrue(all(np.isfinite(b['counts']).all() for b in blocks))

    def test_missing_donor_anchor_refused(self):
        rows, x, mask = self.data()
        rows.loc[0, 'donor_or_clone'] = 'other'
        with self.assertRaisesRegex(ValueError, 'matched donor'):
            prepare(rows, x, mask, ['g1','g2'], ['T'],
                {'alias': ('T', ('T',)), 'secret': ('Q', ('hidden',))},
                hidden_targets=['hidden'], unit='hipsci')

    def test_validation_and_opaque_identity(self):
        self.assertEqual(self.run_adapter(held_groups=['iPSC']), ([], [(i, 'held_group') for i in range(12)]))
        with self.assertRaisesRegex(ValueError, 'protected unit'):
            self.run_adapter(protected_units=['hipsci'])
        rows, x, mask = self.data()
        with self.assertRaisesRegex(ValueError, 'unresolved biological'):
            prepare(rows, x, mask, ['g1','g2'], ['T'], {}, unit='hipsci')
        with self.assertRaisesRegex(ValueError, 'empty target resolution'):
            prepare(rows, x, mask, ['g1','g2'], ['T'],
                    {'alias': ('T', 'T')}, unit='hipsci')


if __name__ == '__main__':
    unittest.main()
