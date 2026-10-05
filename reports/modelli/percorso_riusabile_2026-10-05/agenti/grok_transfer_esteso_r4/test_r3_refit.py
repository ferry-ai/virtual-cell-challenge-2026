"""Fixtures for the r4 derivation. They are not a Kaggle runtime job."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))

from cloud_job import code_hashes, derive_unit, sha256_file, validate_pack  # noqa: E402
from estimator_core import _one_target  # noqa: E402
from launch_packages import (build_jobs, catalogue_rows, dispatch_document,  # noqa: E402
                             module_does_not_push, split_spec)
from linear_transfer import FitBlocked, preparation_allowed  # noqa: E402
from pins import AXIS_FILE, AXIS_SHA256, OPEN_PARENT_KERNEL, REPO, STORAGE_SHA256  # noqa: E402
from release_fit import save_extended_release  # noqa: E402
from split_rule import LINE_GROUPS, frozen_splits, target_fold  # noqa: E402
from vcc2026.multisource import AxisTable, effects_from_pseudobulk as original_effects  # noqa: E402


def _names():
    found = {}
    for index in range(200):
        name = f'G{index}'
        found.setdefault(target_fold(name), name)
        if len(found) == 2:
            break
    folds = sorted(found)
    return found[folds[0]], found[folds[1]], folds[0]


def _write_axis(root, names):
    folder = Path(root) / 'axis-code'
    folder.mkdir(parents=True)
    path = folder / 'gene_names.csv'
    pd.DataFrame({'gene_name': names}).to_csv(path, index=False)
    return {'dataset': 'owner/axis-code', 'relative_path': 'axis-code', 'sha256': sha256_file(path),
            'genes': len(names), 'bytes': path.stat().st_size}


def _bank(root, rows, counts, mask):
    folder = Path(root) / 'bank' / 'unit'
    folder.mkdir(parents=True)
    rows.to_csv(folder / 'rows.csv', index=False)
    np.savez_compressed(folder / 'count_sum.npz', value=counts)
    np.savez_compressed(folder / 'mask.npz', value=mask)
    unit = {'unit': 'unit', 'relative_path': 'bank/unit', 'transfer_source_id': 'cd4_mix',
            'line_group': 'CD4T', 'modality': 'CRISPRi', 'owner': 'davideferrante11',
            'kernel': 'davideferrante11/vcc-bank-cd4-1-3-rest-r2', 'version': 'versions/1',
            'component_policy': {'name': 'bound_axis_membership'},
            'control_labels': {'NTC': 'non-targeting'}}
    for filename, key in (('count_sum.npz', 'count_sum'), ('rows.csv', 'rows'), ('mask.npz', 'mask')):
        path = folder / filename
        unit[key + '_sha256'] = sha256_file(path)
        unit[key + '_bytes'] = path.stat().st_size
    return unit


def _job(axis, budget=10_000_000, hidden=()):
    return {'kind': 'technical_preparation', 'claims_complete_training': False, 'matrix': 'count_sum',
            'ram_budget_bytes': 50_000_000, 'output_budget_bytes': budget, 'global_hidden_targets': list(hidden),
            'splits': split_spec(), 'code_sha256': code_hashes(), 'axis': axis}


class SplitsAndPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gene_a, cls.gene_b, cls.fold_a = _names()

    def _rows(self):
        def one(target):
            return {'study': 'marson', 'context': 'D1', 'donor_or_clone': 'D1', 'condition': 'Rest',
                    'modality': 'CRISPRi', 'chemistry': '10x Flex', 'target': target, 'n': 20,
                    'line_group': 'CD4T'}
        return pd.DataFrame([one('NTC'), one(self.gene_a), one(self.gene_b), one('UNASSIGNED'),
                             one('NOTGENE'), one('A+B'), one('control')])

    def test_registry_groups_and_split_count(self):
        path = REPO / 'reports/modelli/risposta_contesto_2026-10-02/registry.py'
        spec = importlib.util.spec_from_file_location('registry_groups', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(tuple(sorted({row['group'] for row in module.TABLES})), LINE_GROUPS)
        self.assertEqual(len(frozen_splits()), 72)

    def test_exclusions_bind_the_axis_and_do_not_slice_one_pack(self):
        names = ['gB', self.gene_a, self.gene_b, 'KEEP']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            axis = _write_axis(root, names)
            rows = self._rows()
            counts = np.array([[50.0, 5.0, 5.0, 5.0],
                               [50.0, 40.0, 5.0, 5.0],
                               [50.0, 5.0, 40.0, 5.0],
                               [50.0, 5.0, 5.0, 5.0],
                               [50.0, 5.0, 5.0, 5.0],
                               [50.0, 5.0, 5.0, 5.0],
                               [50.0, 5.0, 5.0, 5.0]], dtype=np.float64)
            mask = np.ones(counts.shape, dtype=bool)
            unit = _bank(root, rows, counts, mask)
            out = root / 'out'
            status = derive_unit(root, out, unit, _job(axis))
            self.assertEqual(status['status'], 'derived', status.get('error'))
            self.assertFalse(status['claims_complete_training'])
            effects = json.loads((out / 'effects.json').read_text(encoding='utf-8'))
            self.assertEqual(effects['axis_sha256'], axis['sha256'])
            self.assertEqual(effects['blocked_tokens']['UNASSIGNED'], 'unassigned_or_blank_is_not_a_gene')
            self.assertEqual(effects['blocked_tokens']['A+B'], 'compound_without_source_component_map')
            self.assertEqual(effects['blocked_tokens']['NOTGENE'], 'opaque_token_not_on_bound_axis')
            self.assertEqual(effects['blocked_tokens']['control'], 'control_label_not_in_source_map')
            held = json.loads((out / 'splits' / 'C_CD4T' / 'receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(held['status'], 'excluded_before_statistics')
            self.assertEqual(held['n_rows_kept'], 0)
            other = json.loads((out / 'splits' / 'C_K562' / 'receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(sorted(other['targets']), sorted([self.gene_a, self.gene_b]))
            hidden = json.loads((out / 'splits' / f'J_K562_f{self.fold_a}' / 'receipt.json').read_text(encoding='utf-8'))
            self.assertNotIn(self.gene_a, hidden['targets'])
            self.assertIn(self.gene_b, hidden['targets'])
            self.assertNotEqual(other['statistics_id'], hidden['statistics_id'])
            self.assertIn('hidden_component', hidden['dropped_reasons'])
            self.assertTrue(hidden['estimated_under_split'].startswith('J:'))
            packs = list((out / 'statistics').glob('*.npz'))
            self.assertGreater(len(packs), 1)
            self.assertLess(len(packs), 72)
            self.assertEqual(len(list((out / 'splits').glob('*/receipt.json'))), 72)
            self.assertEqual(validate_pack(out)['status'], 'derived')

    def test_global_hidden_is_applied_before_statistics(self):
        names = ['gB', self.gene_a, self.gene_b, 'KEEP']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            axis = _write_axis(root, names)
            unit = _bank(root, self._rows(), np.ones((7, 4)), np.ones((7, 4), dtype=bool))
            out = root / 'out'
            status = derive_unit(root, out, unit, _job(axis, hidden=[self.gene_b]))
            self.assertEqual(status['status'], 'derived', status.get('error'))
            other = json.loads((out / 'splits' / 'C_K562' / 'receipt.json').read_text(encoding='utf-8'))
            self.assertNotIn(self.gene_b, other['targets'])
            self.assertIn('global_hidden_component', other['dropped_reasons'])

    def test_positional_axis_and_output_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            axis = _write_axis(root, ['0', '1', '2', '3'])
            unit = _bank(root, self._rows(), np.ones((7, 4)), np.ones((7, 4), dtype=bool))
            status = derive_unit(root, root / 'bad', unit, _job(axis))
            self.assertEqual(status['status'], 'blocked')
            self.assertIn('positional', status['error'])
        names = ['gB', self.gene_a, self.gene_b, 'KEEP']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            axis = _write_axis(root, names)
            unit = _bank(root, self._rows(), np.ones((7, 4)), np.ones((7, 4), dtype=bool))
            status = derive_unit(root, root / 'tight', unit, _job(axis, budget=1))
            self.assertEqual(status['status'], 'partial_output_budget', status.get('error'))
            self.assertFalse(status['claims_complete_training'])
            self.assertEqual(list((root / 'tight' / 'statistics').glob('*.npz')), [])


class Packages(unittest.TestCase):
    def test_builder_does_not_push_and_pins_r10(self):
        self.assertTrue(module_does_not_push())
        observed = json.loads((HERE / 'observed_units.json').read_text(encoding='utf-8'))
        self.assertEqual(observed['storage_manifest_sha256'], STORAGE_SHA256)
        self.assertEqual(observed['axis_sha256'], AXIS_SHA256)
        jobs, gaps = build_jobs(observed, AXIS_FILE.stat().st_size)
        self.assertEqual(len(jobs), 24)
        self.assertTrue(all(len(job['params']['units']) == 1 for job in jobs))
        self.assertTrue(all(job['slug'].endswith('-r4') for job in jobs))
        self.assertTrue(all(job['params']['recipe']['hybrid'] is False for job in jobs))
        self.assertTrue(all(job['params']['recipe']['source_weight'] == 1.0 for job in jobs))
        self.assertTrue(all(job['params']['splits']['line_groups'] == list(LINE_GROUPS) for job in jobs))
        self.assertTrue(all(unit['component_policy']['name'] == 'bound_axis_membership'
                            for job in jobs for unit in job['params']['units']))
        self.assertTrue(all(job['params']['axis']['sha256'] == AXIS_SHA256 for job in jobs))
        self.assertFalse(any(OPEN_PARENT_KERNEL in json.dumps(job) or 'gwps' in job['kernel'] for job in jobs))
        cd4 = [job for job in jobs if job['params']['units'][0]['transfer_source_id'] == 'cd4_mix']
        self.assertEqual(len(cd4), 12)
        self.assertTrue(all(job['params']['units'][0]['training_vote'] is False for job in cd4))
        essential = next(job for job in jobs if job['params']['units'][0]['unit'] == 'k562_essential')
        self.assertEqual(essential['params']['units'][0]['transfer_source_id'], 'k562_essential')
        self.assertFalse(essential['params']['units'][0]['replaces_k562'])
        self.assertFalse(essential['enable_gpu'])
        waved = {job['params']['units'][0]['unit'] for job in jobs}
        self.assertTrue(all(gap['unit'] not in waved for gap in gaps))
        self.assertEqual(len(gaps), 19)
        reasons = {gap['unit']: gap['reason_code'] for gap in gaps}
        self.assertEqual(reasons['norman2019'], 'compound_without_map')
        self.assertEqual(reasons['tian2019_ipsc'], 'qc_open')
        self.assertEqual(reasons['hipsci_targeted_19'], 'unresolved_controls')
        self.assertEqual(reasons['hipsci_gw_fitness'], 'scarce_controls')
        self.assertEqual(reasons['a549_ko'], 'other_modality')
        self.assertEqual(reasons['datlinger2017'], 'modality_not_partitioned')
        self.assertEqual(reasons['tian2021_crispri'], 'control_label_unmapped')
        self.assertNotIn('kolf_pan_genome', reasons)
        hep = next(job for job in jobs if job['params']['units'][0]['unit'] == 'hepg2_nadig')
        self.assertEqual(hep['params']['units'][0]['role'], 'validation')
        self.assertTrue(hep['params']['units'][0]['exclude_only_when_held'])
        kolf = next(job for job in jobs if job['params']['units'][0]['unit'] == 'kolf_pan_genome')
        self.assertTrue(kolf['params']['units'][0]['distinct_study_pending_anchor'])
        h1 = [job for job in jobs if job['params']['units'][0]['transfer_source_id'] == 'h1']
        self.assertEqual(len(h1), 2)
        self.assertTrue(all(job['params']['units'][0]['training_vote'] is False for job in h1))
        written = [{'slug': job['slug'], 'dir': 'stage/' + job['slug']} for job in jobs]
        document = dispatch_document(jobs, gaps, written)
        self.assertFalse(document['worker_pushed'])
        self.assertFalse(document['phase2']['push_now'])
        self.assertIn('grok_transfer_esteso_r4', document['preflight_command'])
        self.assertNotIn('kernels push', document['preflight_command'])
        self.assertEqual(document['recommended_order'][0], 'vcc-effects-orion-hct116-r4')
        self.assertTrue(all(item['push_now'] for item in document['packages']))
        rows = catalogue_rows()
        self.assertGreaterEqual(len(rows), 100)
        ids = {row['record_id'] for row in rows}
        self.assertIn('ingested/jurkat_gse249595', ids)
        self.assertIn('remote/scp_NormanWeissman2019_filtered', ids)
        self.assertTrue(all(row['role'] and row['evidence'] for row in rows))
        bad = json.loads(json.dumps(jobs[0]['params']))
        bad['units'][0]['kernel'] = OPEN_PARENT_KERNEL
        with self.assertRaises(FitBlocked):
            preparation_allowed(bad)


class OriginalControlPool(unittest.TestCase):
    def test_control_only_donor_stays_in_the_original_pool(self):
        genes = np.array(['glow', 'gmid'])
        counts = np.array([[8.0, 80.0], [1.0, 1000.0], [0.0, 5_000_000.0]], dtype=np.float64)
        frame = pd.DataFrame([
            {'donor_or_clone': 'A', 'target': 'T', 'n': 20},
            {'donor_or_clone': 'A', 'target': 'NTC', 'n': 40},
            {'donor_or_clone': 'B', 'target': 'NTC', 'n': 40},
        ])
        scattered, cells, used = _one_target(counts, np.ones_like(counts, dtype=bool), frame, genes, 'T', 2)
        obs = pd.DataFrame([
            {'target': 'T', 'donor': 'A', 'condition': 'group', 'n_cells': 20.0},
            {'target': 'non-targeting', 'donor': 'A', 'condition': 'group', 'n_cells': 40.0},
            {'target': 'non-targeting', 'donor': 'B', 'condition': 'group', 'n_cells': 40.0},
        ])
        call = dict(phi=0.2, min_control_frac=1e-6, min_cells=10.0, pseudo=0.5,
                    pseudo_scale='constant', min_expected=1.0)
        full = original_effects(counts, obs, genes, targets=['T'], condition='group', **call)
        reduced = original_effects(counts[:2], obs.iloc[:2].reset_index(drop=True), genes,
                                   targets=['T'], condition='group', **call)
        np.testing.assert_allclose(scattered['shrunk'][0], full.shrunk[0], rtol=1e-5, atol=1e-5, equal_nan=True)
        self.assertFalse(np.allclose(reduced.shrunk, full.shrunk, equal_nan=True))
        self.assertEqual(used, ['A'])
        self.assertEqual(cells, 20)
        self.assertEqual(float(full.shrunk[0, 0]), 0.0)


class ReleaseMix(unittest.TestCase):
    def test_mix_saves_effects_and_holds_the_line_only_in_its_split(self):
        def table(name, value, condition):
            values = np.array([[value, value]], dtype=np.float32)
            return AxisTable(name, ['G1'], values, values, np.full_like(values, np.nan),
                             np.array([100.0]), {'condition': condition})
        fragments = [
            {'unit': 'D1_Rest', 'transfer_source_id': 'cd4_mix', 'line_group': 'CD4T',
             'admitted_model': True, 'exclude_only_when_held': True, 'table': table('cd4_rest', 1.0, 'Rest')},
            {'unit': 'D1_Stim8hr', 'transfer_source_id': 'cd4_mix', 'line_group': 'CD4T',
             'admitted_model': True, 'exclude_only_when_held': True, 'table': table('cd4_stim', 3.0, 'Stim8hr')},
            {'unit': 'hepg2_nadig', 'transfer_source_id': 'hepg2_nadig', 'line_group': 'HepG2',
             'role': 'validation', 'admitted_model': True, 'exclude_only_when_held': True,
             'table': table('hepg2_nadig', 9.0, 'HepG2')},
        ]
        recipe = {'source_weight': 1.0, 'gamma': 1.0, 'reliability_scale': 100.0, 'amplitude': 1.576}
        with tempfile.TemporaryDirectory() as folder:
            kept = save_extended_release(
                fragments, Path(folder) / 'kept', missing=['k562_gwps'], recipe=recipe,
                split_name='C:K562', held_group='K562')
            self.assertIn('cd4_mix', kept['sources'])
            self.assertIn('hepg2_nadig', kept['sources'])
            self.assertFalse(kept['claims_complete_corpus'])
            self.assertFalse(kept['fit_admitted'])
            self.assertTrue((Path(folder) / 'kept' / 'effects.npz').is_file())
            self.assertTrue((Path(folder) / 'kept' / 'manifest.json').is_file())
            self.assertTrue((Path(folder) / 'kept' / 'exposure.json').is_file())
            held = save_extended_release(
                fragments, Path(folder) / 'held', missing=['k562_gwps'], recipe=recipe,
                split_name='C:HepG2', held_group='HepG2')
            self.assertNotIn('hepg2_nadig', held['sources'])
            self.assertIn('hepg2_nadig', held['held_out_by_split'])


if __name__ == '__main__':
    unittest.main()
