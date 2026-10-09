"""Fixture tests of the external-arm reader: a helpful residual is seen, an anchor with fewer pairs is counted."""
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
import lettura_esterni as L  # noqa: E402

M, core = L.load_bench()
N_PANEL, N_TRUTH, N_GENES = 42, 40, 80


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root: Path, residual=0.3):
    """T0 predicts genes 0..59; the nested anchor A0 is T0 without genes 40..59 (a source less); the model export
    AN is A0 plus `residual` x truth on A0's own pairs (same mask)."""
    rng = np.random.default_rng(11)
    panel = ['P%02d' % i for i in range(N_PANEL)]
    axis = ['G%02d' % j for j in range(N_GENES)]
    truth = rng.normal(0, 0.5, (N_TRUTH, N_GENES)).astype(np.float32)
    se = np.full_like(truth, 0.1)
    obs_t0 = np.zeros((N_PANEL, N_GENES), bool)
    obs_t0[:, :60] = True
    t0 = np.where(obs_t0, rng.normal(0, 0.3, (N_PANEL, N_GENES)), 0.0).astype(np.float32)
    t0[:N_TRUTH] += np.where(obs_t0[:N_TRUTH], 0.15 * truth, 0.0).astype(np.float32)
    obs_a0 = obs_t0.copy()
    obs_a0[:, 40:] = False
    a0 = np.where(obs_a0, t0, 0.0).astype(np.float32)
    an = a0.copy()
    an[:N_TRUTH] += np.where(obs_a0[:N_TRUTH], residual * truth, 0.0).astype(np.float32)
    files = {}

    def save(name, lfc, obs):
        path = root / (name + '.npz')
        np.savez_compressed(path, targets=np.array(panel), genes=np.array(axis), lfc=lfc, observed=obs)
        files[name] = {'path': str(path), 'sha256': _sha(path)}

    for arm in L.ARMS:
        save(arm, t0, obs_t0)
    save('A0', a0, obs_a0)
    save('AN', an, obs_a0)
    truth_path = root / 'truth.npz'
    np.savez_compressed(truth_path, targets=np.array(panel[:N_TRUTH]), shrunk=truth, raw=truth, se=se,
                        n_cells=np.full(N_TRUTH, 100))
    effects = {(a, 'C-X'): (t0, obs_t0) for a in (*L.ARMS, 'T0~gamma0', 'T0~nocis')}
    table = {'targets': panel[:N_TRUTH], 'shrunk': truth, 'raw': truth, 'se': se, 'n_cells': np.full(N_TRUTH, 100)}
    res, _, _, _ = core.measure({'C-X': {'lineage': 'X', 'truth': [{'table': 'x', 'role': 'primary'}]}}, list(L.ARMS),
                                effects, {'x': table}.__getitem__, panel, axis, log=lambda *_: None)
    published = root / 'results.json'
    published.write_text(json.dumps({'folds': res}, default=float), encoding='utf-8')
    return {'fold': 'C-X', 'truth_table': 'x', 'lineage': 'X', 'arms': {a: files[a] for a in L.ARMS},
            'extra': {'A0': files['A0'], 'AN': files['AN']}, 'pairs': [['AN', 'A0'], ['A0', 'T0'], ['AN', 'T0']],
            'truth': {'path': str(truth_path), 'sha256': _sha(truth_path)},
            'published_results': {'path': str(published), 'sha256': _sha(published)}}


class ExternalArms(unittest.TestCase):
    def test_a_helpful_residual_on_the_same_mask(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = L.read_fold(build(Path(tmp)), M, core)
        self.assertTrue(doc['parity']['passed'], doc['parity'])
        cov = doc['coverage']['AN-A0']
        self.assertTrue(cov['same_mask'])
        self.assertEqual(cov['predicted_only_by_first'] + cov['predicted_only_by_second'], 0)
        self.assertEqual(cov['changed_pairs'], 40 * 40)                       # the residual touches A0's pairs of 40 targets
        frozen = doc['frozen_bench']['contrasts']['X_AN_minus_A0']['measures']['disc95']
        self.assertTrue(frozen['resolved'] and frozen['mean'] > 0)
        view = doc['generator_view']['contrasts']['AN-A0']
        self.assertTrue(view['disc95g']['resolved'] and view['disc95g']['mean'] > 0)
        self.assertTrue(view['r_spec']['resolved'] and view['r_spec']['mean'] > 0)

    def test_an_anchor_with_fewer_pairs_is_counted_as_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = L.read_fold(build(Path(tmp)), M, core)
        cov = doc['coverage']['A0-T0']
        self.assertFalse(cov['same_mask'])
        self.assertEqual(cov['predicted_only_by_second'], 40 * 20)            # genes 40..59, lost with the source
        self.assertEqual(cov['predicted_by_both_with_different_values'], 0)
        self.assertTrue(doc['generator_view']['disc95g_control_passed'])

    def test_no_residual_means_no_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = L.read_fold(build(Path(tmp), residual=0.0), M, core)
        self.assertEqual(doc['coverage']['AN-A0']['changed_pairs'], 0)
        for m, entry in doc['generator_view']['contrasts']['AN-A0'].items():
            self.assertFalse(entry['resolved'], m)

    def test_a_changed_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = build(Path(tmp))
            spec['extra']['AN']['sha256'] = '0' * 64
            with self.assertRaises(SystemExit):
                L.read_fold(spec, M, core)


if __name__ == '__main__':
    unittest.main()
