import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import preflight as guard


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / 'effects.npz'
        np.savez(self.input, targets=np.array(['A', 'B']), lfc=np.ones((2, 1)))
        paths = {'local': str(self.input), 'runtime': str(self.input)}
        self.manifest = {'schema_version': 1, 'job_id': 'test',
            'inputs': [{'id': 'effects', 'paths': paths, 'bytes': self.input.stat().st_size, 'sha256': guard.digest(self.input)}],
            'outputs': [{'id': 'result', 'paths': {'local': str(self.root / 'new'), 'runtime': str(self.root / 'new')}, 'must_be_absent': True}],
            'target_checks': [{'input_id': 'effects', 'npz_key': 'targets', 'required': ['A', 'B']}],
            'environment': {'packages': {}, 'imports': [], 'probes': []}}

    def test_valid_contract_both_sites_does_not_create_job_output(self):
        for site in ['local', 'runtime']:
            self.assertEqual(guard.validate(self.manifest, site)['status'], 'PASS')
        self.assertFalse((self.root / 'new').exists())

    def test_missing_file_even_when_completion_marker_exists(self):
        marker = self.root / 'finished.json'; marker.write_text('{}')
        self.manifest['inputs'].append({'id': 'finished', 'paths': {'local': str(marker)},
            'bytes': marker.stat().st_size, 'sha256': guard.digest(marker)})
        self.manifest['inputs'][0]['paths']['local'] = str(self.root / 'not-synced.npz')
        with self.assertRaisesRegex(guard.InvalidJob, 'Missing input'):
            guard.validate(self.manifest, 'local')

    def test_wrong_hash_at_same_size_and_wrong_size(self):
        self.manifest['inputs'][0]['sha256'] = 'f' * 64
        with self.assertRaisesRegex(guard.InvalidJob, 'SHA256 differs'):
            guard.validate(self.manifest, 'local')
        self.manifest['inputs'][0]['bytes'] += 1
        with self.assertRaisesRegex(guard.InvalidJob, 'size differs'):
            guard.validate(self.manifest, 'local')

    def test_missing_reserve_targets_rejected_before_work(self):
        self.manifest['target_checks'][0]['required'] = ['RESERVE']
        with self.assertRaisesRegex(guard.InvalidJob, 'lacks required targets: RESERVE'):
            guard.validate(self.manifest, 'local')

    def test_existing_output_and_duplicate_ids_rejected(self):
        (self.root / 'new').mkdir()
        with self.assertRaisesRegex(guard.InvalidJob, 'Output already exists'):
            guard.validate(self.manifest, 'local')
        self.manifest['outputs'][0]['id'] = 'effects'
        with self.assertRaisesRegex(guard.InvalidJob, 'duplicate'):
            guard.validate(self.manifest, 'local')

    def test_environment_missing_import_and_wrong_python(self):
        self.manifest['environment']['imports'] = ['vcc_missing_probe_dependency']
        with self.assertRaises(ImportError):
            guard.validate(self.manifest, 'local')
        self.manifest['environment']['python'] = {'paths': {'local': str(self.root / 'other-python')}}
        with self.assertRaisesRegex(guard.InvalidJob, 'declared job Python'):
            guard.validate(self.manifest, 'local')

    def test_declared_h5ad_nullable_roundtrip(self):
        self.manifest['environment'] |= {'probes': ['h5ad_nullable_roundtrip'], 'allow_write_nullable_strings': True}
        result = guard.validate(self.manifest, 'local')
        self.assertEqual(result['environment']['probes_passed'], ['h5ad_nullable_roundtrip'])
        self.assertIn('This process only', result['environment']['configuration_scope'])

    def test_duplicate_or_nested_outputs_rejected(self):
        for value in [self.root / 'new', self.root / 'new' / 'nested']:
            candidate = copy.deepcopy(self.manifest)
            candidate['outputs'].append({'id': 'other', 'paths': {'local': str(value)}, 'must_be_absent': True})
            with self.assertRaisesRegex(guard.InvalidJob, 'overlap'):
                guard.validate(candidate, 'local')

    def test_manifest_mutation_during_validation_cannot_leave_pass(self):
        manifest = self.root / 'job.json'; receipt = self.root / 'receipt.json'
        manifest.write_text(json.dumps(self.manifest), encoding='utf-8')
        def altered(*unused):
            manifest.write_text('{}', encoding='utf-8')
            return {'status': 'PASS'}
        argv = ['preflight', 'validate', '--manifest', str(manifest), '--site', 'local', '--receipt', str(receipt)]
        with patch.object(sys, 'argv', argv), patch.object(guard, 'validate', side_effect=altered):
            with self.assertRaises(SystemExit) as error:
                guard.main()
        self.assertEqual(error.exception.code, 1)
        self.assertEqual(json.loads(receipt.read_text())['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
