"""Technical identity checks for the r8 generation contract. Not a score bench."""
from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

import numpy as np

import adapters_r8
import generate_contract as contract
import launch_r8


HERE = Path(__file__).resolve().parent


class IdentityTest(unittest.TestCase):
    def test_recipe_weights_every_voted_source_once(self):
        recipe = contract.recipe_from_voted([
            'h1', 'cd4_mix', 'k562_essential', 'kolf_pan_genome', 'orion_hek293t',
        ])
        self.assertEqual(recipe['effect'], 'shrunk')
        self.assertEqual(recipe['gamma'], 1.0)
        self.assertEqual(recipe['reliability_scale'], 100)
        self.assertTrue(recipe['allow_missing_targets'])
        self.assertFalse(recipe['allow_foreign_cache'])
        self.assertEqual(recipe['cis']['pairs'], contract.CIS_PAIRS)
        self.assertEqual(recipe['cis']['max_distance_bp'], 5000)
        self.assertEqual(recipe['cis']['scale'], 2.0)
        for ctx in ('A', 'B', 'C'):
            weights = recipe['contexts'][ctx]['weights']
            self.assertEqual(recipe['contexts'][ctx]['amplitude'], 1.576)
            self.assertEqual(set(weights), {'h1', 'cd4_mix', 'k562_essential', 'kolf_pan_genome', 'orion_hek293t'})
            self.assertTrue(all(value == 1.0 for value in weights.values()))
            self.assertNotIn('k562', weights)

    def test_refuses_gwps_name_double_cd4_and_split_h1(self):
        with self.assertRaises(ValueError):
            contract.recipe_from_voted(['k562', 'cd4_mix'])
        with self.assertRaises(ValueError):
            contract.recipe_from_voted(['cd4_mix', 'cd4_Rest'])
        with self.assertRaises(ValueError):
            contract.recipe_from_voted(['h1_train', 'h1_val'])
        recipe = contract.recipe_from_voted(['k562_essential'])
        self.assertIn('k562_essential', recipe['contexts']['A']['weights'])

    def test_mount_accepts_only_the_retry_directory(self):
        retry = Path('/kaggle/input') / contract.MOUNT_DIR / 'model' / 'source_model.json'
        failed = Path('/kaggle/input') / contract.REFUSE_DIR / 'model' / 'source_model.json'
        self.assertTrue(contract.mix_dir_allowed(retry))
        self.assertFalse(contract.mix_dir_allowed(failed))

    def test_source_model_gate(self):
        accepted = contract.accept_source_model({
            'status': 'mixed_accepted_gate',
            'sources': ['cd4_mix', 'h1', 'k562_essential'],
            'amplitude_applied': False,
            'cis_applied': False,
            'effects_scale_applied': False,
            'k562_essential_replaces_k562': False,
            'training_ready': False,
            'fit_ready': False,
            'loss': None,
        })
        self.assertNotIn('k562', accepted['contexts']['B']['weights'])
        with self.assertRaises(ValueError):
            contract.accept_source_model({
                'status': 'mixed_accepted_gate', 'sources': ['h1'],
                'amplitude_applied': True, 'training_ready': False, 'fit_ready': False, 'loss': None,
            })
        with self.assertRaises(ValueError):
            contract.accept_source_model({
                'status': 'mixed_accepted_gate', 'sources': ['h1'],
                'training_ready': True, 'fit_ready': False, 'loss': None,
            })

    def test_table_keys_and_cd4_se(self):
        shrunk = np.array([[1.0, np.nan]], dtype=np.float32)
        raw = shrunk.copy()
        se = np.array([[0.2, np.nan]], dtype=np.float32)
        keys = contract.TABLE_KEYS
        contract.require_table_arrays('hepg2_nadig', keys, shrunk, raw, se, {})
        with self.assertRaises(ValueError):
            contract.require_table_arrays('hepg2_nadig', ('targets', 'shrunk', 'raw'), shrunk, raw, se, {})
        with self.assertRaises(ValueError):
            contract.require_table_arrays('hepg2_nadig', keys, shrunk, raw, np.array([[np.nan, np.nan]]), {})
        contract.require_table_arrays(
            'cd4_mix', keys, shrunk, raw, np.full_like(shrunk, np.nan),
            {'from': ['cd4_Stim48hr', 'cd4_Rest', 'cd4_Stim8hr']},
        )

    def test_kernel_metadata_and_guard(self):
        metadata = contract.kernel_metadata()
        self.assertEqual(metadata['kernel_sources'], [contract.MOUNT_SLUG])
        self.assertEqual(metadata['dataset_sources'], [contract.AXIS_DATASET])
        self.assertFalse(metadata['enable_gpu'])
        self.assertFalse(metadata['enable_internet'])
        self.assertTrue(metadata['is_private'])
        params = {'mount_slug': contract.MOUNT_SLUG, 'emission': contract.emission()}
        launch_r8.guard_job(metadata, params)
        bad = dict(metadata)
        bad['kernel_sources'] = list(metadata['kernel_sources']) + [launch_r8.REFUSED_KERNEL_SOURCES[0]]
        with self.assertRaises(RuntimeError):
            launch_r8.guard_job(bad, params)

    def test_modules_do_not_push(self):
        for name in ('launch_r8.py', 'generate_contract.py', 'driver.py', 'adapters_r8.py', 'test_r8_identity.py'):
            self.assertTrue(launch_r8.module_does_not_push(HERE / name), name)
            tree = ast.parse((HERE / name).read_text(encoding='utf-8'))
            self.assertFalse(any(isinstance(node, ast.Import) for node in ast.walk(tree) if False))

    def test_reading_rule_has_no_improvement_band(self):
        rule = contract.reading_rule()
        self.assertEqual(rule['reference_t28_official_score'], 0.14484520500645978)
        self.assertTrue(rule['reference_is_not_a_target_or_a_promise'])
        self.assertTrue(rule['no_improvement_band'])
        self.assertIsNone(rule['local_score'])
        self.assertIsNone(rule['loss'])
        blob = json.dumps(rule)
        self.assertNotIn('0.135', blob)
        self.assertNotIn('0.18', blob)

    def test_missing_adapter_is_not_a_scientific_exclusion(self):
        for name in ('hipsci', 'tian2021', 'tian2019', 'scp', 'ko', 'a549', 'norman', 'gse249595'):
            described = adapters_r8.describe(name)
            self.assertFalse(described['admitted'])
            self.assertFalse(described['scientific_exclusion'])
            self.assertTrue(described['technical_gap'])
            with self.assertRaises(adapters_r8.AdapterGap):
                adapters_r8.load(name)


if __name__ == '__main__':
    unittest.main()
