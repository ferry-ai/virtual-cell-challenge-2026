"""Small failure-boundary tests for production provenance and diagnostic export."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from ammi_inputs_v4 import load_anchors,training_data
from ammi_io_v4 import save_checkpoint,reload_checkpoint
from ammi_context import ContextCorrection
from pie_adapter import sha256
from run_ammi_v4 import query_export,run

def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha256(p))

class RuntimeTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_swapped_failure_preserves_native_and_checkpoint(self):
        anchor=dict(lfc=np.ones((3,2),np.float32),observed=np.ones((3,2),bool))
        p=self.root/'anchor.npz';np.savez(p,targets=['a','b','c'],genes=['g','h'],**anchor)
        model=ContextCorrection(2,2,torch.zeros(4));checkpoint=save_checkpoint(model,self.root/'model.pt',{})
        def fake(*args,**kwargs):
            if args[3]=='swapped':raise ValueError('guard failed')
            return anchor['lfc'],np.zeros((3,2)),[]
        with patch('run_ammi_v4.swapped_contexts',return_value=['swapped']),patch('run_ammi_v4.predict',side_effect=fake):
            exports,failures=query_export(model,None,None,{'native':'OUTER'},{},anchor,pin(p),
                ['a','b','c'],['g','h'],self.root,{'swapped':'TRAIN'},'cells')
        self.assertEqual(len(exports),1);self.assertEqual(len(failures),1)
        self.assertEqual(sha256(self.root/'query_000_native.npz'),sha256(p))
        self.assertEqual(sha256(Path(checkpoint['path'])),checkpoint['sha256'])
        restored,_=reload_checkpoint(checkpoint,torch.device('cpu'))
        for k,v in model.state_dict().items():torch.testing.assert_close(v,restored.state_dict()[k])

    def test_production_parity_uses_its_own_verified_pairs(self):
        requests=[];done=[];locations={}
        for ident,excluded,sources in [('row',['TRAIN'],['other']),('query',[],['train','other']),('A',[],['train','other'])]:
            p=self.root/(ident+'.npz')
            np.savez(p,targets=['t'],genes=['g'],lfc=np.ones((1,1),np.float32),observed=np.ones((1,1),bool))
            locations[ident]=pin(p)
            consumed={s:'a'*64 for s in sources}
            requests.append(dict(id=ident,excluded_lineages=excluded,sources=sources,expected_cache_sha256=consumed))
            done.append(dict(id=ident,excluded_lineages=excluded,consumed=consumed,effects_sha256=sha256(p)))
        contract=dict(requests=requests,source_lineages={'train':'TRAIN','other':'OTHER'},parity_pairs=[['A','query']])
        fold=dict(mode='production',outer=None,inner=None,outer_query_anchor='query',
                  contexts={'c':dict(role='training',lineage='TRAIN',anchor_id='row')})
        receipt=dict(status='COMPLETE',requests=done,outer_only_reference_parity_verified=False,
                     production_parity_pairs_verified=[['A','query']])
        p=self.root/'completion.json';p.write_text(json.dumps(receipt))
        self.assertEqual(set(load_anchors(contract,pin(p),locations,fold,['g'],['t'])),{'row','query'})
        receipt['production_parity_pairs_verified']=[];p.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'production T0 parity'):
            load_anchors(contract,pin(p),locations,fold,['g'],['t'])

    def test_production_rejects_held_training_view(self):
        view=dict(schema='external-ridge-chunks/1',modality='CRISPRi',genes=['g'],
                  regime='C',excluded_contexts=['X'],excluded_targets=[])
        with self.assertRaisesRegex(ValueError,'production view'):
            training_data(view,dict(mode='production'),{},[],None,None,{},'1'*64,'2'*64)

    def test_cpu_cannot_run_biological_pilot(self):
        p=self.root/'spec.json';p.write_text(json.dumps(dict(schema='AMMI-biological-runtime/4',
            status='ready',mode='pilot',fold='C-K562')))
        with patch('torch.cuda.is_available',return_value=False),self.assertRaisesRegex(RuntimeError,'actual CUDA'):
            run(p,sha256(p),'cells',17,self.root/'out')
        self.assertFalse((self.root/'out').exists())

if __name__=='__main__':unittest.main()
