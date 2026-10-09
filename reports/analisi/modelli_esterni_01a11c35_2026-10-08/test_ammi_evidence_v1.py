"""Tiny metadata fixtures: incomplete exports cannot become completed evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from collect_ammi_evidence_v1 import digest, metadata_name, validate


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.save('template.json', {'queries': {'query-context': 'outer'}})
        self.prepared = dict(slug='davidmaisterx/job', private=True, fold='C-K562', mode='cells',
            template=dict(path=str(self.root/'template.json'), sha256=digest(self.root/'template.json')))
        training = dict(input_receipt_sha256='runtime', device='cuda', fixture=False,
            context_mode='cells', seed=17, epochs=[dict(epoch=e, guard={'pass': True}) for e in (1, 2)])
        self.save('training_receipt.json', training)
        self.save('preflight.json', dict(manifest_sha256='runtime'))
        self.save('zero_residual_parity.receipt.json', dict(zero_residual=True, byte_parity=True,
            output_sha256='anchor', anchor_sha256='anchor'))
        claim = dict(quantity='ln_fold_change', emission_scale_applied=False,
            anchor_sha256='anchor', output_sha256='prediction', bytes=99)
        self.save('query_000_native.receipt.json', claim)
        self.complete = dict(status='COMPLETE', fold='C-K562', mode='cells', seed=17,
            device='cuda', no_outer_truth_read=True, manifest_sha256='runtime',
            training_receipt_sha256=digest(self.root/'training_receipt.json'),
            checkpoint=dict(path='/kaggle/working/job/checkpoint.pt', bytes=32, sha256='checkpoint'),
            exports=[dict(context_id='query-context', control_context_id='query-context',
                intervention='native', file='query_000_native.npz', receipt=claim)],
            diagnostic_failures=[dict(context_id='query-context',
                status='GUARD_FAILED_DIAGNOSTIC_ONLY', native_export_preserved=True)])
        self.save('complete.json', self.complete)
        self.inventory = {'job/checkpoint.pt', 'job/query_000_native.npz'}

    def save(self, name, value):
        (self.root/name).write_text(json.dumps(value), encoding='utf-8')

    def test_swap_failure_preserves_native_without_promotion(self):
        report = validate(self.root, self.prepared, self.inventory)
        self.assertEqual(report['status'], 'METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING')
        self.assertFalse(report['exports'][0]['binary_hash_verified'])
        self.assertFalse(report['scientific_benefit_verified'])

    def test_missing_native_or_swap_receipt_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.root, self.prepared, {'job/checkpoint.pt'})
        self.complete['diagnostic_failures'] = []
        self.save('complete.json', self.complete)
        with self.assertRaises(ValueError):
            validate(self.root, self.prepared, self.inventory)

    def test_changed_training_receipt_rejected(self):
        with (self.root/'training_receipt.json').open('a') as stream:
            stream.write(' ')
        with self.assertRaises(ValueError):
            validate(self.root, self.prepared, self.inventory)

    def test_allowlist_excludes_source_data_logs_and_paths(self):
        for name in ('job/ntc.npz', 'job/query_000_native.npz', 'job/checkpoint.pt',
                     'job/../complete.json', '../complete.json', 'job/runtime.json',
                     'job.log', 'job/private_locators.json'):
            self.assertIsNone(metadata_name(name, 'job'))
        self.assertEqual(metadata_name('job/query_000_native.receipt.json', 'job'),
                         'query_000_native.receipt.json')


if __name__ == '__main__':
    unittest.main()
