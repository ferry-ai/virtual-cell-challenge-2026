"""Fixtures for the general consumer: synthetic banks only, no real data."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    return dict(bytes=Path(path).stat().st_size, sha256=sha(path))


GENES = ['G%02d' % i for i in range(40)]
PANEL = ['G01', 'G02', 'G03']


def bank(root, kernel, unit, rows, counts, masks=None):
    folder = root / 'input' / kernel.split('/')[1] / 'bank' / unit
    folder.mkdir(parents=True)
    frame = pd.DataFrame(rows, columns=['study', 'context', 'donor_or_clone', 'condition', 'modality',
                                        'chemistry', 'target', 'n', 'line_group'])
    frame.to_csv(folder / 'rows.csv', index=False)
    masks = np.ones(counts.shape, bool) if masks is None else masks
    np.savez_compressed(folder / 'count_sum.npz', value=counts)
    np.savez_compressed(folder / 'mask.npz', value=masks)
    (folder / 'complete.json').write_text(json.dumps(dict(rows=len(frame), cells_used=int(frame.n.sum()))))
    files = {n: pin(folder / n) for n in ('count_sum.npz', 'mask.npz', 'rows.csv', 'complete.json')}
    return dict(unit=unit, kernel=kernel, relative_path='bank/' + unit, files=files, producer=dict(version=1))


def run(root, params):
    work = root / 'work'
    work.mkdir()
    (work / 'gene_names.csv').write_text('gene_name\n' + '\n'.join(GENES) + '\n')
    (work / 'pert_counts.csv').write_text('target\n' + '\n'.join(PANEL) + '\n')
    base = dict(kind='fixture', arm='crispri', recipe=dict(phi=.2, min_control_frac=1e-6, min_cells=10.,
                pseudo=.5, pseudo_scale='constant', min_expected=1.),
                axis=dict(sha256=sha(work / 'gene_names.csv'), genes=len(GENES)),
                panel=dict(targets=PANEL, panel_sha256=hashlib.sha256('\n'.join(PANEL).encode()).hexdigest()),
                embedded_inputs={'gene_names.csv': pin(work / 'gene_names.csv')}, context_rename={},
                merge_blocks=False, context_is_donor=False, compare_to=None, hidden_targets=[],
                held_groups=[], protected_units=['h1_test'], min_ram_bytes=0)
    base.update(params)
    (work / 'params.json').write_text(json.dumps(base))
    os.environ['VCC_INPUT_ROOT'] = str(root / 'input')
    os.environ['VCC_WORK_ROOT'] = str(work)
    for module in ('runtime',):
        sys.modules.pop(module, None)
    import runtime
    old = os.getcwd()
    os.chdir(work)
    try:
        runtime.main()
    finally:
        os.chdir(old)
    receipt = json.loads((work / 'fit_receipt.json').read_text())
    with np.load(work / (base['name'] + '.npz'), allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    return receipt, arrays


def rows_for(study, context, donor, targets, n=50, modality='CRISPRi'):
    return [(study, context, donor, 'MISSING', modality, 'MISSING', t, n, 'LINE') for t in targets]


class Consumer(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(7)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def counts(self, n):
        return self.rng.poisson(200, size=(n, len(GENES))).astype(np.float64)

    def test_single_context_matches_original_estimator(self):
        import estimator
        labels = ['NTC', 'G01', 'G02', 'OFFPANEL', 'UNASSIGNED', 'A_B']
        x = self.counts(len(labels))
        x[1, 1] = 5  # knocked-down own gene
        unit = bank(self.root, 'own/kern-a', 'u1', rows_for('s1', 'ctx', 'MISSING', labels), x)
        receipt, arrays = run(self.root, dict(name='src', study='s1', modality='CRISPRi', units=[unit]))
        self.assertEqual(list(arrays['targets']), ['G01', 'G02'])
        obs = pd.DataFrame(dict(target=['non-targeting', 'G01', 'G02'], donor=['d'] * 3,
                                condition=['c'] * 3, n_cells=[50.] * 3))
        direct = estimator.effects_from_pseudobulk(x[:3], obs, np.asarray(GENES), targets=PANEL,
                                                   condition=None, **estimator.CALL)
        np.testing.assert_allclose(arrays['shrunk'], direct['shrunk'], rtol=1e-6)
        np.testing.assert_allclose(arrays['raw'], direct['raw'], rtol=1e-6)
        roles = receipt['inventory'][0]['cells_by_role']
        self.assertEqual(roles, dict(control=50, panel_target=100, outside_frozen_panel=100, aux_unassigned=50))
        own = {r['target']: r for r in receipt['contexts'][0]['own_gene']}
        self.assertLess(own['G01']['raw'], -2)
        self.assertFalse(receipt['mixer_consumed'])

    def test_merge_blocks_equals_summed_counts(self):
        import estimator
        labels = ['NTC', 'G01', 'G03']
        xa, xb = self.counts(3), self.counts(3)
        ua = bank(self.root, 'own/kern-a', 'a', rows_for('s1', 'ctx', 'MISSING', labels, 30), xa)
        ub = bank(self.root, 'own/kern-a', 'b', rows_for('s1', 'ctx', 'MISSING', labels, 20), xb)
        receipt, arrays = run(self.root, dict(name='src', study='s1', modality='CRISPRi', units=[ua, ub],
                                              merge_blocks=True))
        obs = pd.DataFrame(dict(target=['non-targeting', 'G01', 'G03'], donor=['d'] * 3,
                                condition=['c'] * 3, n_cells=[50.] * 3))
        direct = estimator.effects_from_pseudobulk(xa + xb, obs, np.asarray(GENES), targets=PANEL,
                                                   condition=None, **estimator.CALL)
        np.testing.assert_allclose(arrays['shrunk'], direct['shrunk'], rtol=1e-6)
        self.assertEqual(list(arrays['n_cells']), [50, 50])

    def test_unmerged_duplicate_blocks_are_refused(self):
        labels = ['NTC', 'G01']
        ua = bank(self.root, 'own/kern-a', 'a', rows_for('s1', 'ctx', 'MISSING', labels), self.counts(2))
        ub = bank(self.root, 'own/kern-a', 'b', rows_for('s1', 'ctx', 'MISSING', labels), self.counts(2))
        with self.assertRaises(ValueError):
            run(self.root, dict(name='src', study='s1', modality='CRISPRi', units=[ua, ub]))

    def test_contexts_are_estimated_apart_then_equal_weighted(self):
        labels = ['NTC', 'G01']
        x1, x2 = self.counts(2), self.counts(2)
        rows = rows_for('s1', 'c1', 'MISSING', labels, 30, 'KO') + rows_for('s1', 'c2', 'MISSING', labels, 80, 'KO')
        unit = bank(self.root, 'own/kern-a', 'u', rows, np.vstack([x1, x2]))
        receipt, arrays = run(self.root, dict(name='src', study='s1', modality='KO', arm='ko', units=[unit]))
        self.assertEqual(len(receipt['contexts']), 2)
        work = self.root / 'work'
        parts = [np.load(work / ('src__context%d.npz' % i))['shrunk'] for i in (0, 1)]
        np.testing.assert_allclose(arrays['shrunk'], (parts[0] + parts[1]) / 2, rtol=1e-5)
        self.assertEqual(list(arrays['n_cells']), [110])

    def test_donor_pooling_by_context_rename(self):
        labels = ['NTC', 'G02']
        rows = rows_for('s1', 'D1_stim', 'D1', labels, 40, 'KO') + rows_for('s1', 'D2_stim', 'D2', labels, 60, 'KO')
        unit = bank(self.root, 'own/kern-a', 'u', rows, self.counts(4))
        receipt, _ = run(self.root, dict(name='src', study='s1', modality='KO', arm='ko', units=[unit],
                                         context_rename={'D1_stim': 'stim', 'D2_stim': 'stim'}))
        self.assertEqual(len(receipt['contexts']), 1)
        self.assertEqual(receipt['contexts'][0]['donors'], ['D1', 'D2'])
        self.assertEqual(receipt['n_cells'], [100])

    def test_changed_bank_bytes_stop_the_run(self):
        unit = bank(self.root, 'own/kern-a', 'u', rows_for('s1', 'c', 'MISSING', ['NTC', 'G01']), self.counts(2))
        unit['files']['count_sum.npz']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            run(self.root, dict(name='src', study='s1', modality='CRISPRi', units=[unit]))

    def test_wrong_modality_and_missing_controls_stop_the_run(self):
        unit = bank(self.root, 'own/kern-a', 'u', rows_for('s1', 'c', 'MISSING', ['NTC', 'G01']), self.counts(2))
        with self.assertRaises(ValueError):
            run(self.root, dict(name='src', study='s1', modality='KO', units=[unit]))

    def test_unmeasured_gene_stays_nan_and_reference_is_compared(self):
        labels = ['NTC', 'G01']
        x = self.counts(2)
        masks = np.ones(x.shape, bool)
        masks[:, 5] = False
        x[:, 5] = 0
        unit = bank(self.root, 'own/kern-a', 'u', rows_for('s1', 'c', 'MISSING', labels), x, masks)
        ref = self.root / 'input' / 'ref' / 'old.npz.bin'
        ref.parent.mkdir(parents=True)
        with ref.open('wb') as f:
            np.savez_compressed(f, targets=np.asarray(['G01', 'G09']),
                                shrunk=np.ones((2, len(GENES)), np.float32), raw=np.ones((2, len(GENES)), np.float32),
                                se=np.ones((2, len(GENES)), np.float32), n_cells=np.asarray([1, 1]),
                                meta=np.asarray('{}'))
        receipt, arrays = run(self.root, dict(name='src', study='s1', modality='CRISPRi', units=[unit],
                                              compare_to=dict(file='old.npz.bin', **pin(ref))))
        self.assertTrue(np.isnan(arrays['shrunk'][0, 5]))
        self.assertEqual(receipt['comparison']['shared'], 1)
        self.assertEqual(receipt['comparison']['only_reference'], ['G09'])


if __name__ == '__main__':
    unittest.main()
