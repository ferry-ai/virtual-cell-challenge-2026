import gzip, hashlib, json, tempfile, unittest
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch
from torch import nn
from sample_reader import BIO, sha
from population_parts_v1 import PopulationParts
from trainer_stream_v1 import StreamFit


def bank(root,rows,means,partition=None):
    root.mkdir(); rows.to_csv(root/'rows.csv',index=False)
    np.savez_compressed(root/'mean_proportion.npz',value=np.asarray(means,np.float32))
    np.savez_compressed(root/'mask.npz',value=np.ones((len(rows),3),bool))
    np.savez_compressed(root/'sampled_controls.npz',**{str(i):np.asarray(means[i]) for i,r in rows.iterrows() if r.target=='NTC'})
    files={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in root.iterdir()}
    receipt={'complete':True,'unit':'u','rows':len(rows),'cells_used':int(rows.n.sum()),
             'cells_in':int(rows.n.sum()),'source_verification':'source','files':files}
    if partition: receipt['partition']=partition
    (root/'complete.json').write_text(json.dumps(receipt))
    return sha(root/'complete.json')


class FitTests(unittest.TestCase):
    def rows(self):
        return pd.DataFrame({'study':['s']*2,'context':['c']*2,'donor_or_clone':['d']*2,
            'condition':['rest']*2,'modality':['CRISPRi']*2,'chemistry':['flex']*2,
            'target':['G1','NTC'],'line_group':['line']*2,'n':[1,1]})

    def test_control_in_other_part_and_incomplete_union_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); rows=self.rows(); means=[[.7,.2,.1],[.2,.4,.4]]
            keys=[tuple(str(r[c]) for c in (*BIO,'target')) for _,r in rows.iterrows()]
            proof={'parts':2,'global_rows':2,'global_cells':2,'method':'sorted_complete_BIO_target_round_robin_v1',
                   'all_keys_sha256':hashlib.sha256(json.dumps(sorted(keys),separators=(',',':')).encode()).hexdigest()}
            parts=[]
            for i in range(2):
                p=root/str(i); parts.append((p,bank(p,rows.iloc[[i]].reset_index(drop=True),[means[i]],{**proof,'part':i})))
            with self.assertRaisesRegex(ValueError,'incomplete partition'): PopulationParts(parts[:1])
            reader=PopulationParts(parts); b=list(reader.batches())[0]
            np.testing.assert_allclose(b['control_mean'],[means[1]])
            self.assertEqual(b['metadata'].target.tolist(),['G1'])
            (parts[0][0]/'mean_proportion.npz').write_bytes(b'excluded')
            held=PopulationParts(parts,held_groups=['line'])
            self.assertEqual(list(held.batches()),[])

    def test_actual_update_sample_consumption_and_resume_unique_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); rows=self.rows(); br=root/'bank'; sr=root/'sample';sr.mkdir()
            digest=bank(br,rows,[[.7,.2,.1],[.2,.4,.4]])
            rows.to_csv(sr/'bank_rows.csv',index=False)
            np.savez_compressed(sr/'mask.npz',value=np.ones((2,3),bool))
            sp.save_npz(sr/'shard_00000.npz',sp.csr_matrix([[7,2,1],[2,4,4]]))
            with gzip.open(sr/'shard_00000.jsonl.gz','wt') as f:
                for i in range(2): f.write(json.dumps({'bank_row':i,'cell_key':str(i),'stratum':['rep'],
                           'probabilities':{'64':1}})+'\n')
            files={f.name:{'bytes':f.stat().st_size,'sha256':sha(f),'cells':2} for f in sr.iterdir()}
            (sr/'complete.json').write_text(json.dumps({'complete':True,'unit':'u','genes':3,
                                'bank_receipt_sha256':digest,'files':files}))
            lock=root/'lock.json'; lock.write_text(json.dumps({'units':{'u':{
                'bank':{'state':'remote_complete_manifest_checked','receipt_sha256':digest},
                'samples':{'state':'remote_complete_manifest_checked','receipt_sha256':sha(sr/'complete.json')}}}}))
            ctx=json.dumps([str(rows.iloc[0][c]) for c in BIO],separators=(',',':'))
            context={'context_id':ctx,'role':'supervision','state':'ready','group':'line','artifacts':[{'path':'bank'}],
                'gene_axis_sha256':'axis','source_receipt_sha256':'source','cells_admitted':2,'cells_sampled':2,
                'target_count':1,'stratum_count':1,'target_ids':['G1'],'strata_by_target':{'G1':['["rep"]']},
                'split_cells_sampled':1}
            manifest={'contexts':[context],'catalogue_records':[{'record_id':'r','role':'supervision',
                       'evidence':'fixture','context_ids':[ctx]}]}
            mounts={'u':[{'lock_unit':'u','bank_root':br,'samples':[{'lock_unit':'u','root':sr}]}]}
            session=StreamFit(manifest,['r'],lock,sha(lock),mounts)
            class Model(nn.Module):
                def __init__(self): super().__init__(); self.r=nn.Parameter(torch.zeros(3))
                def forward(self,a,t,c,m): return self.r.expand_as(a)
            class Features:
                def verify(self,identity): self.checked=True
                def __call__(self,u,p,ix,meta,basal,mask):
                    return np.zeros_like(basal),np.ones((len(ix),1)),np.ones((len(ix),1))
            model=Model(); opt=torch.optim.SGD(model.parameters(),lr=.1); feat=Features()
            session.fit_epoch(model,opt,feat,lambda m:np.ones(len(m)))
            self.assertTrue(feat.checked); self.assertGreater(float(model.r.detach().abs().sum()),0)
            saved=json.loads(json.dumps(session.accept()))
            resumed=StreamFit(manifest,['r'],lock,sha(lock),mounts); resumed.restore(saved)
            resumed.fit_epoch(model,opt,feat,lambda m:np.ones(len(m)))
            result=resumed.accept()['exposure'][ctx]
            self.assertEqual(len(result['cells']),1);self.assertEqual(len(result['controls']),1)
            self.assertGreater(result['loss_weight_sum'],saved['exposure'][ctx]['loss_weight_sum'])
            saved['identity']['lock_sha256']='other'
            with self.assertRaisesRegex(ValueError,'resume release'): resumed.restore(saved)


if __name__=='__main__': unittest.main()
