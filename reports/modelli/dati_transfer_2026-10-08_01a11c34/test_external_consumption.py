"""Small receipt fixtures catch dropped contexts, changed weights and forged hashes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from verify_external_consumption import sha, verify


class ConsumptionTests(unittest.TestCase):
    def fixture(self, root):
        view = dict(genes=['G1', 'G2'], quantity='natural-log fold change', normalization='frozen',
            modality='CRISPRi', regime='T', release_sha256='release', split_manifest_sha256='split',
            excluded_targets=['HIDDEN'], excluded_contexts=[], expected_rows_by_context={'c1': 1, 'c2': 1},
            chunks=[dict(path='UNRESOLVED_MOUNT/' + c, producer='p/job', producer_file=c + '.npz',
                bytes=100, sha256=c, context_id=c, context_group='lineage', targets=[t], weights=[0.5],
                identity={'modality': 'CRISPRi', 'line_group': 'lineage'})
                for c, t in [('c1', 'T1'), ('c2', 'T2')]])
        self.save(root/'view.json', view)
        digest = sha(root/'view.json')
        source = copy.deepcopy(view)
        source['runtime_resolution'] = dict(source_view_sha256=digest, chunk_hashes_verified=True,
                                            source_visibility_changed=False)
        source['mask_storage'] = 'finite_verified'
        for c in source['chunks']:
            c['path'] = '/kaggle/input/' + c['producer_file']
        code = {n: 'frozen-' + n for n in ('run_sufficient_probe_v2.py', 'target_sufficient_ridge_v2.py',
            'embedding_ridge.py', 'chunk_store_v2.py', 'pie_adapter.py', 'feature_policy.py')}
        fit = dict(model_sha256='model', native_predictions_sha256='predictions', code=code,
            manifest={k: view[k] for k in ('quantity', 'normalization', 'modality', 'regime', 'release_sha256',
                'split_manifest_sha256', 'expected_rows_by_context', 'excluded_targets', 'excluded_contexts')},
            store_receipt=dict(source_manifest=source, shape=[2, 2], original_mask_equivalence_verified_chunks=2,
                builder_sha256=code['chunk_store_v2.py']),
            consumed_rows_by_context={'c1': 1, 'c2': 1}, consumed_rows_by_lineage={'lineage': 2},
            context_lineages={'c1': 'lineage', 'c2': 'lineage'},
            exposure=dict(rows_read=2, unique_feature_targets=2, targets_read=['T1', 'T2'],
                rows_by_context_group={'lineage': 2}, total_row_weight=1., alpha=1., uses_context=False,
                changes_to_bank_or_shrinkage=False, observed_per_gene=[2, 1], weighted_observations_per_gene=[1., 0.5]))
        self.save(root/'fit.json', fit)
        done = dict(status='COMPLETE', receipt_sha256=sha(root/'fit.json'),
                    model_sha256='model', predictions_sha256='predictions')
        self.save(root/'complete.json', done)
        self.save(root/'resolution.json', dict(source_view_sha256=digest, chunks=2, rows=2, contexts=2,
            bytes_verified=200, downloaded_bytes=0, inputs=[dict(producer=c['producer'], file=c['producer_file'],
                bytes=c['bytes'], sha256=c['sha256'], route='native_mount') for c in view['chunks']]))
        self.save(root/'prepared.json', dict(view_sha256=digest, private=True,
            slug='davideferrante11/esm2-fixture', modules=code, private_bytes=0))
        return view, fit, done

    def save(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def check(self, root):
        return verify(root/'view.json', sha(root/'view.json'), root/'fit.json',
            root/'complete.json', root/'resolution.json', root/'prepared.json')

    def test_complete_receipts_preserve_all_contexts_without_claiming_arrays_or_benefit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            result = self.check(root)
            self.assertEqual((result['rows'], result['contexts'], result['targets']), (2, 2, 2))
            self.assertFalse(result['prediction_arrays_independently_verified'])
            self.assertFalse(result['complete_D053'])

    def test_rehashed_receipt_cannot_change_weights_split_or_drop_context(self):
        mutations = [lambda f: f['store_receipt']['source_manifest']['chunks'][0]['weights'].__setitem__(0, .75),
            lambda f: f['store_receipt']['source_manifest']['excluded_targets'].clear(),
            lambda f: f['consumed_rows_by_context'].pop('c2')]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); _, fit, done = self.fixture(root)
                mutate(fit); self.save(root/'fit.json', fit)
                done['receipt_sha256'] = sha(root/'fit.json'); self.save(root/'complete.json', done)
                with self.assertRaises(ValueError): self.check(root)

    def test_receipt_identity_and_code_identity_are_independent_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, fit, done = self.fixture(root)
            fit['code']['feature_policy.py'] = 'changed'; self.save(root/'fit.json', fit)
            with self.assertRaisesRegex(ValueError, 'completion receipt hash'): self.check(root)
            done['receipt_sha256'] = sha(root/'fit.json'); self.save(root/'complete.json', done)
            with self.assertRaisesRegex(ValueError, 'fit code identity'): self.check(root)


if __name__ == '__main__':
    unittest.main()
