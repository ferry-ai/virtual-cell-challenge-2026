"""Equivalence to the original estimator and mix. Fixtures, not a bank run."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vcc2026.multisource import AxisTable, effects_from_pseudobulk, mix

import cd4_joint
import launch_r5
import mix_model

CALL = {
    'phi': 0.2,
    'min_control_frac': 1e-6,
    'min_cells': 10.0,
    'pseudo': 0.5,
    'pseudo_scale': 'constant',
    'min_expected': 1.0,
}
GENES = np.array(['g0', 'g1', 'g2'])


def _original(matrix, obs, targets, condition):
    return effects_from_pseudobulk(matrix, obs, GENES, targets=targets, condition=condition, **CALL)


def _as_arrays(result):
    shrunk = result.shrunk if hasattr(result, 'shrunk') else result['shrunk']
    raw = result.raw if hasattr(result, 'raw') else result['raw']
    se = result.se if hasattr(result, 'se') else result['se']
    n_cells = result.n_cells if hasattr(result, 'n_cells') else result['n_cells']
    targets = result.targets if hasattr(result, 'targets') else result['targets']
    control = result.control_mean if hasattr(result, 'control_mean') else result['control_mean']
    return targets, np.asarray(shrunk), np.asarray(raw), np.asarray(se), np.asarray(n_cells), np.asarray(control)


def _multi_donor():
    """Two effect donors plus a control-only donor. D1 target is split across rows."""
    rows = [
        ('D1', 'non-targeting', 100, [20, 0, 5000]),
        ('D1', 'non-targeting', 20, [5, 0, 1000]),
        ('D1', 'T', 40, [800, 0, 100]),
        ('D1', 'T', 30, [200, 0, 50]),
        ('D1', 'OFFAXIS', 25, [50, 0, 80]),
        ('D1', 'ENSG00000198888', 25, [10, 0, 40]),
        ('D2', 'non-targeting', 80, [30, 0, 4000]),
        ('D2', 'T', 4000, [40, 0, 3900]),
        ('D3', 'non-targeting', 50, [0, 8000, 20]),
    ]
    obs = pd.DataFrame({
        'donor': [row[0] for row in rows],
        'target': [row[1] for row in rows],
        'condition': 'Rest',
        'n_cells': [row[2] for row in rows],
    })
    matrix = np.asarray([row[3] for row in rows], dtype=np.float64)
    return matrix, obs


class JointTests(unittest.TestCase):
    def test_compact_matches_original_and_not_the_donor_average(self):
        matrix, obs = _multi_donor()
        targets = ['ENSG00000198888', 'OFFAXIS', 'T']
        original = _original(matrix, obs, targets, 'Rest')
        frame = pd.DataFrame({
            'donor_or_clone': obs['donor'], 'target': obs['target'], 'condition': obs['condition'],
            'n': obs['n_cells'], 'line_group': 'CD4T',
        })
        kept, decisions, _report = cd4_joint.prepare_bank_frame(
            frame, GENES, 'Rest', {'NTC': 'non-targeting'}, {}, [])
        compact, records, info = cd4_joint.compact_kept(matrix, kept, decisions)
        self.assertIn('D3', info['donors_with_controls'])
        self.assertEqual(info['donors_without_controls'], [])
        attached = cd4_joint.attach_counts(records, compact)
        stack_budget = compact.shape[0] * compact.shape[1] * 8
        one = cd4_joint.effects_from_records(attached, GENES, targets, CALL, stack_budget)
        per_target = cd4_joint.effects_from_records(attached, GENES, targets, CALL, stack_budget - 1)
        self.assertEqual(one['schedule'], 'one_call')
        self.assertEqual(per_target['schedule'], 'per_target_equivalent')
        for result in (one, per_target):
            got = _as_arrays(result)
            ref = _as_arrays(original)
            self.assertEqual(list(got[0]), list(ref[0]))
            for left, right in zip(got[1:5], ref[1:5]):
                np.testing.assert_allclose(left, right, rtol=1e-6, atol=1e-6, equal_nan=True)
            np.testing.assert_allclose(got[5], ref[5], rtol=1e-6, atol=1e-6)
        from estimator_core import effects_from_pseudobulk as port
        compact_obs = pd.DataFrame({
            'target': [item['target'] for item in records],
            'donor': [item['donor'] for item in records],
            'condition': 'group',
            'n_cells': [item['n_cells'] for item in records],
        })
        ported = port(compact, compact_obs, GENES, targets=targets, condition='group', **CALL)
        original_compact = effects_from_pseudobulk(
            compact, compact_obs, GENES, targets=targets, condition='group', **CALL)
        np.testing.assert_allclose(ported['shrunk'], original_compact.shrunk, rtol=0, atol=0, equal_nan=True)
        # Separate donor fits, then a weighted mean of already-shrunk rows.
        donor_rows = []
        for donor in ('D1', 'D2'):
            mask = obs['donor'].to_numpy() == donor
            donor_rows.append(_original(matrix[mask], obs.loc[mask].reset_index(drop=True), ['T'], 'Rest'))
        weights = np.array([float(item.n_cells[item.targets.index('T')]) for item in donor_rows])
        averaged = sum(item.shrunk[item.targets.index('T')] * weight
                       for item, weight in zip(donor_rows, weights)) / weights.sum()
        joint_row = one['shrunk'][one['targets'].index('T')]
        self.assertFalse(np.allclose(averaged, joint_row, rtol=1e-5, atol=1e-5, equal_nan=True))
        without = obs['donor'].to_numpy() != 'D3'
        dropped = _original(matrix[without], obs.loc[without].reset_index(drop=True), ['T'], 'Rest')
        self.assertFalse(np.allclose(dropped.control_mean, original.control_mean, rtol=0, atol=0))

    def test_labels_keep_off_axis_ids_and_do_not_split(self):
        self.assertEqual(cd4_joint.classify_label('ENSG00000198888', {}, {})['kind'], 'perturbation')
        self.assertEqual(cd4_joint.classify_label('OFFAXIS', {}, {})['kind'], 'perturbation')
        self.assertEqual(cd4_joint.classify_label('NTC', {'NTC': 'non-targeting'}, {})['kind'], 'control')
        self.assertEqual(cd4_joint.classify_label('UNASSIGNED', {}, {})['reason'], 'unassigned_or_blank')
        self.assertEqual(cd4_joint.classify_label('control', {}, {})['reason'],
                         'control_token_not_in_verified_source_map')
        split = cd4_joint.classify_label('A+B', {}, {})
        self.assertEqual(split['reason'], 'separator_not_split')
        self.assertNotIn('components', split)
        frame = pd.DataFrame({
            'donor_or_clone': ['D1', 'D1', 'D1', 'D1'],
            'target': ['UNASSIGNED', 'A+B', 'ENSG00000198888', 'NTC'],
            'condition': 'Rest', 'n': [20, 20, 20, 30], 'line_group': 'CD4T',
        })
        kept, decisions, _report = cd4_joint.prepare_bank_frame(frame, ['g0'], 'Rest', {'NTC': 'non-targeting'}, {}, [])
        _matrix, records, info = cd4_joint.compact_kept(np.ones((4, 1)), kept, decisions)
        self.assertEqual(sorted(item['target'] for item in records), ['ENSG00000198888', 'non-targeting'])
        reasons = sorted(item['reason'] for item in info['blocked_rows'])
        self.assertEqual(reasons, ['separator_not_split', 'unassigned_or_blank'])

    def test_hidden_before_statistics_and_mask_policy(self):
        frame = pd.DataFrame({
            'donor_or_clone': ['D1', 'D1'], 'target': ['TP53', 'NTC'], 'condition': 'Rest',
            'n': [20, 30], 'line_group': 'CD4T',
        })
        _kept, decisions, _report = cd4_joint.prepare_bank_frame(
            frame, ['g0'], 'Rest', {'NTC': 'non-targeting'}, {}, ['TP53'])
        self.assertEqual(decisions[0]['reason'], 'global_hidden_before_statistics')
        counts = np.array([[0.0, 1.0], [0.0, 2.0]])
        mask = np.array([[False, True], [False, True]])
        self.assertEqual(cd4_joint.assert_mask_policy(counts, mask), (2, 2))
        mask[0, 0] = False
        counts[0, 0] = 3
        with self.assertRaises(cd4_joint.JointBlocked):
            cd4_joint.assert_mask_policy(counts, mask)

    def test_disk_spill_matches_the_in_memory_call(self):
        matrix, obs = _multi_donor()
        targets = ['T']
        frame = pd.DataFrame({
            'donor_or_clone': obs['donor'], 'target': obs['target'], 'condition': 'Rest',
            'n': obs['n_cells'], 'line_group': 'CD4T',
        })
        kept, decisions, _report = cd4_joint.prepare_bank_frame(
            frame, GENES, 'Rest', {'NTC': 'non-targeting'}, {}, [])
        compact, records, _info = cd4_joint.compact_kept(matrix, kept, decisions)
        attached = cd4_joint.attach_counts(records, compact)
        memory = cd4_joint.effects_from_records(attached, GENES, targets, CALL, 10 ** 9)
        original = _original(matrix, obs, targets, 'Rest')
        with tempfile.TemporaryDirectory() as folder:
            light = cd4_joint.spill_compact(folder, 'D1_Rest', compact, records)
            mapper = cd4_joint.CountMap()
            try:
                spilled = cd4_joint.effects_from_records(light, GENES, targets, CALL, 10 ** 9, count_of=mapper)
            finally:
                mapper.close()
        np.testing.assert_allclose(spilled['shrunk'], memory['shrunk'], rtol=0, atol=0, equal_nan=True)
        np.testing.assert_allclose(spilled['shrunk'], original.shrunk, rtol=1e-6, atol=1e-6, equal_nan=True)
        np.testing.assert_allclose(spilled['raw'], original.raw, rtol=1e-6, atol=1e-6, equal_nan=True)

    def test_line_group_disagreement_blocks(self):
        frame = pd.DataFrame({
            'donor_or_clone': ['D1'], 'target': ['NTC'], 'condition': 'Rest',
            'n': [10], 'line_group': 'K562',
        })
        with self.assertRaises(cd4_joint.JointBlocked):
            cd4_joint.prepare_bank_frame(frame, ['g0'], 'Rest', {}, {}, [])


class MixTests(unittest.TestCase):
    def test_port_matches_original_mix(self):
        left = AxisTable('a', ['T1', 'T2'],
                         np.array([[5.0, 1.0], [5.0, 3.0]], np.float32),
                         np.array([[4.0, 1.0], [4.0, 2.0]], np.float32),
                         np.ones((2, 2), np.float32), np.array([10.0, 10.0]))
        right = AxisTable('b', ['T1', 'T2'],
                          np.array([[1.0, 0.0], [1.0, 9.0]], np.float32),
                          np.array([[8.0, 0.0], [8.0, 7.0]], np.float32),
                          np.ones((2, 2), np.float32), np.array([100000.0, 100000.0]))
        for gamma in (0.0, 1.0):
            ref, ref_w = mix([left, right], ['T1', 'T2'], gamma=gamma, reliability_scale=100.0)
            tables = [mix_model.Table(tab.name, tab.targets, tab.shrunk, tab.raw, tab.se, tab.n_cells)
                      for tab in (left, right)]
            got, got_w = mix_model.mix(tables, ['T1', 'T2'], gamma=gamma, reliability_scale=100.0)
            np.testing.assert_allclose(got, ref, rtol=1e-6, atol=1e-6)
            np.testing.assert_allclose(got_w, ref_w, rtol=1e-6, atol=1e-6)
        raw_ref = [AxisTable(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells) for tab in (left, right)]
        ref_raw, _weight = mix(raw_ref, ['T1', 'T2'], gamma=0.0, reliability_scale=100.0)
        raw_tables = [mix_model.Table(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells)
                      for tab in (left, right)]
        got_raw, _got_w = mix_model.mix(raw_tables, ['T1', 'T2'], gamma=0.0)
        np.testing.assert_allclose(got_raw, ref_raw, rtol=1e-6, atol=1e-6)

    def test_condition_mix_is_gamma0_and_not_an_equal_mean(self):
        small = mix_model.Table('cd4_Rest', ['T'], np.array([[0.0, 0.0]], np.float32),
                                np.array([[1.0, 2.0]], np.float32), np.ones((1, 2), np.float32), np.array([10.0]))
        large = mix_model.Table('cd4_Stim8hr', ['T'], np.array([[10.0, 4.0]], np.float32),
                                np.array([[9.0, 0.0]], np.float32), np.ones((1, 2), np.float32), np.array([100000.0]))
        mixed = mix_model.condition_mix([small, large])
        ref_tables = [AxisTable(tab.name, tab.targets, tab.shrunk, tab.raw, tab.se, tab.n_cells)
                      for tab in (small, large)]
        ref, weight = mix(ref_tables, ['T'], gamma=0.0, reliability_scale=100.0)
        np.testing.assert_allclose(mixed.shrunk, np.where(weight > 0, ref, np.nan), rtol=1e-6, atol=1e-6)
        raw_tabs = [AxisTable(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells) for tab in (small, large)]
        ref_raw, raw_w = mix(raw_tabs, ['T'], gamma=0.0, reliability_scale=100.0)
        np.testing.assert_allclose(mixed.raw, np.where(raw_w > 0, ref_raw, np.nan), rtol=1e-6, atol=1e-6)
        equal = (small.shrunk + large.shrunk) / 2
        self.assertFalse(np.allclose(mixed.shrunk, equal, rtol=1e-4, atol=1e-4))
        gamma1, _w = mix(ref_tables, ['T'], gamma=1.0, reliability_scale=100.0)
        self.assertFalse(np.allclose(np.nan_to_num(mixed.shrunk), gamma1, rtol=1e-4, atol=1e-4))
        self.assertFalse(np.allclose(mixed.shrunk, mixed.raw))

    def test_fragment_keeps_every_bio_table_and_votes_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'vcc-effects-demo-r4' / 'effects' / 'demo'
            (output / 'splits' / 'a').mkdir(parents=True)
            (output / 'splits' / 'b').mkdir()
            (output / 'statistics').mkdir()
            bio_a = np.array([[1.0, 0.0]], np.float32)
            bio_b = np.array([[5.0, 8.0]], np.float32)
            np.savez_compressed(output / 'statistics' / 'abc.npz',
                                **{'0_shrunk': bio_a, '0_raw': bio_a, '0_n_cells': np.array([100.0]),
                                   '1_shrunk': bio_b, '1_raw': bio_b + 1, '1_n_cells': np.array([100.0])})
            effects = {'axis_sha256': 'axis', 'statistics': [{
                'id': 'abc', 'file': 'statistics/abc.npz', 'arrays': ['shrunk', 'raw'],
                'tables': [{'name': 'demo::bio_a', 'targets': ['T'], 'meta': {}},
                           {'name': 'demo::bio_b', 'targets': ['ONLY_B', 'T'], 'meta': {}}]}]}
            # The second table must have two targets to prove index 0 is not the only one read.
            bio_b = np.array([[7.0, 1.0], [5.0, 8.0]], np.float32)
            np.savez_compressed(output / 'statistics' / 'abc.npz',
                                **{'0_shrunk': bio_a, '0_raw': bio_a, '0_n_cells': np.array([100.0]),
                                   '1_shrunk': bio_b, '1_raw': bio_b + 1, '1_n_cells': np.array([50.0, 100.0])})
            effects['statistics'][0]['tables'][1]['targets'] = ['ONLY_B', 'T']
            (output / 'effects.json').write_text(json.dumps(effects), encoding='utf-8')
            (output / 'source_model.json').write_text(json.dumps({'kind': 'source_effect_fragment', 'unit': 'demo'}),
                                                      encoding='utf-8')
            for name, rows, status, stat in (
                    ('a', 10, 'derived', 'small'), ('b', 80, 'derived', 'abc')):
                (output / 'splits' / name / 'receipt.json').write_text(json.dumps({
                    'split': name, 'status': status, 'statistics_id': stat, 'file': 'statistics/abc.npz',
                    'n_rows_kept': rows, 'regime': 'C', 'held_group': 'K562', 'fold': 0,
                }), encoding='utf-8')
            selection = mix_model.select_fragment(output)
            self.assertEqual(selection['n_tables'], 2)
            self.assertIn('ONLY_B', selection['tables'][1].targets)
            self.assertTrue(selection['not_used_fold'])
            collapsed = mix_model.collapse_fragment(selection, 'demo')
            other = mix_model.Table('other', ['T'], np.array([[0.0, 0.0]], np.float32),
                                    np.array([[0.0, 0.0]], np.float32), np.ones((1, 2), np.float32),
                                    np.array([100.0]))
            model = mix_model.final_mix([collapsed, other], gamma=1.0, reliability_scale=100.0, weight=1.0)
            self.assertEqual(model['sources'], ['demo', 'other'])
            both = mix_model.final_mix([
                mix_model.Table('demo_a', ['T'], bio_a, bio_a, None, np.array([100.0])),
                mix_model.Table('demo_b', ['ONLY_B', 'T'], bio_b, bio_b, None, np.array([50.0, 100.0])),
                other,
            ])
            row = model['targets'].index('T')
            self.assertFalse(np.allclose(model['shrunk_weight'][row], both['shrunk_weight'][both['targets'].index('T')]))

    def test_partial_conditions_do_not_become_cd4_mix(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'vcc-effects-cd4-rest-joint-r5' / 'Rest'
            root.mkdir(parents=True)
            np.savez_compressed(root / 'effects.npz', shrunk=np.zeros((1, 2), np.float32),
                                raw=np.zeros((1, 2), np.float32), se=np.ones((1, 2), np.float32),
                                n_cells=np.array([10]), targets=np.array(['T']),
                                control_mean=np.ones(2))
            (root / 'source_model.json').write_text(json.dumps({
                'kind': 'cd4_condition_joint', 'condition': 'Rest', 'transfer_source_id': 'cd4_Rest',
                'axis_sha256': 'axis', 'schedule': 'one_call'}), encoding='utf-8')
            (root / 'status.json').write_text(json.dumps({'status': 'derived'}), encoding='utf-8')
            built = mix_model.build_incremental(Path(folder), [
                {'role': 'cd4_condition', 'slug': 'davideferrante11/vcc-effects-cd4-rest-joint-r5', 'condition': 'Rest'},
                {'role': 'cd4_condition', 'slug': 'davideferrante11/vcc-effects-cd4-stim8hr-joint-r5', 'condition': 'Stim8hr'},
            ])
            self.assertEqual(built['status'], 'blocked')
            self.assertIsNone(built['cd4_mix'])


class LaunchTests(unittest.TestCase):
    def test_module_does_not_push(self):
        self.assertTrue(launch_r5.module_does_not_push())
        text = Path(launch_r5.__file__).read_text(encoding='utf-8')
        self.assertNotIn('import subprocess', text)


if __name__ == '__main__':
    unittest.main()
