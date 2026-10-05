"""Split identity, source votes, and the push-free launcher. Fixtures, not a bank run."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from vcc2026.multisource import AxisTable
from vcc2026.multisource import mix as original_mix

import launch_r6
import mix_model
import pins
import split_rule

AXIS = 'axis-sha'


def _manifest():
    return mix_model.frozen_manifest()


def _split_dir(name):
    return name.replace(':', '_')


def _write_fragment(root, slug, unit, source_id, line, vote, manifest, *, production_id='FULL',
                    block=None, arrays=('shrunk', 'raw', 'se'), scale=1.0, status='derived'):
    output = Path(root) / slug
    (output / 'splits').mkdir(parents=True)
    targets = ['t0', 't1']
    width = 2
    if 'se' in arrays:
        saved = {'0_shrunk': np.full((2, width), scale, np.float32),
                 '0_raw': np.full((2, width), scale * 2, np.float32),
                 '0_se': np.ones((2, width), np.float32),
                 '0_n_cells': np.array([10, 20])}
        pack = output / 'statistics' / (production_id + '.npz')
        pack.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(pack, **saved)
    tables = [{'name': unit + '_bio', 'targets': targets, 'meta': {}}]
    (output / 'effects.json').write_text(json.dumps({
        'axis_sha256': AXIS, 'blocked_tokens': {},
        'statistics': [{'id': production_id, 'file': 'statistics/' + production_id + '.npz',
                        'arrays': list(arrays), 'tables': tables}],
    }), encoding='utf-8')
    (output / 'source_model.json').write_text(json.dumps({
        'kind': 'source_effect_fragment', 'unit': unit, 'transfer_source_id': source_id,
        'line_group': line, 'training_vote': vote, 'axis_sha256': AXIS,
    }), encoding='utf-8')
    (output / 'status.json').write_text(json.dumps({
        'status': status, 'blocked_output_splits': [block] if block else [],
    }), encoding='utf-8')
    for spec in manifest:
        name = spec['name']
        if name == block:
            receipt = {'split': name, 'regime': spec['regime'], 'held_group': spec['held_group'],
                       'fold': spec['fold'], 'status': 'blocked_output', 'n_rows_kept': 999}
        elif spec['regime'] == 'C' and spec['fold'] is None and spec['held_group'] != line:
            receipt = {'split': name, 'regime': 'C', 'held_group': spec['held_group'], 'fold': None,
                       'status': 'derived', 'statistics_id': production_id,
                       'file': 'statistics/' + production_id + '.npz', 'arrays': list(arrays), 'n_rows_kept': 50}
        elif spec['held_group'] == line:
            receipt = {'split': name, 'regime': spec['regime'], 'held_group': line, 'fold': spec['fold'],
                       'status': 'derived', 'statistics_id': 'HELD', 'file': 'statistics/HELD.npz',
                       'arrays': list(arrays), 'n_rows_kept': 10}
        else:
            receipt = {'split': name, 'regime': spec['regime'], 'held_group': spec['held_group'],
                       'fold': spec['fold'], 'status': 'derived', 'statistics_id': 'JID',
                       'file': 'statistics/JID.npz', 'arrays': list(arrays), 'n_rows_kept': 999}
        folder = output / 'splits' / _split_dir(name)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
    return output


def _write_joint(root, condition, slug):
    output = Path(root) / slug
    output.mkdir(parents=True)
    (output / 'source_model.json').write_text(json.dumps({
        'kind': 'cd4_condition_joint', 'condition': condition, 'transfer_source_id': 'cd4_' + condition,
        'axis_sha256': AXIS, 'global_hidden_targets': [], 'schedule': 'all_donors_one_condition',
    }), encoding='utf-8')
    (output / 'status.json').write_text(json.dumps({'status': 'derived'}), encoding='utf-8')
    np.savez_compressed(output / 'effects.npz', targets=np.array(['t0', 't1']),
                        shrunk=np.ones((2, 2), np.float32), raw=np.full((2, 2), 2, np.float32),
                        se=np.ones((2, 2), np.float32), n_cells=np.array([12, 12]))
    return output


def _expected_fragment(slug, unit, source_id, line, vote, admission='required'):
    return {'role': 'fragment', 'admission': admission, 'slug': slug, 'condition': None,
            'transfer_source_id': source_id, 'unit': unit, 'line_group': line, 'training_vote': vote}


class IdentityTests(unittest.TestCase):
    def test_full_production_identity_beats_a_larger_j_row_count(self):
        manifest = [
            {'name': 'C:HCT116', 'regime': 'C', 'held_group': 'HCT116', 'fold': None},
            {'name': 'C:HepG2', 'regime': 'C', 'held_group': 'HepG2', 'fold': None},
            {'name': 'J:HCT116:f0', 'regime': 'J', 'held_group': 'HCT116', 'fold': 0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = _write_fragment(tmp, 'hepg2', 'hepg2_nadig', 'hepg2_nadig', 'HepG2', True, manifest)
            self.assertFalse((output / 'statistics' / 'JID.npz').exists())
            selected = mix_model.select_production(output, 'HepG2', manifest)
        self.assertEqual(selected['statistics_id'], 'FULL')
        self.assertEqual(selected['selection_rule'], 'split_identity')
        self.assertEqual(selected['max_n_rows_kept_ignored'], 999)
        self.assertLess(selected['n_rows_kept'], selected['max_n_rows_kept_ignored'])
        held = [item for item in selected['validation'] if item['name'] == 'C:HepG2'][0]
        self.assertFalse(held['vote'])
        self.assertEqual(held['contribution'], 'absent')

    def test_disagreeing_production_ids_block_even_when_row_counts_match(self):
        manifest = [
            {'name': 'C:HCT116', 'regime': 'C', 'held_group': 'HCT116', 'fold': None},
            {'name': 'C:K562', 'regime': 'C', 'held_group': 'K562', 'fold': None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = _write_fragment(tmp, 'hepg2', 'hepg2_nadig', 'hepg2_nadig', 'HepG2', True, manifest)
            other = json.loads((output / 'splits' / 'C_K562' / 'receipt.json').read_text(encoding='utf-8'))
            other['statistics_id'] = 'OTHER'
            other['file'] = 'statistics/OTHER.npz'
            other['n_rows_kept'] = 50
            (output / 'splits' / 'C_K562' / 'receipt.json').write_text(json.dumps(other), encoding='utf-8')
            with self.assertRaises(mix_model.MixBlocked) as caught:
                mix_model.select_production(output, 'HepG2', manifest)
        self.assertIn('identity conflict', str(caught.exception))

    def test_manifest_is_bound_before_any_mount_is_read(self):
        with self.assertRaises(mix_model.MixBlocked) as caught:
            mix_model.build_incremental(Path('missing-root'), [], [{'name': 'no'}], axis_sha256=AXIS)
        self.assertIn('frozen', str(caught.exception))

    def test_cd4_joint_does_not_vote_as_a_held_or_j_effect(self):
        held = mix_model.joint_validation_vote({'name': 'C:CD4T', 'regime': 'C', 'held_group': 'CD4T', 'fold': None})
        jay = mix_model.joint_validation_vote({'name': 'J:HCT116:f0', 'regime': 'J', 'held_group': 'HCT116', 'fold': 0})
        other = mix_model.joint_validation_vote({'name': 'C:HCT116', 'regime': 'C', 'held_group': 'HCT116', 'fold': None})
        self.assertFalse(held['vote'])
        self.assertFalse(jay['vote'])
        self.assertEqual(held['reason'], 'production_joint_not_reused_as_validation')
        self.assertEqual(held['contribution'], 'absent')
        self.assertTrue(other['vote'])


class MixTests(unittest.TestCase):
    def _bank(self, root, manifest):
        _write_fragment(root, 'h1-train', 'h1_train', 'h1', 'H1', False, manifest, scale=1.0)
        _write_fragment(root, 'h1-val', 'h1_val', 'h1', 'H1', False, manifest, production_id='H1B', scale=3.0)
        _write_fragment(root, 'hepg2', 'hepg2_nadig', 'hepg2_nadig', 'HepG2', True, manifest)
        _write_fragment(root, 'kolf', 'kolf_chromatin', 'kolf_chromatin', 'iPSC', True, manifest)
        _write_fragment(root, 'hek', 'orion_hek293t', 'orion_hek293t', 'HEK293T', True, manifest,
                        status='partial_output_budget', block='J:A549:f4')
        _write_fragment(root, 'inexact', 'inexact_source', 'inexact_source', 'Hs27', True, manifest,
                        arrays=('shrunk',), status='partial_output_budget')
        for condition, slug in (
            ('Rest', 'vcc-effects-cd4-rest-joint-r5'),
            ('Stim8hr', 'vcc-effects-cd4-stim8hr-joint-r5'),
            ('Stim48hr', 'vcc-effects-cd4-stim48hr-joint-r5'),
        ):
            _write_joint(root, condition, slug)

    def _expected(self):
        rows = [
            _expected_fragment('h1-train', 'h1_train', 'h1', 'H1', False),
            _expected_fragment('h1-val', 'h1_val', 'h1', 'H1', False),
            _expected_fragment('hepg2', 'hepg2_nadig', 'hepg2_nadig', 'HepG2', True),
            _expected_fragment('kolf', 'kolf_chromatin', 'kolf_chromatin', 'iPSC', True),
            _expected_fragment('hek', 'orion_hek293t', 'orion_hek293t', 'HEK293T', True, 'if_exact'),
            _expected_fragment('inexact', 'inexact_source', 'inexact_source', 'Hs27', True, 'if_exact'),
            _expected_fragment('hct-absent', 'orion_hct116', 'orion_hct116', 'HCT116', True, 'if_exact'),
        ]
        for condition, slug in (
            ('Rest', 'vcc-effects-cd4-rest-joint-r5'),
            ('Stim8hr', 'vcc-effects-cd4-stim8hr-joint-r5'),
            ('Stim48hr', 'vcc-effects-cd4-stim48hr-joint-r5'),
        ):
            rows.append({'role': 'cd4_condition', 'admission': 'required', 'slug': slug, 'condition': condition,
                         'transfer_source_id': 'cd4_' + condition, 'unit': 'cd4_' + condition, 'line_group': 'CD4T'})
        return rows

    def test_gate_keeps_h1_hepg2_kolf_and_exact_hek(self):
        manifest = _manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._bank(root, manifest)
            built = mix_model.build_incremental(root, self._expected(), manifest, axis_sha256=AXIS)
            self.assertEqual(built['status'], 'mixed_accepted_gate')
            self.assertEqual(built['model']['sources'],
                             ['cd4_mix', 'h1', 'hepg2_nadig', 'kolf_chromatin', 'orion_hek293t'])
            self.assertNotIn('h1_train', built['model']['sources'])
            self.assertNotIn('inexact_source', built['model']['sources'])
            self.assertTrue(any(item['slug'] == 'hct-absent' for item in built['pending']))
            self.assertTrue(any('se or raw absent' in item['error'] for item in built['refused']))
            h1 = [table for table in built['sources'] if table.name == 'h1'][0]
            np.testing.assert_allclose(h1.shrunk, np.full((2, 2), 2, np.float32))
            self.assertTrue(h1.meta['aggregated_after_shrink'])
            self.assertNotIn('from', h1.meta)
            hek = [item for item in built['fragments'] if item['unit'] == 'orion_hek293t'][0]
            self.assertEqual(hek['statistics_id'], 'FULL')
            missing = [item for item in hek['validation'] if item['name'] == 'J:A549:f4'][0]
            self.assertFalse(missing['vote'])
            self.assertEqual(missing['contribution'], 'absent')
            held = [item for item in hek['validation'] if item['name'] == 'C:HEK293T'][0]
            self.assertEqual(held['reason'], 'excluded_when_held')
            document = mix_model._validation_document(manifest, built)
            cd4_held = [item for item in document['cd4'] if item['name'] == 'C:CD4T'][0]
            self.assertFalse(cd4_held['vote'])
            out = root / 'model'
            mix_model.write_release(out, built, {'sources': built['model']['sources']},
                                    output_budget_bytes=pins.OUTPUT_BUDGET_BYTES,
                                    catalogue_gaps=[{'name': 'k562_gwps'}])
            saved = json.loads((out / 'source_model.json').read_text(encoding='utf-8'))
            self.assertFalse(saved['fit_ready'])
            self.assertFalse(saved['fit_admitted'])
            self.assertFalse(saved['all_compatible_admitted'])
            self.assertTrue(saved['usable_export'])
            self.assertFalse(saved['claims_complete_training'])
            with np.load(out / 'effects.npz') as effects:
                self.assertNotIn('lfc', effects.files)
            with np.load(out / 'cache' / 'h1.npz') as cache:
                self.assertEqual(set(cache.files), {'targets', 'shrunk', 'raw', 'se', 'n_cells', 'meta'})
            self.assertTrue((out / 'cache' / 'cd4_Rest.npz').is_file())

    def test_two_conditions_do_not_become_cd4_mix(self):
        manifest = _manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._bank(root, manifest)
            expected = [item for item in self._expected() if item['slug'] != 'vcc-effects-cd4-stim48hr-joint-r5']
            built = mix_model.build_incremental(root, expected, manifest, axis_sha256=AXIS)
            self.assertEqual(built['status'], 'blocked_missing_mount')
            self.assertIsNone(built['model'])
            out = root / 'blocked'
            mix_model.write_release(out, built, {}, output_budget_bytes=pins.OUTPUT_BUDGET_BYTES, catalogue_gaps=[])
            self.assertFalse((out / 'effects.npz').exists())
            status = json.loads((out / 'status.json').read_text(encoding='utf-8'))
            self.assertFalse(status['fit_ready'])
            self.assertFalse(status['usable_export'])

    def test_gamma_matches_the_original_mix(self):
        values = [
            ('one', np.array([[1.0, np.nan], [0.5, 0.25]], np.float32), np.array([10, 30])),
            ('two', np.array([[3.0, 4.0], [np.nan, 1.0]], np.float32), np.array([20, 40])),
        ]
        ours = [mix_model.Table(name, ['a', 'b'], rows, rows, np.ones_like(rows), cells) for name, rows, cells in values]
        theirs = [AxisTable(name, ['a', 'b'], rows, rows, np.ones_like(rows), cells) for name, rows, cells in values]
        for gamma in (0.0, 1.0):
            left, left_w = mix_model.mix(ours, ['a', 'b', 'c'], gamma=gamma, reliability_scale=100.0)
            right, right_w = original_mix(theirs, ['a', 'b', 'c'], gamma=gamma, reliability_scale=100.0)
            np.testing.assert_allclose(left, right)
            np.testing.assert_allclose(left_w, right_w)


class LaunchTests(unittest.TestCase):
    def test_launcher_does_not_push_and_keeps_the_rejected_sources(self):
        self.assertTrue(launch_r6.module_does_not_push())
        self.assertEqual(len(split_rule.frozen_splits()), 72)
        fragments = launch_r6.load_fragments()
        units = {item['unit'] for item in fragments}
        self.assertTrue({'hepg2_nadig', 'h1_train', 'h1_val', 'kolf_chromatin', 'orion_hek293t'} <= units)
        self.assertEqual(sum(item['transfer_source_id'] == 'h1' for item in fragments), 2)
        job = launch_r6.build_job(fragments, {'dataset': 'davideferrante11/vcc-ingest-code-cd4-r1',
                                              'sha256': pins.AXIS_SHA256, 'genes': pins.AXIS_GENES, 'bytes': 1},
                                  {'applied_in_mixer': False}, {'expected_sha256': 'abc'})
        self.assertEqual(job['params']['split_manifest'], mix_model.frozen_manifest())
        self.assertNotIn(pins.OPEN_PARENT_KERNEL, json.dumps(job['params']))
        joined = '\n'.join(job['kernel_sources'])
        self.assertIn('hepg2-nadig', joined)
        self.assertIn('h1-train', joined)
        self.assertIn('h1-val', joined)
        self.assertIn('kolf-chromatin', joined)
        self.assertIn('orion-hek293t', joined)
        self.assertIn('hct116', joined)
        self.assertNotIn('kolf-metabolic', joined)
        self.assertNotIn('kolf-strong', joined)
        self.assertNotIn('pan-genome', joined)
        self.assertNotIn('gwps', joined)
        admissions = {item['unit']: item['admission'] for item in fragments}
        self.assertEqual(admissions['orion_hct116'], 'required')
        self.assertEqual(admissions['kolf_metabolic'], 'if_exact')
        self.assertEqual(admissions['orion_hek293t'], 'if_exact')
        expected_slugs = [item['slug'] for item in job['params']['expected']]
        self.assertIn(launch_r6.PAN_REPAIR_SLUG, expected_slugs)
        self.assertNotIn(launch_r6.PAN_BLOCKED_SLUG, expected_slugs)
        self.assertIn(launch_r6.PAN_REPAIR_SLUG, job['deferred_kernels'])
        self.assertEqual(sum(item['role'] == 'cd4_condition' for item in job['params']['expected']), 3)
        self.assertIn('davideferrante11/vcc-effects-cd4-stim8hr-joint-r5-retry1', job['kernel_sources'])
        self.assertNotIn('davideferrante11/vcc-effects-cd4-stim8hr-joint-r5', job['kernel_sources'])
        bad = dict(job)
        bad['kernel_sources'] = [pins.OPEN_PARENT_KERNEL]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                launch_r6.write_packages([bad], tmp)


if __name__ == '__main__':
    unittest.main()
