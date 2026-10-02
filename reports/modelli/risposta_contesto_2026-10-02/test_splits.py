"""P1 acceptance fixtures: aliases, one line in several studies, QC losses, corpus changes, leakage.

Run: py.cmd -m unittest discover -s reports/modelli/risposta_contesto_2026-10-02 -p "test_*.py"
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from splits import Split, assert_no_leak, evaluation_rows, make_splits, target_fold, training_mask


def corpus() -> pd.DataFrame:
    """Two K562 studies, an alias pair (one Ensembl ID, two symbols), a target seen only in a table that fails QC."""
    rows = [
        # table, group, target symbol, key, cells, qc
        ('k562_gw', 'K562', 'FAM96B', 'ENSG00000166595', 120, True),       # alias of CIAO2B
        ('k562_ess', 'K562', 'POLR2A', 'ENSG00000181222', 300, True),
        ('k562_gw', 'K562', 'POLR2A', 'ENSG00000181222', 200, True),
        ('rpe1', 'RPE1', 'CIAO2B', 'ENSG00000166595', 80, True),
        ('rpe1', 'RPE1', 'POLR2A', 'ENSG00000181222', 90, True),
        ('rpe1', 'RPE1', 'ONLYQCFAIL', 'ENSG00000000001', 50, True),
        ('hct116', 'HCT116', 'ONLYQCFAIL', 'ENSG00000000001', 60, False),  # table failing QC
        ('hct116', 'HCT116', 'POLR2A', 'ENSG00000181222', 5, True),        # too few cells
        ('hct116', 'HCT116', 'MYC', 'ENSG00000136997', 70, True),
    ]
    return pd.DataFrame(rows, columns=['table', 'group', 'target', 'target_key', 'n_cells', 'qc_ok'])


class TestStableFolds(unittest.TestCase):
    def test_fold_depends_only_on_key_and_salt(self):
        keys = [f'ENSG{i:011d}' for i in range(500)]
        a = {k: target_fold(k, 5) for k in keys}
        b = {k: target_fold(k, 5) for k in reversed(keys[:250] + [f'NEW{i}' for i in range(300)] + keys[250:])}
        self.assertTrue(all(a[k] == b[k] for k in keys))
        counts = np.bincount(list(a.values()), minlength=5)
        self.assertTrue((counts > 60).all())          # roughly balanced

    def test_adding_or_reordering_tables_keeps_roles(self):
        rows = corpus()
        extra = pd.DataFrame([('new_study', 'HEK293T', 'POLR2A', 'ENSG00000181222', 100, True)],
                             columns=rows.columns)
        for split in make_splits(['K562', 'RPE1', 'HCT116'], n_folds=3):
            before = training_mask(rows, split)
            grown = pd.concat([extra, rows.iloc[::-1]], ignore_index=True)
            after = training_mask(grown, split)[1:][::-1]
            np.testing.assert_array_equal(before, after)


class TestExclusions(unittest.TestCase):
    def test_c_removes_every_study_of_the_line(self):
        rows = corpus()
        m = training_mask(rows, Split('C', 'K562', None, 3))
        self.assertFalse(m[rows.group.eq('K562').to_numpy()].any())
        self.assertTrue(m[~rows.group.eq('K562').to_numpy()].all())

    def test_j_removes_alias_rows_everywhere(self):
        rows = corpus()
        key = 'ENSG00000166595'
        f = target_fold(key, 3)
        m = training_mask(rows, Split('J', 'HCT116', f, 3))
        self.assertFalse(m[rows.target_key.eq(key).to_numpy()].any())   # both FAM96B and CIAO2B rows

    def test_leak_check_raises_for_any_arm(self):
        rows = corpus()
        split = Split('C', 'RPE1', None, 3)
        with self.assertRaises(AssertionError):
            assert_no_leak(rows, split, 'transfer')
        assert_no_leak(rows[training_mask(rows, split)], split, 'transfer')


class TestRegimeAfterQC(unittest.TestCase):
    def test_c_without_support_after_qc_is_lost_not_reassigned(self):
        rows = corpus()
        ev = evaluation_rows(rows, Split('C', 'RPE1', None, 3))
        self.assertIn('ENSG00000000001', set(ev.lost.target_key))
        self.assertEqual(set(ev.lost.loc[ev.lost.target_key.eq('ENSG00000000001'), 'reason']),
                         {'no_training_support_after_qc'})
        # the alias target is supported by K562 under its other symbol
        self.assertIn('ENSG00000166595', set(ev.rows.target_key))
        # POLR2A has support from K562 only: HCT116's row has 5 cells
        self.assertEqual(int(ev.rows.loc[ev.rows.target_key.eq('ENSG00000181222'), 'support'].iloc[0]), 1)

    def test_j_targets_have_no_training_rows(self):
        rows = corpus()
        for f in range(3):
            ev = evaluation_rows(rows, Split('J', 'RPE1', f, 3))
            self.assertTrue((ev.rows.support == 0).all())


if __name__ == '__main__':
    unittest.main()
