"""The pooled call matches script 98. The post-shrink average does not. The launcher does not push."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vcc2026.multisource import effects_from_pseudobulk as original_call

import h1_joint
import launch_r7
import mix_model
import pins
import pool_adapter


def _original(matrix, obs, genes, **kwargs):
    return original_call(matrix, pd.DataFrame(obs), genes, **kwargs)


def _banks():
    control = np.array([20.0, 1.0])
    half_a = np.array([3.0, 1.0])
    half_b = np.array([9.0, 1.0])
    left = [{'donor': 'd', 'target': 'non-targeting', 'n_cells': 100.0, 'counts': control},
            {'donor': 'd', 'target': 'T', 'n_cells': 30.0, 'counts': half_a}]
    right = [{'donor': 'd', 'target': 'non-targeting', 'n_cells': 100.0, 'counts': control.copy()},
             {'donor': 'd', 'target': 'T', 'n_cells': 30.0, 'counts': half_b}]
    truth = [{'donor': 'd', 'target': 'non-targeting', 'n_cells': 100.0, 'counts': control.copy()},
             {'donor': 'd', 'target': 'T', 'n_cells': 30.0, 'counts': half_a.copy()},
             {'donor': 'd', 'target': 'T', 'n_cells': 30.0, 'counts': half_b.copy()}]
    return left, right, truth


class PoolTests(unittest.TestCase):
    def test_postshrink_average_differs_and_the_pool_matches(self):
        genes = ['g0', 'g1']
        left, right, truth = _banks()
        pooled, info = pool_adapter.pool_records([left, right])
        self.assertEqual(info['duplicate_controls_dropped'], 1)
        new = pool_adapter.estimate_pooled(pooled, genes, ['T'], effects_fn=_original, condition=None)
        truth_rows, _ = pool_adapter.pool_records([truth])
        original = pool_adapter.estimate_pooled(truth_rows, genes, ['T'], effects_fn=_original, condition=None)
        np.testing.assert_allclose(new['shrunk'], original['shrunk'])
        np.testing.assert_allclose(new['raw'], original['raw'])
        np.testing.assert_allclose(new['se'], original['se'])
        old_left = pool_adapter.estimate_pooled(left, genes, ['T'], effects_fn=_original, condition=None)
        old_right = pool_adapter.estimate_pooled(right, genes, ['T'], effects_fn=_original, condition=None)
        averaged = 0.5 * (old_left['shrunk'] + old_right['shrunk'])
        self.assertFalse(np.allclose(averaged, original['shrunk']))
        ported = pool_adapter.estimate_pooled(truth_rows, genes, ['T'], condition=None)
        np.testing.assert_allclose(ported['shrunk'], original['shrunk'], equal_nan=True)
        np.testing.assert_allclose(ported['raw'], original['raw'], equal_nan=True)
        np.testing.assert_allclose(ported['se'], original['se'], equal_nan=True)

    def test_panel_projection_matches_the_direct_call_and_changes_centering(self):
        genes = ['g0', 'g1']
        records = [
            {'donor': 'd', 'target': 'non-targeting', 'n_cells': 100.0, 'counts': np.array([20.0, 1.0])},
            {'donor': 'd', 'target': 'A', 'n_cells': 40.0, 'counts': np.array([3.0, 1.0])},
            {'donor': 'd', 'target': 'B', 'n_cells': 40.0, 'counts': np.array([30.0, 1.0])},
            {'donor': 'd', 'target': 'C', 'n_cells': 40.0, 'counts': np.array([9.0, 1.0])},
        ]
        panel = ['A', 'C']
        full = pool_adapter.estimate_pooled(records, genes, ['A', 'B', 'C'], effects_fn=_original, condition=None)
        direct = pool_adapter.estimate_pooled(records, genes, panel, effects_fn=_original, condition=None)
        projected = pool_adapter.project_rows(
            full['targets'], full['shrunk'], full['raw'], full['se'], full['n_cells'], panel)
        np.testing.assert_allclose(projected['shrunk'], direct['shrunk'], equal_nan=True)
        np.testing.assert_allclose(projected['raw'], direct['raw'], equal_nan=True)
        np.testing.assert_allclose(projected['se'], direct['se'], equal_nan=True)
        self.assertEqual(projected['targets'], direct['targets'])
        self.assertEqual(projected['unused_targets'], ['B'])
        wide = mix_model.Table('s', full['targets'], full['shrunk'], full['raw'], full['se'], full['n_cells'], {})
        narrow = mix_model.project_table(wide, panel)
        self.assertFalse(np.allclose(wide.common(), narrow.common(), equal_nan=True))
        on_union, _ = mix_model.mix([wide], panel, gamma=1.0)
        on_panel, _ = mix_model.mix([narrow], panel, gamma=1.0)
        self.assertFalse(np.allclose(on_union, on_panel, equal_nan=True))

    def test_per_target_spill_matches_one_call(self):
        genes = ['g0', 'g1']
        records = [
            {'donor': 'd', 'target': 'non-targeting', 'n_cells': 100.0, 'counts': np.array([20.0, 1.0])},
            {'donor': 'd', 'target': 'A', 'n_cells': 40.0, 'counts': np.array([3.0, 1.0])},
            {'donor': 'd', 'target': 'C', 'n_cells': 40.0, 'counts': np.array([9.0, 1.0])},
        ]
        one = pool_adapter.estimate_spilled(
            records, genes, ['A', 'C'], budget_bytes=10**9, effects_fn=_original, condition=None)
        spilled = pool_adapter.estimate_spilled(
            records, genes, ['A', 'C'], budget_bytes=2 * 2 * 8, effects_fn=_original, condition=None)
        self.assertEqual(one['schedule'], 'one_call')
        self.assertEqual(spilled['schedule'], 'per_target_equivalent')
        np.testing.assert_allclose(spilled['shrunk'], one['shrunk'], equal_nan=True)
        np.testing.assert_allclose(spilled['raw'], one['raw'], equal_nan=True)
        np.testing.assert_allclose(spilled['se'], one['se'], equal_nan=True)

    def test_off_axis_panel_target_stays_a_perturbation_id(self):
        panel = {'ONPANEL'}
        self.assertEqual(h1_joint.classify('ONPANEL', panel), 'ONPANEL')
        self.assertEqual(h1_joint.classify('NTC', panel), 'non-targeting')
        self.assertIsNone(h1_joint.classify('FOO+BAR', panel))
        self.assertIsNone(h1_joint.classify('UNASSIGNED', panel))
        self.assertEqual(h1_joint.classify('ENSG0001', panel), 'off_panel')

    def test_two_h1_fragments_do_not_vote(self):
        table = mix_model.Table
        one = table('h1_train', ['T'], np.ones((1, 1)), np.ones((1, 1)), np.ones((1, 1)), np.array([10]),
                    {'transfer_source_id': 'h1'})
        two = table('h1_val', ['T'], np.full((1, 1), 3), np.full((1, 1), 3), np.ones((1, 1)), np.array([10]),
                    {'transfer_source_id': 'h1'})
        with self.assertRaises(mix_model.MixBlocked):
            mix_model.one_vote([one, two])
        with self.assertRaises(mix_model.MixBlocked):
            mix_model.collapse_fragment({'tables': [one, two]}, 'h1')


class JointRunTests(unittest.TestCase):
    def test_tiny_banks_match_the_original_call_on_the_panel(self):
        panel = ['A']
        pin = {'n': 1, 'targets': panel,
               'panel_sha256': hashlib.sha256('A'.encode('utf-8')).hexdigest()}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'out'
            control = np.array([20.0, 1.0])
            banks = {
                'h1_train': [('non-targeting', control, 100.0), ('A', np.array([3.0, 1.0]), 30.0),
                             ('B', np.array([8.0, 1.0]), 30.0)],
                'h1_val': [('non-targeting', control.copy(), 100.0), ('A', np.array([9.0, 1.0]), 30.0)],
            }
            params_banks = []
            for unit, rows in banks.items():
                bank = root / unit
                bank.mkdir()
                frame = pd.DataFrame({
                    'line_group': ['H1'] * len(rows),
                    'target': [item[0] for item in rows],
                    'donor_or_clone': ['d'] * len(rows),
                    'n': [item[2] for item in rows],
                    'study': ['vcc2025_h1'] * len(rows),
                })
                frame.to_csv(bank / 'rows.csv', index=False)
                np.savez_compressed(bank / 'count_sum.npz', value=np.vstack([item[1] for item in rows]))
                np.savez_compressed(bank / 'mask.npz', value=np.ones((len(rows), 2), dtype=bool))
                params_banks.append({'unit': unit, 'relative_path': unit})
            params = {'banks': params_banks, 'genes': ['g0', 'g1'], 'axis_sha256': 'tiny',
                      'panel': pin, 'min_expected': 1, 'pseudo_scale': 'constant'}
            self.assertEqual(h1_joint.run(root, params, output), 'derived')
            model = json.loads((output / 'source_model.json').read_text(encoding='utf-8'))
            self.assertEqual(model['unused_targets'], ['B'])
            self.assertEqual(model['panel_targets_present'], ['A'])
            self.assertFalse(model['h1_test_included'])
            receipts = [json.loads(path.read_text(encoding='utf-8'))
                        for path in (output / 'splits').glob('*/receipt.json')]
            production = [item for item in receipts
                          if item['regime'] == 'C' and item['fold'] is None and item['held_group'] != 'H1']
            self.assertTrue(production)
            self.assertEqual(len({item['statistics_id'] for item in production}), 1)
            self.assertTrue(all(item['arrays'] == ['shrunk', 'raw', 'se'] for item in production))
            held = [item for item in receipts if item['held_group'] == 'H1' and item['regime'] == 'C']
            self.assertEqual(held[0]['status'], 'excluded_before_statistics')
            with np.load(output / production[0]['file']) as pack:
                got = {key: np.array(pack['0_' + key]) for key in ('shrunk', 'raw', 'se')}
            truth = [
                {'donor': 'd', 'target': 'non-targeting', 'n_cells': 100.0, 'counts': control.copy()},
                {'donor': 'd', 'target': 'A', 'n_cells': 30.0, 'counts': np.array([3.0, 1.0])},
                {'donor': 'd', 'target': 'A', 'n_cells': 30.0, 'counts': np.array([9.0, 1.0])},
            ]
            original = pool_adapter.estimate_pooled(truth, ['g0', 'g1'], ['A'], effects_fn=_original, condition=None)
            np.testing.assert_allclose(got['shrunk'], original['shrunk'], equal_nan=True)
            np.testing.assert_allclose(got['raw'], original['raw'], equal_nan=True)
            np.testing.assert_allclose(got['se'], original['se'], equal_nan=True)
            averaged_banks = []
            for rows in banks.values():
                kept = [item for item in rows if item[0] != 'B']
                averaged_banks.append([
                    {'donor': 'd', 'target': item[0], 'n_cells': item[2], 'counts': item[1]} for item in kept])
            left = pool_adapter.estimate_pooled(averaged_banks[0], ['g0', 'g1'], ['A'], effects_fn=_original, condition=None)
            right = pool_adapter.estimate_pooled(averaged_banks[1], ['g0', 'g1'], ['A'], effects_fn=_original, condition=None)
            self.assertFalse(np.allclose(0.5 * (left['shrunk'] + right['shrunk']), original['shrunk'], equal_nan=True))


class LaunchTests(unittest.TestCase):
    def test_aliases_and_no_push(self):
        self.assertTrue(launch_r7.module_does_not_push())
        resolved = launch_r7.logical_sources(launch_r7._receipts(launch_r7.SOURCEFITS),
                                             launch_r7._receipts(launch_r7.JOINTS))
        self.assertEqual(resolved['multi'], {'h1': ['h1_train', 'h1_val']})
        slugs = [item['slug'] for item in resolved['sources'] + resolved['joints']]
        for failed in launch_r7.FAILED:
            self.assertNotIn(failed, slugs)
        self.assertIn('davideferrante11/vcc-effects-cd4-stim8hr-joint-r5-retry1', slugs)
        self.assertIn('davideferrante11/vcc-effects-kolf-metabolic-r4-retry1', slugs)
        self.assertIn('davideferrante11/vcc-effects-kolf-strong-r4-retry1', slugs)
        self.assertIn('davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1', slugs)
        panel = launch_r7.bound_panel()
        self.assertEqual(panel['n'], 300)
        identity = launch_r7.h1_identity(panel['targets'])
        self.assertEqual(identity['h1_train_targets'], 150)
        self.assertEqual(identity['h1_val_targets'], 50)
        self.assertEqual(identity['shared_targets'], 0)
        self.assertEqual(identity['local_index_on_panel']['h1_train'], 13)
        self.assertEqual(identity['local_index_on_panel']['h1_val'], 4)
        axis = launch_r7._axis()
        jobs = [launch_r7.h1_job(resolved, axis, panel), launch_r7.hek_job(resolved, axis),
                launch_r7.mix_job(resolved, axis, identity, panel)]
        joined = '\n'.join(slug for job in jobs for slug in job['kernel_sources'])
        for failed in launch_r7.FAILED:
            self.assertNotIn(failed, [slug for job in jobs for slug in job['kernel_sources']])
        self.assertNotIn('vcc-effects-h1-train-r4', joined)
        self.assertNotIn('vcc-effects-h1-val-r4', joined)
        self.assertNotIn(pins.OPEN_PARENT_KERNEL, json.dumps([job['params'] for job in jobs]))
        self.assertEqual(len(jobs[2]['params']['split_manifest']), 72)
        self.assertIn('davideferrante11/vcc-effects-h1-joint-r7', jobs[2]['kernel_sources'])
        self.assertIn('davideferrante11/vcc-effects-kolf-metabolic-r4-retry1', jobs[2]['kernel_sources'])
        self.assertIn('davideferrante11/vcc-effects-kolf-strong-r4-retry1', jobs[2]['kernel_sources'])
        self.assertNotIn('davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1', jobs[2]['kernel_sources'])
        self.assertIn('davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1', jobs[2]['deferred_kernels'])
        self.assertTrue(jobs[0]['push_now'])
        self.assertTrue(jobs[1]['push_now'])
        self.assertFalse(jobs[2]['push_now'])
        self.assertEqual(jobs[0]['params']['panel']['panel_sha256'], pins.PANEL_SHA256)


if __name__ == '__main__':
    unittest.main()
