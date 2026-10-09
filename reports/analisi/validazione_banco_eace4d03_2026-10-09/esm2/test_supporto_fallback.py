"""Fixture tests of the fallback support audit: known counts, known winners, parity with the frozen bench."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import supporto_fallback as S  # noqa: E402

M = S.load_metrics()
import bench_core as core  # noqa: E402  (the frozen bench, on the path after load_metrics)

AMP = 1.576
N_PANEL, N_TRUTH, N_GENES = 42, 40, 80


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root: Path, break_adapter=False, fill='truth'):
    """40 compared targets, 80 genes. The transfer predicts genes 0..49 except one gene per target (inside the
    rank, since each column loses one target of 40); genes 50..79 are filled by the external model only.
    Columns 60 and 61 are panel genes (excluded), 72..79 are unmeasured by the truth."""
    rng = np.random.default_rng(7)
    panel = ['P%02d' % i for i in range(N_PANEL)]
    axis = ['G%02d' % j for j in range(N_GENES)]
    axis[60], axis[61] = panel[0], panel[1]
    truth = rng.normal(0, 0.5, (N_TRUTH, N_GENES)).astype(np.float32)
    se = np.full_like(truth, 0.1)
    truth_file = truth.copy()
    truth_file[:, 72:] = np.nan
    obs_t0 = np.zeros((N_PANEL, N_GENES), bool)
    obs_t0[:, :50] = True
    for i in range(N_PANEL):
        obs_t0[i, i % 50] = False
    t0 = np.where(obs_t0, rng.normal(0, 0.3, (N_PANEL, N_GENES)), 0.0).astype(np.float32)
    t0[:N_TRUTH] += np.where(obs_t0[:N_TRUTH], 0.15 * truth, 0.0).astype(np.float32)  # the transfer knows its targets, weakly
    obs_e2 = np.ones((N_PANEL, N_GENES), bool)
    obs_e2[N_PANEL - 1] = False                                   # a target without features, outside the truth
    e2 = np.zeros((N_PANEL, N_GENES), np.float32)
    if fill == 'truth':                                           # the external model is right on what it fills
        e2[:N_TRUTH] = truth / AMP
    else:                                                         # the external model knows only a common response
        e2[:] = (truth.mean(axis=0, keepdims=True) + 0.3) / AMP
    if fill == 'truth':
        e2[N_TRUTH:N_PANEL - 1] = rng.normal(0, 0.3, (N_PANEL - 1 - N_TRUTH, N_GENES)).astype(np.float32)
    e2 = np.where(obs_e2, e2, 0.0).astype(np.float32)
    e2g = np.where(obs_e2, e2[obs_e2.any(axis=1)].mean(axis=0, keepdims=True), 0.0).astype(np.float32)
    obs_f = obs_t0 | obs_e2
    fallback = np.where(obs_t0, t0, np.where(obs_e2, (e2.astype(np.float64) * AMP).astype(np.float32), 0.0)).astype(np.float32)
    if break_adapter:
        fallback[3, 5] += 0.25                                    # a transfer value changed by the adapter
    files = {}

    def save(name, lfc, obs):
        path = root / (name + '.npz')
        np.savez_compressed(path, targets=np.array(panel), genes=np.array(axis), lfc=lfc, observed=obs)
        files[name] = {'path': str(path), 'sha256': _sha(path)}

    for arm in S.ARMS:
        save(arm, t0, obs_t0)
    save('fallback', fallback, obs_f)
    save('E2', e2, obs_e2)
    save('E2g', e2g, obs_e2)
    truth_path = root / 'truth.npz'
    np.savez_compressed(truth_path, targets=np.array(panel[:N_TRUTH]), shrunk=truth_file, raw=truth_file, se=se,
                        n_cells=np.full(N_TRUTH, 100))
    # the "published" closure results come from the frozen bench itself
    effects = {(a, 'C-X'): (t0, obs_t0) for a in (*S.ARMS, 'T0~gamma0', 'T0~nocis')}
    effects[('E2f', 'C-X')] = (fallback, obs_f)
    folds = {'C-X': {'lineage': 'X', 'truth': [{'table': 'x', 'role': 'primary'}]}}
    table = {'targets': panel[:N_TRUTH], 'shrunk': truth_file, 'raw': truth_file, 'se': se, 'n_cells': np.full(N_TRUTH, 100)}
    res, _, _, _ = core.measure(folds, list(S.ARMS), effects, {'x': table}.__getitem__, panel, axis, log=lambda *_: None,
                                extra_arms=['E2f'], extra_contrasts=[('C_integration', 'E2f', 'T0')])
    results_path = root / 'results.json'
    results_path.write_text(json.dumps({'folds': res}, default=float), encoding='utf-8')
    return {'fold': 'C-X', 'truth_table': 'x', 'amplitude': AMP, 'arms': {a: files[a] for a in S.ARMS},
            'fallback': files['fallback'], 'E2': files['E2'], 'E2g': files['E2g'],
            'truth': {'path': str(truth_path), 'sha256': _sha(truth_path)},
            'closure_results': {'path': str(results_path), 'sha256': _sha(results_path)}}


class SupportAudit(unittest.TestCase):
    def test_counts_parity_and_reading_when_the_fill_is_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = S.audit(build(Path(tmp)), M)
        self.assertTrue(doc['parity']['passed'], doc['parity'])
        self.assertTrue(doc['adapter']['passed'], doc['adapter'])
        filled = doc['support']['filled']
        # 40 compared targets x (30 genes the transfer never predicts + its one missing gene)
        self.assertEqual(filled['in_targets_compared'], 40 * 31)
        self.assertEqual(filled['not_judgeable_truth_unmeasured'], 40 * 8)
        self.assertEqual(filled['not_judgeable_panel_gene_column'], 40 * 2)
        self.assertEqual(filled['judgeable'], 40 * 31 - 320 - 80)
        self.assertEqual(filled['judgeable_in_rank_95'], 40)             # only the one missing gene per target
        self.assertFalse(filled['measure_covers_the_change'])
        self.assertEqual(doc['support']['genes_for_rank_95'], 50)
        # the frozen own-support contrast is reproduced for every measure
        for m, entry in doc['own_support_as_published'].items():
            if entry['published_mean'] is not None and entry['mean'] is not None:
                self.assertAlmostEqual(entry['mean'], entry['published_mean'], places=9, msg=m)
        # a fill equal to the truth: no error left on the filled pairs, the swap is worse than zero
        only = doc['filled_only']
        self.assertEqual(only['targets_with_enough_filled_pairs'], 40)
        self.assertLess(only['levels']['esm2']['mse_vs_zero'], 1e-6)
        self.assertGreater(only['levels']['swapped']['mse_vs_zero'], 1.5)
        reading = doc['reading']
        self.assertTrue(reading['fallback_reduces_error'])
        self.assertTrue(reading['gain_is_target_specific'])
        self.assertFalse(reading['generic_part_is_enough'])
        self.assertTrue(doc['generator_view']['disc95g_control_passed'])
        self.assertTrue(reading['fallback_discriminates_better'])

    def test_a_common_response_is_not_called_target_specific(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = S.audit(build(Path(tmp), fill='common'), M)
        self.assertTrue(doc['parity']['passed'] and doc['adapter']['passed'])
        reading = doc['reading']
        self.assertFalse(reading['gain_is_target_specific'])
        contrast = doc['filled_only']['contrasts']['esm2-swapped']['mse_vs_zero']
        self.assertLess(abs(contrast['mean']), 1e-6)                    # every target gets the same fill

    def test_a_changed_transfer_value_stops_before_any_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = build(Path(tmp), break_adapter=True)
            doc = S.audit(spec, M)
        self.assertIn('stopped', doc)
        self.assertNotIn('generator_view', doc)

    def test_a_changed_input_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = build(Path(tmp))
            spec['E2']['sha256'] = '0' * 64
            with self.assertRaises(SystemExit):
                S.audit(spec, M)


if __name__ == '__main__':
    unittest.main()
