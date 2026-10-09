"""Small CPU counterexamples for frozen AMMI pilot invariants."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
import torch

from ammi_contract_v2 import (lineage_weights, row_objective, consumption,
                              swapped_contexts, final_diagnostics, export_residual)
from pie_adapter import sha256


class ContractTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_many_contexts_cannot_increase_lineage_mass(self):
        contexts = ['a1']*7 + ['a2'] + ['b1']*2
        lineages = ['A']*8 + ['B']*2
        w = lineage_weights(contexts, lineages)
        self.assertAlmostEqual(w[:8].sum(), .5)
        self.assertAlmostEqual(w[8:].sum(), .5)
        self.assertAlmostEqual(w[:7].sum(), .25)
        order = list(reversed(range(10)))
        receipt = consumption(order, contexts, lineages, w, [1.]*10)
        self.assertEqual([r['seen_rows'] for r in receipt['lineage']], [8,2])
        for r in receipt['lineage']:
            self.assertAlmostEqual(r['expected_mass'], r['consumed_mass'])
        with self.assertRaises(ValueError): consumption([0]*10, contexts, lineages, w, [1.]*10)
        with self.assertRaises(ValueError): lineage_weights(['a','a'], ['A','B'])

    def test_unequal_masks_and_batches_do_not_change_global_objective(self):
        prediction = torch.tensor([[1.,float('nan')],[2.,2.],[3.,3.]], requires_grad=True)
        response = torch.zeros_like(prediction)
        observed = torch.tensor([[True,False],[True,True],[True,True]])
        weights = torch.tensor([.25,.25,.5])
        full, pieces = row_objective(prediction,response,observed,weights,3)
        self.assertAlmostEqual(float(full.detach()), .25+1+4.5)
        b1,_=row_objective(prediction[:2],response[:2],observed[:2],weights[:2],3)
        b2,_=row_objective(prediction[2:],response[2:],observed[2:],weights[2:],3)
        torch.testing.assert_close(full, b1*2/3+b2/3)
        full.backward()
        self.assertEqual(float(prediction.grad[0,1]), 0)
        self.assertTrue(torch.isfinite(prediction.grad).all())
        with self.assertRaises(ValueError):
            row_objective(prediction,response,torch.zeros_like(observed),weights,3)

    def test_swap_never_uses_same_lineage_and_is_query_order_independent(self):
        refs={'a1':'A','a2':'A','b1':'B','c1':'C'}
        contexts=['a1','b1','outer']; lineages=['A','B','Z']
        result=swapped_contexts(contexts,lineages,refs)
        for source,lineage in zip(result,lineages): self.assertNotEqual(refs[source],lineage)
        self.assertEqual(result[::-1],swapped_contexts(contexts[::-1],lineages[::-1],refs))
        self.assertEqual(result[0],swapped_contexts(contexts[:1],lineages[:1],refs)[0])
        with self.assertRaises(ValueError): swapped_contexts(['a'],['A'],{'a':'A'})

    def test_whole_prediction_common_share_reported_without_new_threshold(self):
        a=torch.ones((4,2),dtype=torch.float64)
        r=torch.tensor([[.1,-.1],[-.1,.1],[.1,-.1],[-.1,.1]],dtype=torch.float64)
        report=final_diagnostics(a,r,torch.ones_like(a,dtype=torch.bool),['x']*4)[0]
        self.assertTrue(report['pass'])
        self.assertEqual(report['anchor_common_share'],1)
        self.assertGreater(report['prediction_common_share'],.9)
        self.assertIsNone(report['whole_prediction_threshold'])

    def test_export_zero_is_byte_identical_and_nonzero_has_unchanged_axes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); anchor=root/'anchor.npz'
            a=np.asarray([[1,-0.],[-1,0.],[1,0.],[-1,0.]],dtype=np.float32)
            mask=np.ones_like(a,dtype=bool); genes=['g1','g2']; targets=['t1','t2','t3','t4']
            np.savez_compressed(anchor,lfc=a,observed=mask,targets=targets,genes=genes,extra=np.asarray('pinned'))
            digest=sha256(anchor)
            receipt=export_residual(anchor,digest,np.zeros_like(a),mask,targets,genes,root/'zero.npz','x')
            self.assertTrue(receipt['byte_parity'])
            self.assertEqual(anchor.read_bytes(),(root/'zero.npz').read_bytes())
            r=a*.1
            receipt=export_residual(anchor,digest,r,mask,targets,genes,root/'changed.npz','x')
            self.assertFalse(receipt['zero_residual'])
            with np.load(root/'changed.npz') as exported:
                np.testing.assert_allclose(exported['lfc'],a+r)
                self.assertEqual(exported['extra'].item(),'pinned')
            with self.assertRaises(ValueError):
                export_residual(anchor,'0'*64,r,mask,targets,genes,root/'bad.npz','x')
            with self.assertRaises(ValueError):
                export_residual(anchor,digest,r,mask,targets[::-1],genes,root/'bad.npz','x')
            with self.assertRaises(ValueError):
                export_residual(anchor,digest,np.ones_like(a),mask,targets,genes,root/'bad.npz','x')
            self.assertFalse((root/'bad.npz').exists())


if __name__=='__main__': unittest.main()
