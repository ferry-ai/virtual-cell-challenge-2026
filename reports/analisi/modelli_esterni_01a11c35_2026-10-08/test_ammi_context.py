"""Small CPU fixtures for the proposed contextual correction, never biological scores."""
import unittest
import torch
from ammi_context import ContextCorrection, weighted_masked_loss, export_guard


class ContextCorrectionTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7); torch.set_num_threads(1)
        self.features = torch.randn(8, 5, dtype=torch.float64)
        self.weights = torch.arange(1,9,dtype=torch.float64);self.weights/=self.weights.sum()
        self.mean = self.weights @ self.features
        self.model=ContextCorrection(3,4,self.mean,rank=2,hidden=6).double()
        self.cells=torch.randn(8,5,3,dtype=torch.float64)
        self.observed=torch.ones_like(self.cells,dtype=torch.bool)
        self.valid=torch.ones((8,5),dtype=torch.bool)
        self.available=torch.ones(8,dtype=torch.bool)
        self.anchor=torch.randn(8,4,dtype=torch.float64)

    def run_model(self, model=None, **overrides):
        values=dict(target_features=self.features,available=self.available,cells=self.cells,
                    observed=self.observed,valid=self.valid,anchor=self.anchor)
        values.update(overrides)
        return (model or self.model)(**values)

    def test_zero_parity_and_gradients_after_first_step(self):
        prediction,residual=self.run_model()
        self.assertTrue(torch.equal(prediction,self.anchor));self.assertEqual(float(residual.abs().sum()),0)
        optimizer=torch.optim.SGD(self.model.parameters(),lr=.1)
        truth=self.anchor+torch.randn_like(self.anchor)
        for step in range(2):
            optimizer.zero_grad();prediction,_=self.run_model()
            weighted_masked_loss(prediction,truth,torch.ones_like(truth,dtype=torch.bool),self.weights).backward()
            self.assertGreater(float(self.model.decoder.weight.grad.abs().sum()),0)
            if step:
                self.assertGreater(float(self.model.target_projection.weight.grad.abs().sum()),0)
                self.assertGreater(float(self.model.cell_encoder[0].weight.grad.abs().sum()),0)
            optimizer.step()

    def test_reference_center_is_weighted_and_batch_independent(self):
        torch.nn.init.normal_(self.model.decoder.weight)
        shared=self.cells[:1].expand_as(self.cells)
        _,r=self.run_model(cells=shared)
        torch.testing.assert_close(self.weights @ r,torch.zeros(4,dtype=r.dtype),atol=1e-12,rtol=0)
        single,_=self.run_model(target_features=self.features[:1],available=self.available[:1],
            cells=shared[:1],observed=self.observed[:1],valid=self.valid[:1],anchor=self.anchor[:1])
        full,_=self.run_model(cells=shared)
        torch.testing.assert_close(single,full[:1],atol=1e-12,rtol=0)

    def test_cells_differ_with_same_mean_and_are_permutation_invariant(self):
        a=torch.tensor([[[-2.,0,0],[2.,0,0]]],dtype=torch.float64)
        b=torch.zeros_like(a); mask=torch.ones_like(a,dtype=torch.bool);valid=torch.ones((1,2),dtype=torch.bool)
        self.assertFalse(torch.allclose(self.model.encode_controls(a,mask,valid),self.model.encode_controls(b,mask,valid)))
        torch.testing.assert_close(self.model.encode_controls(a,mask,valid),self.model.encode_controls(a.flip(1),mask,valid))
        self.model.context_mode='mean'
        torch.testing.assert_close(self.model.encode_controls(a,mask,valid),self.model.encode_controls(b,mask,valid))

    def test_missing_target_falls_back_and_masked_nan_does_not_learn(self):
        torch.nn.init.normal_(self.model.decoder.weight)
        features=self.features.clone();features[0]=float('nan');available=self.available.clone();available[0]=False
        prediction,residual=self.run_model(target_features=features,available=available)
        self.assertTrue(torch.equal(prediction[0],self.anchor[0]));self.assertEqual(float(residual[0].abs().sum()),0)
        truth=prediction.detach().clone();truth[0]=float('nan');mask=torch.ones_like(truth,dtype=torch.bool);mask[0]=False
        self.assertEqual(float(weighted_masked_loss(prediction,truth,mask,self.weights)),0)

    def test_checkpoint_and_export_guard(self):
        clone=ContextCorrection(3,4,self.mean,rank=2,hidden=6).double();clone.load_state_dict(self.model.state_dict())
        torch.testing.assert_close(self.run_model(clone)[0],self.run_model()[0])
        a=torch.ones((8,4));mask=torch.ones_like(a,dtype=torch.bool)
        self.assertTrue(export_guard(a,torch.zeros_like(a),mask,['c']*8)[0]['pass'])
        with self.assertRaises(ValueError):export_guard(a,a*.1,mask,['c']*8)
        r=torch.ones_like(a);r[::2]=-1
        with self.assertRaises(ValueError):export_guard(a,r,mask,['c']*8)

    def test_no_observed_controls_fails_closed(self):
        with self.assertRaises(ValueError):self.run_model(valid=torch.zeros_like(self.valid))


if __name__=='__main__':unittest.main()
