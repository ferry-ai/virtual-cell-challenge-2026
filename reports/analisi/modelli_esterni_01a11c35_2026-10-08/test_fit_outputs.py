"""Small artifact fixtures: corruption, semantic masks and frozen reload parity."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from feature_policy import POLICY
from pie_adapter import sha256
from verify_fit_outputs import verify


class OutputTests(unittest.TestCase):
    def fixture(self, root):
        fit=root/'job'/'fit';fit.mkdir(parents=True)
        esm=root/'esm';esm.mkdir()
        feature=np.arange(1280,dtype=np.float32)[None,:]/1280
        np.save(esm/'embeddings.npy',feature)
        (esm/'meta.json').write_text(json.dumps(dict(name='esm2',layout='dense',index='pert',
            keys=['A'],dim=1280,dtype='float32',provenance={'synthetic':True})))
        coef=np.ones((1281,3),dtype=np.float64)*.001
        generic=np.array([1.,0.,3.]);support=np.array([True,False,True])
        np.savez_compressed(fit/'ridge.npz',coef=coef,intercept=generic,generic=generic,support=support,
            feature_mean=np.zeros(1281),feature_scale=np.ones(1281),
            imputation_mean=feature[0],feature_policy=np.asarray(POLICY))
        targets=['A']*16+['missing'];queries=[dict(target=t,context_id='c'+str(i),context_group='new') for i,t in enumerate(targets)]
        effect=np.full((17,3),np.nan)
        effect[:16]=np.column_stack((feature,np.zeros(1)))@coef+generic
        effect[:,1]=np.nan
        available=np.array([True]*16+[False]);mask=available[:,None]&support
        values=dict(effects=effect,observed=mask,genes=np.array(['g0','g1','g2']),targets=np.array(targets),
            context_ids=np.array([q['context_id'] for q in queries]),context_groups=np.array(['new']*17),
            esm2_observed=available,generic=np.broadcast_to(generic,(17,3)),generic_observed=np.broadcast_to(support,(17,3)))
        np.savez_compressed(fit/'native_predictions.npz',**values)
        receipt=dict(manifest=dict(regime='production',alpha=1.,queries=queries,
            esm2=dict(sha256={n:sha256(esm/n) for n in ('meta.json','embeddings.npy')})),
            exposure=dict(targets_read=['A']),context_lineages={'seen':'old'},
            store_receipt=dict(source_manifest=dict(genes=['g0','g1','g2'])))
        prepared=root/'prepared.json';prepared.write_text(json.dumps(dict(queries=17,job_id='fixture')))
        self.seal(fit,receipt)
        return fit,prepared,esm,receipt,values

    def seal(self,fit,receipt):
        receipt.update(model_sha256=sha256(fit/'ridge.npz'),native_predictions_sha256=sha256(fit/'native_predictions.npz'))
        (fit/'manifest.json').write_text(json.dumps(receipt))
        (fit.parent/'complete.json').write_text(json.dumps(dict(status='COMPLETE',model_sha256=receipt['model_sha256'],
            predictions_sha256=receipt['native_predictions_sha256'],receipt_sha256=sha256(fit/'manifest.json'))))

    def test_stream_all_blocks_and_reload_missing_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            fit,prepared,esm,_,_=self.fixture(Path(tmp))
            result=verify(fit.parent,prepared,esm)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['queries'],17)
            self.assertEqual(result['feature_missing_queries'],1)

    def test_mask_corruption_even_when_checksums_are_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fit,prepared,esm,receipt,values=self.fixture(Path(tmp))
            values['observed'][10,0]=False
            np.savez_compressed(fit/'native_predictions.npz',**values);self.seal(fit,receipt)
            with self.assertRaisesRegex(ValueError,'mask differs'):
                verify(fit.parent,prepared,esm)

    def test_reload_detects_inconsistent_numeric_predictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            fit,prepared,esm,receipt,values=self.fixture(Path(tmp))
            values['effects'][0,0]+=1
            np.savez_compressed(fit/'native_predictions.npz',**values);self.seal(fit,receipt)
            with self.assertRaises(AssertionError):verify(fit.parent,prepared,esm)

    def test_checksum_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            fit,prepared,esm,_,_=self.fixture(Path(tmp))
            with (fit/'ridge.npz').open('ab') as f:f.write(b'corrupted')
            with self.assertRaisesRegex(ValueError,'checksum'):
                verify(fit.parent,prepared,esm)


if __name__=='__main__':unittest.main()
