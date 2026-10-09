"""Synthetic tests for the biological boundary; no real RNA or cloud jobs."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import scipy.sparse as sp
import torch

from ammi_inputs_v3 import checked, load_ntc, load_anchors, training_data, module
from ammi_guard_v3 import discrimination, predict, inner_guard
from ammi_context import ContextCorrection
from run_ammi_pilot_v3 import save_checkpoint, reload_checkpoint, run
from pie_adapter import sha256

HERE=Path(__file__).parent
REPO=HERE.parents[2]
DATI=REPO/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
VALID=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco'


def pin(path):
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha256(path))


class BiologicalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        torch.set_num_threads(1)

    def tearDown(self): self.temp.cleanup()

    def ntc_part(self, part, begin, n=40):
        root=self.root/part;root.mkdir()
        reader=pin(DATI/'ntc_cells.py')
        genes=['g0','g1','g2']
        sp.save_npz(root/'counts.npz',sp.csr_matrix(np.tile([2,3,0],(n,1))))
        np.savez(root/'axes_depth_mask.npz',genes=genes,native_depth=np.full(n,10.),
                 masks=np.array([[True,True,False]]),mask_index=np.zeros(n,dtype=int))
        records=[dict(part_id=part,context_id='c',identity={k:'x' for k in (
            'study','context','donor_or_clone','condition','modality','chemistry')},
            stratum=['lib','batch','NTC'],cell_key=str(i),priority=f'{i:064x}',
            stratum_population=100,source_sha256='a'*64,source_row=i) for i in range(begin,begin+n)]
        (root/'cells.json').write_text(json.dumps(records))
        files={name:pin(root/name) for name in ('counts.npz','axes_depth_mask.npz','cells.json')}
        receipt=dict(schema='native-NTC-extraction-completion/1',status='COMPLETE',part_id=part,
            plan_sha256='b'*64,perturbed_RNA_rows_read=0,code={'ntc_cells.py':reader['sha256']},
            normalized_scale='log1p(counts * 10000 / native_depth)',files=files,
            arrays_shape=[n,3],contexts={'c':n})
        (root/'complete.json').write_text(json.dumps(receipt))
        return dict(completion=pin(root/'complete.json'),plan_sha256='b'*64),genes,reader

    def test_ntc_global_reservoir_and_native_normalization(self):
        a,genes,reader=self.ntc_part('a',0)
        b,_,_=self.ntc_part('b',40)
        expected={'a':'b'*64,'b':'b'*64}
        controls,audit=load_ntc([b,a],genes,['c'],reader,expected)
        x,m=controls['c']
        self.assertEqual(x.shape,(64,3));self.assertEqual(audit['contexts']['c']['cells_before_global_merge'],80)
        np.testing.assert_allclose(x[0],[np.log1p(2000),np.log1p(3000),0],rtol=1e-6)
        self.assertTrue(m[:,:2].all());self.assertFalse(m[:,2].any())
        with self.assertRaisesRegex(ValueError,'coverage'): load_ntc([a],genes,['missing'],reader,{'a':'b'*64})
        with self.assertRaisesRegex(ValueError,'part coverage'):load_ntc([a],genes,['c'],reader,expected)

    def test_corrupt_pin_and_duplicate_cells_fail(self):
        a,genes,reader=self.ntc_part('a',0)
        b,_,_=self.ntc_part('b',0)
        with self.assertRaisesRegex(ValueError,'duplicate'):load_ntc([a,b],genes,['c'],reader,{'a':'b'*64,'b':'b'*64})
        Path(a['completion']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'pin'):load_ntc([a],genes,['c'],reader,{'a':'b'*64})

    def training_fixture(self):
        identity=dict(modality='CRISPRi',line_group='TRAIN')
        path=self.root/'chunk.npz';genes=['g0','g1'];panel=['t0','t1','t2']
        np.savez(path,genes=genes,targets=panel,meta=json.dumps(identity),
                 shrunk=np.array([[1,2],[3,4],[5,6]],dtype=np.float32),mask=np.ones((3,2),bool))
        chunk=dict(pin(path),context_id='c',context_group='TRAIN',identity=identity,targets=panel)
        inner=dict(chunk,context_id='held',sha256='f'*64,path='MUST_NOT_READ')
        view=dict(schema='external-ridge-chunks/1',modality='CRISPRi',regime='C',excluded_contexts=['OUTER'],
                  effect_field='shrunk',genes=genes,chunks=[inner,chunk])
        fold=dict(outer='OUTER',inner='INNER',no_final_refit=True,contexts={
            'c':dict(role='training',lineage='TRAIN',anchor_id='a'),
            'held':dict(role='inner_guard',lineage='INNER',anchor_id='q'),
            'gap':dict(role='training',lineage='GAP',anchor_id='z')})
        anchors={'a':dict(lfc=np.ones((3,2),np.float32),observed=np.ones((3,2),bool))}
        return view,fold,anchors,panel,np.eye(3,dtype=np.float32),np.array([True,False,True]),{chunk['sha256']:str(path)}

    def test_inner_response_not_resolved_and_gaps_are_named(self):
        args=self.training_fixture()
        a,audit=training_data(*args,'1'*64,'2'*64)
        self.assertEqual(len(a['contexts']),2)
        self.assertEqual(audit['contexts']['gap']['selected'],0)
        self.assertEqual(len(audit['consumed_chunks']),1)
        args[0]['chunks'][0]['targets']=['poison']
        b,_=training_data(*args,'1'*64,'2'*64)
        np.testing.assert_array_equal(a['response'],b['response'])
        self.assertEqual(a['row_ids'],b['row_ids'])

    def test_disc95_matches_independent_bench_with_missing_support(self):
        metrics=module(pin(VALID/'metrics.py'),'metrics')
        original=sys.modules.get('metrics');sys.modules['metrics']=metrics
        try: bench=module(pin(VALID/'bench_core.py'),'ammi_test_bench')
        finally:
            if original is None:sys.modules.pop('metrics',None)
            else:sys.modules['metrics']=original
        rng=np.random.default_rng(18);n=25;g=30
        panel=[f't{i}' for i in range(n)];genes=['t0']+[f'g{i}' for i in range(g-1)]
        base=rng.normal(size=(n,g)).astype(np.float32);mask=np.ones((n,g),bool)
        mask[2,4]=False;mask[3,7]=False;base[~mask]=0
        pred=base*.999
        truth=dict(targets=np.array(panel),raw=base.copy(),shrunk=base.copy(),se=np.ones((n,g)),n_cells=np.full(n,50))
        ours=discrimination(metrics,base,pred,mask,truth,panel,genes)
        effects={(a,'inner'):(base if a!='AMMI' else pred,mask) for a in ['T0','AMMI','T0~gamma0','T0~nocis']}
        result,*_=bench.measure({'inner':dict(lineage='INNER',truth=[dict(table='truth',role='primary')])},
            ['T0'],effects,lambda _:truth,panel,genes,log=lambda _:None,extra_arms=['AMMI'],
            extra_contrasts=[('delta','AMMI','T0')])
        result=result['inner']['truth']['truth']
        self.assertEqual(ours['anchor'],result['arms']['T0']['disc95'])
        self.assertEqual(ours['prediction'],result['arms']['AMMI']['disc95'])
        self.assertEqual(ours['positive_control'],result['contrasts']['c_shuffle']['measures']['disc95']['all'])
        self.assertEqual(ours['prediction_minus_anchor'],result['contrasts']['delta']['measures']['disc95']['all'])
        self.assertTrue(ours['pass'])
        with self.assertRaisesRegex(ValueError,'support'):
            discrimination(metrics,base,pred,np.zeros_like(mask),truth,panel,genes)

    def test_nested_anchor_consumption_and_row_exclusion(self):
        genes=['g0','g1'];panel=['t0','t1','t2']
        locations={};requests=[];complete=[]
        for ident,excluded,sources in [('a',['OUTER','INNER','TRAIN'],['other']),
                                        ('q',['OUTER','INNER'],['train','other'])]:
            path=self.root/(ident+'.npz')
            np.savez(path,targets=panel,genes=genes,lfc=np.ones((3,2),np.float32),observed=np.ones((3,2),bool))
            locations[ident]=pin(path)
            consumed={s+'.npz':('1' if s=='train' else '2')*64 for s in sources}
            requests.append(dict(id=ident,excluded_lineages=excluded,sources=sources,expected_cache_sha256=consumed))
            complete.append(dict(id=ident,excluded_lineages=excluded,consumed=dict(consumed),effects_sha256=sha256(path)))
        contract=dict(requests=requests,source_lineages={'train':'TRAIN','other':'OTHER'})
        receipt=self.root/'complete.json'
        receipt.write_text(json.dumps(dict(status='COMPLETE',outer_only_reference_parity_verified=True,requests=complete)))
        fold=dict(outer='OUTER',inner='INNER',inner_query_anchor='q',outer_query_anchor='q',
            contexts={'c':dict(role='training',lineage='TRAIN',anchor_id='a')})
        loaded=load_anchors(contract,pin(receipt),locations,fold,genes,panel)
        self.assertEqual(set(loaded),{'a','q'})
        fold['contexts']['c']['anchor_id']='q'
        with self.assertRaisesRegex(ValueError,'row lineage'):
            load_anchors(contract,pin(receipt),locations,fold,genes,panel)
        fold['contexts']['c']['anchor_id']='a'
        complete[1]['consumed']['poison.npz']='f'*64
        receipt.write_text(json.dumps(dict(status='COMPLETE',outer_only_reference_parity_verified=True,requests=complete)))
        with self.assertRaisesRegex(ValueError,'consumption'):
            load_anchors(contract,pin(receipt),locations,fold,genes,panel)

    def test_checkpoint_roundtrip_missing_feature_and_unchanged_mask(self):
        torch.manual_seed(2)
        model=ContextCorrection(3,4,torch.zeros(5)).eval()
        with torch.no_grad(): model.decoder.weight.normal_(0,1e-5)
        controls={'c':(np.ones((3,3),np.float32),np.ones((3,3),bool))}
        x=np.random.default_rng(3).normal(size=(6,5)).astype(np.float32)
        mask=np.ones((6,4),bool);mask[:,3]=False
        anchor=np.ones((6,4),np.float32);anchor[:,3]=0
        available=np.array([False,True,True,True,True,True]);x[0]=np.nan
        # Balanced target projection produces a residual passing the structural guard.
        x[1:]-=x[1:].mean(0)
        a,r,_=predict(model,x,available,'c',controls,anchor,mask)
        np.testing.assert_array_equal(a[0],anchor[0]);self.assertTrue((r[~mask]==0).all())
        saved=save_checkpoint(model,self.root/'model.pt',{'test':True})
        loaded,identity=reload_checkpoint(saved,torch.device('cpu'))
        b,_,_=predict(loaded,x,available,'c',controls,anchor,mask)
        np.testing.assert_array_equal(a,b);self.assertEqual(identity,{'test':True})

    def test_guard_original_cache_external_axis_and_review_boundary(self):
        rng=np.random.default_rng(18);n=25;g=30
        panel=[f't{i}' for i in range(n)];genes=[f'g{i}' for i in range(g)]
        base=rng.normal(size=(n,g)).astype(np.float32);mask=np.ones((n,g),bool)
        cache=self.root/'truth.npz'
        np.savez(cache,targets=panel,raw=base,shrunk=base,se=np.ones_like(base))
        axis=self.root/'axis.csv';axis.write_text('gene_name\n'+'\n'.join(genes)+'\n')
        review=self.root/'review.txt';review.write_text('SYNTHETIC FIXTURE ONLY')
        spec=dict(review_status='agreed',review_pin=pin(review),axis=pin(axis),
            rule='anchor-shuffle-disc95-lo-positive; structural-residual-r2; no-benefit-threshold',
            routes=[dict(context_id='c',lineage='INNER',role='primary',truth=pin(cache))])
        fold=dict(inner='INNER',outer='OUTER',inner_query_anchor='q',
                  contexts={'c':dict(role='inner_guard')})
        controls={'c':(np.ones((3,3),np.float32),np.ones((3,3),bool))}
        anchors={'q':dict(lfc=base,observed=mask)}
        x=rng.normal(size=(n,5)).astype(np.float32);available=np.ones(n,bool)
        args=(fold,pin(VALID/'metrics.py'),controls,anchors,x,available,panel,genes)
        guard,baseline=inner_guard(spec,*args)
        result=guard(ContextCorrection(3,g,torch.zeros(5)),1)
        self.assertTrue(result['pass']);self.assertIsNone(result['benefit_threshold'])
        spec['routes'][0]['lineage']='OUTER'
        spec['routes'][0]['truth']['path']='MUST_NOT_READ'
        with self.assertRaisesRegex(ValueError,'forbidden'):inner_guard(spec,*args)
        spec['review_status']='pending'
        with self.assertRaisesRegex(ValueError,'review'):inner_guard(spec,*args)

    def test_biological_runner_has_no_cpu_fallback(self):
        path=self.root/'runtime.json'
        path.write_text(json.dumps(dict(schema='AMMI-biological-runtime/3',status='ready',fold='C-K562')))
        from unittest.mock import patch
        with patch('torch.cuda.is_available',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'CUDA'):
                run(path,sha256(path),'cells',17,self.root/'out')
        self.assertFalse((self.root/'out').exists())


if __name__=='__main__':unittest.main()
