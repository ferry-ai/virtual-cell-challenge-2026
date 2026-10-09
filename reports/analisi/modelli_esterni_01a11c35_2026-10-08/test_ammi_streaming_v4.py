"""Small synthetic tests of sparse staging and recomputed control gradients."""
import copy
import gc
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch

from ammi_controls_v4 import stage_controls, validate_origin
from ammi_encoder_v4 import encode
from ammi_context import ContextCorrection
from ammi_train_v4 import fit
import test_ammi_biological_v3 as fixtures
import test_ammi_train_v2 as training_fixtures


class Stream:
    def __init__(self,x,m,limit):self.x=x;self.m=m;self.shape=x.shape;self.calls=[];self.limit=limit
    def batch(self,a,b):
        if b-a>self.limit:raise AssertionError('dense population materialized')
        self.calls.append((a,b));return self.x[a:b],self.m[a:b]


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        torch.set_num_threads(1)
        # Synthetic payloads are kilobytes; keep the production 1-GiB reserve
        # independent of other desktop apps during these algorithm tests.
        self.ram=patch('ammi_controls_v4.available_memory',return_value=8<<30)
        self.ram.start();self.addCleanup(self.ram.stop)
    def tearDown(self):gc.collect();self.tmp.cleanup()

    def test_sparse_merge_matches_original_and_accepts_pinned_old_producer(self):
        a,genes,reader=fixtures.BiologicalBoundaryTests.ntc_part(self,'a',0)
        b,_,_=fixtures.BiologicalBoundaryTests.ntc_part(self,'b',40)
        for p in (a,b):
            p['producer_code']=json.loads(Path(p['completion']['path']).read_text())['code']
            p.update(part_role='training',denominator_policy='ingestion_depth_native')
        controls,audit=stage_controls([b,a],genes,['c'],reader,{'a':'b'*64,'b':'b'*64},self.root/'stage')
        c=controls['c'];self.assertEqual(len(c),64)
        x,m=c.batch(10,14)
        np.testing.assert_allclose(x,np.tile([np.log1p(2000),np.log1p(3000),0],(4,1)),rtol=1e-6)
        self.assertFalse(m[:,2].any());self.assertFalse(audit['all_dense_control_arrays_materialized'])
        # Selection remains the globally lowest 64 cell priorities, independent of part order.
        selected=[(audit['parts'][int(p)]['part_id'],int(r)) for p,r in c.addresses]
        self.assertEqual(selected,[('a',i) for i in range(40)]+[('b',i) for i in range(24)])
        del c,controls;gc.collect()

    def test_missing_part_fails_even_when_context_is_present(self):
        a,genes,reader=fixtures.BiologicalBoundaryTests.ntc_part(self,'a',0)
        a['producer_code']=json.loads(Path(a['completion']['path']).read_text())['code']
        a.update(part_role='training',denominator_policy='ingestion_depth_native')
        with self.assertRaisesRegex(ValueError,'part coverage'):
            stage_controls([a],genes,['c'],reader,{'a':'b'*64,'missing':'c'*64},self.root/'stage')

    def test_streamed_encoder_outputs_and_gradients_match_eager(self):
        rng=np.random.default_rng(12)
        x=rng.normal(size=(17,5)).astype(np.float32);m=rng.random(x.shape)>.2;m[:,0]=True
        x[~m]=np.nan
        for mode in ('cells','mean'):
            torch.manual_seed(14)
            eager=ContextCorrection(5,4,torch.zeros(6),context_mode=mode)
            stream=copy.deepcopy(eager)
            value=eager.encode_controls(torch.from_numpy(x)[None],torch.from_numpy(m)[None],torch.ones((1,len(x)),dtype=torch.bool))
            value.square().sum().backward()
            source=Stream(x,m,3)
            saved=[]
            def pack(t):saved.append(tuple(t.shape));return t
            with torch.autograd.graph.saved_tensors_hooks(pack,lambda t:t):
                actual=encode(stream,source,torch.device('cpu'),block_size=3)
                actual.square().sum().backward()
            torch.testing.assert_close(actual,value,atol=2e-7,rtol=2e-6)
            for a,b in zip(eager.cell_encoder.parameters(),stream.cell_encoder.parameters()):
                torch.testing.assert_close(a.grad,b.grad,atol=2e-7,rtol=2e-5)
            self.assertNotIn((17,10),saved)
            if mode=='cells':self.assertGreater(len(source.calls),6)

    def test_destination_depth_policy_cannot_be_silently_relabelled(self):
        spec=dict(part_role='destination',denominator_policy='full_provided_official_X_before_alignment')
        validate_origin(spec,dict(spec))
        with self.assertRaisesRegex(ValueError,'provenance'):
            validate_origin(spec,dict(part_role='destination',denominator_policy='ingestion_depth_native'))
        with self.assertRaisesRegex(ValueError,'provenance'):validate_origin(spec,{})
        validate_origin(dict(part_role='training',denominator_policy='ingestion_depth_native'),{})

    def test_streamed_training_and_checkpoint_before_guard_failure(self):
        f=training_fixtures.TrainerTests();f.setUp()
        controls={c:Stream(x,m,256) for c,(x,m) in f.controls.items()}
        calls=[]
        with self.assertRaisesRegex(ValueError,'guard failed'):
            fit(f.data,controls,[],'cells',17,lambda model,epoch:{'pass':False},fixture=True,
                checkpoint_callback=lambda model,epoch,audit:calls.append(epoch))
        self.assertEqual(calls,[1])
        model,receipt=fit(f.data,controls,[],'none',17,lambda model,epoch:{'pass':True},fixture=True)
        self.assertEqual(len(receipt['epochs']),2)


if __name__=='__main__':unittest.main()
