"""Tiny synthetic training tests; no biological RNA or cloud compute."""
import unittest
import numpy as np
import torch
from ammi_train_v2 import fit


class TrainerTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        rng=np.random.default_rng(4)
        self.data=dict(contexts=['a']*6+['b']*2,lineages=['A']*6+['B']*2,
            row_ids=[str(i) for i in range(8)],features=rng.normal(size=(8,5)).astype('float32'),
            response=rng.normal(size=(8,4)).astype('float32'),anchor=np.ones((8,4),dtype='float32'),
            observed=np.ones((8,4),dtype=bool),input_receipt_sha256='fixture',anchor_receipt_sha256='fixture')
        self.controls={c:(rng.normal(size=(3,3)).astype('float32'),np.ones((3,3),dtype=bool)) for c in ['a','b']}

    def test_two_complete_epochs_and_paired_reproducibility(self):
        guard=lambda model,epoch:dict(pass_=True,epoch=epoch,**{'pass':True})
        a,r=fit(self.data,self.controls,['OUTER','INNER'],'cells',17,guard,fixture=True)
        b,s=fit(self.data,self.controls,['OUTER','INNER'],'cells',17,guard,fixture=True)
        self.assertEqual(len(r['epochs']),2)
        for epoch in r['epochs']:
            for lineage in epoch['coverage']['lineage']: self.assertAlmostEqual(lineage['consumed_mass'],.5)
        for k in a.state_dict(): torch.testing.assert_close(a.state_dict()[k],b.state_dict()[k],atol=0,rtol=0)
        self.assertFalse(r['complete_D053'])

    def test_excluded_responses_and_failed_guard_are_rejected(self):
        with self.assertRaises(ValueError): fit(self.data,self.controls,['A'],'none',17,lambda m,e:{'pass':True},fixture=True)
        calls=[]
        def reject(model,epoch): calls.append(epoch); return {'pass':False}
        with self.assertRaises(ValueError): fit(self.data,self.controls,[],'cells',17,reject,fixture=True)
        self.assertEqual(calls,[1])

    def test_none_model_does_not_change_with_control_values(self):
        guard=lambda m,e:{'pass':True}
        a,_=fit(self.data,self.controls,[],'none',29,guard,fixture=True)
        changed={c:(values*50,mask) for c,(values,mask) in self.controls.items()}
        b,_=fit(self.data,changed,[],'none',29,guard,fixture=True)
        for k in a.state_dict(): torch.testing.assert_close(a.state_dict()[k],b.state_dict()[k],atol=0,rtol=0)


if __name__=='__main__': unittest.main()
