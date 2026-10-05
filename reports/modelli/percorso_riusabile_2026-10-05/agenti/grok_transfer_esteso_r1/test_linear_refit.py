"""Tiny fixtures for the fail-closed linear transfer. Not a corpus fit."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from linear_effects import estimate_source, load_count_sum  # noqa: E402
from linear_transfer import FitBlocked, cloud_params_refused, mix_arm, refuse, run_refit  # noqa: E402
from pins import MANIFEST_SHA256, ORIGINAL_SOURCES, REPO  # noqa: E402
from reconcile import build_admission, load_manifest, write_protocol  # noqa: E402
from vcc2026.multisource import AxisTable  # noqa: E402


def row(donor, condition, target, counts_n, modality='CRISPRi', line='CD4', components=None):
    item = {'study': 'study', 'context': condition, 'donor_or_clone': donor, 'condition': condition,
            'modality': modality, 'chemistry': 'CRISPRi', 'target': target, 'n': counts_n,
            'line_group': line}
    if components is not None:
        item['target_components'] = components
    return item


def frame(items):
    return pd.DataFrame(items)


class Effects(unittest.TestCase):
    def test_min_expected_ignores_the_target_count(self):
        genes = ['g0', 'g1']
        rows = frame([row('d', 'rest', 'NTC', 20), row('d', 'rest', 'T', 20)])
        counts = np.array([[0.4, 1000], [50, 50]], dtype=float)
        result = estimate_source(rows, counts, np.ones(2, dtype=bool), genes, 'src', modality='CRISPRi')
        table = result['tables'][0]
        self.assertEqual(table.targets, ['T'])
        self.assertTrue(np.isnan(table.shrunk[0, 0]))
        self.assertTrue(np.isfinite(table.shrunk[0, 1]))
        self.assertEqual(table.meta['called_with']['matrix'], 'count_sum')

    def test_unmeasured_gene_cannot_vote(self):
        genes = ['g0', 'g1']
        rows = frame([row('d', 'rest', 'NTC', 20), row('d', 'rest', 'T', 20)])
        counts = np.array([[100, 100], [50, 50]], dtype=float)
        mask = np.array([[True, True], [False, True]])
        table = estimate_source(rows, counts, mask, genes, 'src', modality='CRISPRi')['tables'][0]
        self.assertTrue(np.isnan(table.raw[0, 0]))
        self.assertTrue(np.isfinite(table.raw[0, 1]))

    def test_conditions_are_not_pooled(self):
        genes = ['g0']
        rows = frame([row('d', 'rest', 'NTC', 20), row('d', 'rest', 'T', 20),
                      row('d', 'stim', 'NTC', 20), row('d', 'stim', 'T', 20)])
        counts = np.array([[10, ], [100, ], [100, ], [10, ]], dtype=float)
        tables = estimate_source(rows, counts, np.ones(1, dtype=bool), genes, 'src', modality='CRISPRi')['tables']
        self.assertEqual([table.meta['condition'] for table in tables], ['rest', 'stim'])
        values = [float(table.raw[0, 0]) for table in tables]
        self.assertLess(values[0] * values[1], 0)

    def test_held_group_and_compound_component_are_removed(self):
        genes = ['g0']
        rows = frame([
            row('d', 'rest', 'NTC', 20),
            row('d', 'rest', 'T', 20),
            row('h', 'rest', 'NTC', 20, line='HepG2'),
            row('h', 'rest', 'SECRET', 50, line='HepG2'),
            row('d', 'rest', 'AB', 20, components=['A', 'B']),
        ])
        counts = np.ones((5, 1)) * 30
        result = estimate_source(rows, counts, np.ones(1, dtype=bool), genes, 'src', modality='CRISPRi',
                                held_groups={'HepG2'}, hidden_targets={'B'})
        reasons = {item['reason'] for item in result['dropped_rows']}
        self.assertEqual(reasons, {'held_group', 'hidden_component'})
        self.assertEqual(result['tables'][0].targets, ['T'])

    def test_unknown_control_label_is_not_a_control(self):
        genes = ['g0']
        rows = frame([row('d', 'rest', 'control', 20), row('d', 'rest', 'T', 20)])
        counts = np.array([[30], [30]], dtype=float)
        with self.assertRaises(ValueError):
            estimate_source(rows, counts, np.ones(1, dtype=bool), genes, 'src', modality='CRISPRi')

    def test_mean_proportion_file_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mean_proportion.npz'
            np.savez_compressed(path, value=np.ones((1, 1)))
            with self.assertRaises(ValueError):
                load_count_sum(path, '0' * 64, path.stat().st_size)


class Transfer(unittest.TestCase):
    def test_mix_uses_frozen_weight_and_amplitude(self):
        from vcc2026.multisource import mix
        left = AxisTable('k562', ['T1', 'T2'], np.array([[4.0, 0.0], [0.0, 0.0]], np.float32),
                         np.array([[4.0, 0.0], [0.0, 0.0]], np.float32), np.ones((2, 2), np.float32),
                         np.array([100.0, 100.0]), {})
        right = AxisTable('cd4_mix', ['T1', 'T2'], np.array([[0.0, 0.0], [0.0, 4.0]], np.float32),
                          np.array([[0.0, 0.0], [0.0, 4.0]], np.float32), np.ones((2, 2), np.float32),
                          np.array([100.0, 100.0]), {})
        effects, denominator = mix_arm([left, right], ['T1', 'T2'], ['k562', 'cd4_mix'],
                                       {'T1': ['T1'], 'T2': ['T2']})
        manual, manual_den = mix([left, right], ['T1', 'T2'], weights={'k562': 1.0, 'cd4_mix': 1.0},
                                 gamma=1.0, reliability_scale=100.0)
        self.assertTrue(np.allclose(effects, manual * 1.576))
        self.assertTrue(np.allclose(denominator, manual_den))
        self.assertFalse(np.allclose(effects, 0))

    def test_missing_component_map_blocks(self):
        table = AxisTable('k562', ['T'], np.ones((1, 1), np.float32), np.ones((1, 1), np.float32),
                          np.ones((1, 1), np.float32), np.array([10.0]), {})
        with self.assertRaises(FitBlocked):
            mix_arm([table], ['T'], ['k562'], {})

    def test_real_admission_blocks_before_fit(self):
        load_manifest()
        admission = build_admission()
        self.assertFalse(admission['fit_admitted'])
        self.assertEqual(admission['manifest_sha256'], MANIFEST_SHA256)
        self.assertGreater(admission['n_records'], 0)
        self.assertEqual(admission['fit_inputs'], [])
        with self.assertRaises(FitBlocked):
            run_refit(admission, {'original': 'must not be read'}, ['T'], {'T': ['T']})
        with self.assertRaises(FitBlocked):
            cloud_params_refused({'fit_admitted': False, 'matrix': 'count_sum',
                                  'manifest_sha256': MANIFEST_SHA256})

    def test_forbidden_dataset_blocks_even_if_flagged_admitted(self):
        admission = {'manifest_sha256': MANIFEST_SHA256, 'fit_admitted': True, 'records': [],
                     'fit_inputs': [{'dataset': 'davideferrante11/rlead-bench-cube-r2', 'version': 1,
                                     'receipt_sha256': 'a', 'producer': 'p', 'matrix': 'count_sum',
                                     'transfer_source_id': 'k562'}]}
        with self.assertRaises(FitBlocked):
            run_refit(admission, {}, ['T'], {'T': ['T']}, allow_local_fit=True)

    def test_opened_gate_mixes_original_and_expanded_on_a_fixture(self):
        def make(name, values):
            arr = np.array(values, np.float32)
            return AxisTable(name, ['T', 'U'], arr, arr.copy(), np.ones_like(arr), np.array([100.0, 100.0]), {})
        original = [make(name, [[1.0, 0.0], [0.0, 1.0]]) for name in ORIGINAL_SOURCES]
        extra = make('rpe1::rest', [[5.0, 0.0], [0.0, 1.0]])
        admission = {
            'manifest_sha256': MANIFEST_SHA256, 'fit_admitted': True, 'records': [],
            'fit_inputs': [{'dataset': 'owner/explicit-r1', 'version': 3, 'receipt_sha256': 'b',
                            'producer': 'owner/producer-r1', 'matrix': 'count_sum',
                            'transfer_source_id': 'rpe1::rest'}],
            'required_context_ids': ['remote/rpe1'], 'loaded_context_ids': ['remote/rpe1'],
            'expanded_source_names': list(ORIGINAL_SOURCES) + ['rpe1::rest'],
            'hidden_targets': [], 'emission': {'effects_scale': 1.5},
        }
        out = run_refit(admission, {'original': original, 'expanded': original + [extra]}, ['T', 'U'],
                        {'T': ['T'], 'U': ['U']}, allow_local_fit=True)
        self.assertFalse(np.allclose(out['original'][0], out['expanded'][0]))

    def test_protocol_is_written_without_a_score(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'protocol.json'
            payload = write_protocol(path)
        self.assertTrue(payload['reading']['loss_is_not_a_decision_metric'])
        self.assertNotIn('observed_score', payload)

    def test_refuse_writes_blockers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'refusal.json'
            payload = refuse({'fit_admitted': False, 'blockers': ['roles open'], 'records': [],
                              'manifest_sha256': MANIFEST_SHA256, 'fit_inputs': []}, path)
        self.assertFalse(payload['fit_launched'])
        self.assertIn('roles open', payload['blockers'])


class Pin(unittest.TestCase):
    def test_recipe_matches_the_frozen_arm(self):
        recipe = json.loads((REPO / 'configs/recipes/t25.json').read_text(encoding='utf-8'))
        self.assertEqual(recipe['gamma'], 1.0)
        self.assertEqual(recipe['reliability_scale'], 100)
        for spec in recipe['contexts'].values():
            self.assertEqual(spec['amplitude'], 1.576)
            self.assertEqual(set(spec['weights']), set(ORIGINAL_SOURCES))
            self.assertTrue(all(value == 1.0 for value in spec['weights'].values()))
