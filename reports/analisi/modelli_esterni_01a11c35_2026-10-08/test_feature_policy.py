"""Missing-feature training retention and C/T/J separation on small fixtures."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from feature_policy import POLICY, prepare_features, validate_queries
from chunk_store_v2 import build_store, load_store
from embedding_ridge import MaskedRidge
from pie_adapter import sha256
from run_sufficient_probe_v2 import run
from predict_saved_ridge import predict as predict_saved


class FeaturePolicyTests(unittest.TestCase):
    def test_weighted_training_only_mean_and_missing_flag(self):
        x = np.array([[1., 3.], [5., 7.], [np.nan, np.nan], [999., -999.]])
        index = np.array([0, 1, 2, 0])
        weight = np.array([1., 2., 9., 3.])
        actual, mean, receipt = prepare_features(x, [True, True, False, True], 3, index, weight, POLICY)
        np.testing.assert_allclose(mean, [7/3, 13/3])
        np.testing.assert_allclose(actual[2], [7/3, 13/3, 1])
        self.assertEqual(receipt['missing_training_rows'], 1)
        self.assertEqual(receipt['missing_training_weight'], 9)
        x[3] *= 12345
        x[2] = 12345  # Unobserved placeholders cannot affect imputation.
        _, other, _ = prepare_features(x, [True, True, False, True], 3, index, weight, POLICY)
        np.testing.assert_array_equal(mean, other)
        with self.assertRaisesRegex(ValueError, 'explicit'):
            prepare_features(x, [True]*4, 3, index, weight, 'silent_zero')
        with self.assertRaisesRegex(ValueError, 'no observed'):
            prepare_features(x, [False]*4, 3, index, weight, POLICY)

    def test_regimes_reject_wrong_target_or_context(self):
        def check(regime, target='new', cid='seen-id', group='seen'):
            validate_queries(regime, ['old'], ['seen'], ['seen-id'],
                             [dict(target=target, context_id=cid, context_group=group)])
        check('T')
        check('C', 'old', 'new-id', 'new')
        check('J', 'new', 'new-id', 'new')
        check('production', 'old')
        for args in [('T', 'old'), ('T', 'new', 'new-id', 'seen'),
                     ('C', 'new', 'new-id', 'new'), ('C', 'old'),
                     ('J', 'old', 'new-id', 'new'), ('J', 'new'),
                     ('production', 'new', 'seen-id', 'wrong')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                check(*args)

    def test_real_runner_T_retains_missing_rows_matches_dense_and_masks_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['A', 'B', 'missing']
            genes = ['g0', 'g1', 'unsupported']
            y = np.array([[1, 4, np.nan], [3, 1, np.nan], [9, np.nan, np.nan]], np.float32)
            mask = np.isfinite(y)
            weights = [1., 3., 7.]
            identity = dict(study='fixture', line_group='seen', modality='CRISPRi')
            chunk = root/'chunk.npz'
            np.savez(chunk, targets=names, genes=genes, shrunk=y, mask=mask, meta=json.dumps(identity))
            source = dict(schema='external-ridge-chunks/1', modality='CRISPRi', regime='T',
                          quantity='fixture', normalization='fixture', effect_field='shrunk',
                          validation_review='fixture', release_sha256='a'*64, split_manifest_sha256='b'*64,
                          genes=genes, excluded_contexts=[], excluded_targets=['new', 'new-missing'],
                          expected_rows_by_context={'seen-id':3},
                          chunks=[dict(path=str(chunk), sha256=sha256(chunk), context_id='seen-id',
                                       context_group='seen', targets=names, weights=weights, identity=identity)])
            source_path = root/'source.json'; source_path.write_text(json.dumps(source))
            store = root/'store'; build_store(source_path, store)
            source['mask_storage'] = 'finite_verified'
            source_path.write_text(json.dumps(source))
            implicit = root/'implicit'; build_store(source_path, implicit)
            _, implicit_mask, _, _ = load_store(implicit, sha256(implicit/'manifest.json'))
            np.testing.assert_array_equal(implicit_mask[:2, :2], mask[:2, :2])
            del implicit_mask
            self.assertFalse((implicit/'observed.npy').exists())
            esm = root/'esm'; esm.mkdir()
            np.save(esm/'embeddings.npy', np.array([[1., 3.], [5., 7.], [2., 6.]], np.float32))
            (esm/'meta.json').write_text(json.dumps(dict(name='esm2', layout='dense', index='pert',
                keys=['A', 'B', 'new'], dim=2, dtype='float32', provenance={'synthetic':True})))
            config = dict(schema_version=1, protocol_status='agreed', validation_review='fixture',
                quantity='fixture', normalization='fixture', modality='CRISPRi', regime='T', mode='development',
                alpha=1., release_sha256='a'*64, split_manifest_sha256='b'*64,
                train=dict(path=str(store), sha256=sha256(store/'manifest.json')),
                expected_rows_by_context={'seen-id':3}, excluded_contexts=[], excluded_targets=['new', 'new-missing'],
                esm2=dict(path=str(esm), sha256={n:sha256(esm/n) for n in ('meta.json', 'embeddings.npy')}),
                queries=[dict(context_id='seen-id', context_group='seen', target=t) for t in ['new', 'new-missing']],
                missing_feature_policy=POLICY, row_block=2, gene_block=2)
            manifest = root/'fit.json'; manifest.write_text(json.dumps(config))
            progress = []
            receipt = run(manifest, root/'out', progress=lambda model,start,stop,counters:
                          progress.append((start,stop,counters['genes_completed'])))
            self.assertEqual(progress, [(0,2,2),(2,3,3)])
            self.assertEqual(receipt['exposure']['rows_read'], 3)
            self.assertEqual(receipt['feature_policy']['missing_training_rows'], 1)
            self.assertEqual(receipt['feature_policy']['rows_dropped'], 0)
            x, mean, _ = prepare_features(np.array([[1.,3.], [5.,7.], [np.nan,np.nan], [2.,6.]]),
                [True,True,False,True], 3, np.arange(3), weights, POLICY)
            dense = MaskedRidge(1.).fit(x[:3], y, mask, row_contexts=['seen']*3, row_targets=names,
                sample_weight=weights, excluded_contexts=[], excluded_targets=[])
            with np.load(root/'out'/'native_predictions.npz') as prediction:
                expected, _ = dense.predict(x[3:])
                np.testing.assert_allclose(prediction['effects'][:1], expected, atol=1e-11, equal_nan=True)
                self.assertFalse(prediction['observed'][1].any())
                self.assertTrue(np.isnan(prediction['effects'][1]).all())
                self.assertAlmostEqual(prediction['generic'][0, 0], 73/11)
                self.assertFalse(prediction['generic_observed'][:,2].any())
            with np.load(root/'out'/'ridge.npz') as model:
                np.testing.assert_array_equal(model['imputation_mean'], mean)
            reloaded = predict_saved(root/'out', esm, config['queries'])
            with np.load(root/'out'/'native_predictions.npz') as original:
                for key in ('effects', 'observed', 'generic', 'esm2_observed'):
                    np.testing.assert_array_equal(reloaded[key], original[key])
            config['train'] = dict(path=str(implicit), sha256=sha256(implicit/'manifest.json'))
            manifest.write_text(json.dumps(config)); run(manifest, root/'implicit-out')
            with np.load(root/'out'/'ridge.npz') as a, np.load(root/'implicit-out'/'ridge.npz') as b:
                np.testing.assert_array_equal(a['coef'], b['coef'])
            bad = y.copy(); bad[0, 0] = np.nan
            np.savez(chunk, targets=names, genes=genes, shrunk=bad, mask=mask, meta=json.dumps(identity))
            source['chunks'][0]['sha256'] = sha256(chunk)
            source_path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError, 'invalid observed'):
                build_store(source_path, root/'invalid-mask')


if __name__ == '__main__':
    unittest.main()
