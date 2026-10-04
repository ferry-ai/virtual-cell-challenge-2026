"""Tiny CPU invariants, not biological validation or a training benchmark."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

from graph_adapter import ContextGraph, GraphCellNet

ROOT = Path(__file__).resolve().parents[3]
BASE_DIR = ROOT / 'reports/modelli/ibrido_selettivo_2026-10-04'
sys.path.insert(0, str(BASE_DIR))
spec = importlib.util.spec_from_file_location('gears_audit_cellnet_v5', BASE_DIR / 'cellnet.py')
cellnet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cellnet
spec.loader.exec_module(cellnet)


class GraphTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17)
        torch.set_num_threads(1)
        self.features = torch.tensor([[1., 0., .5], [0., 1., .3], [1., 1., .2], [0., 0., 0.]])
        self.edges = torch.tensor([[0, 1, 2], [1, 0, 1]])
        self.weights = torch.tensor([1., .5, .7])

    def graph(self, active=True):
        g = ContextGraph(self.features, self.edges, self.weights, 4, 4)
        if active:
            with torch.no_grad():
                g.message_out.weight.copy_(torch.eye(4))
        return g

    def test_zero_initial_message_and_isolated_fallback(self):
        z = torch.randn(4, 4)
        self.assertTrue(torch.equal(self.graph(False)(z, torch.arange(4)), torch.zeros(4, 4)))
        self.assertTrue(torch.equal(self.graph()(z[2:], torch.tensor([2, 3])), torch.zeros(2, 4)))

    def test_context_changes_message_and_receives_gradient(self):
        g = self.graph()
        z = torch.tensor([[1., 2., 3., 4.], [-1., -2., -3., -4.]], requires_grad=True)
        out = g(z, torch.tensor([0, 0]))  # node 0 has one incoming edge
        self.assertGreater(float((out[0] - out[1]).detach().abs().max()), 1e-5)
        out.square().sum().backward()
        self.assertGreater(float(z.grad.abs().sum()), 0.)

    def test_batch_order_and_composition_invariance(self):
        g = self.graph().eval()
        z, idx = torch.randn(4, 4), torch.tensor([0, 1, 0, 3])
        batched = g(z, idx)
        singles = torch.cat([g(z[i:i+1], idx[i:i+1]) for i in range(4)])
        torch.testing.assert_close(batched, singles)
        p = torch.tensor([2, 0, 3, 1])
        torch.testing.assert_close(g(z[p], idx[p]), batched[p])

    def test_node_relabeling_equivariance(self):
        g = self.graph()
        permutation = torch.tensor([2, 0, 1, 3])  # keep sentinel last
        inverse = torch.argsort(permutation)
        other = ContextGraph(self.features[permutation], inverse[self.edges], self.weights, 4, 4)
        for name, parameter in g.named_parameters():
            dict(other.named_parameters())[name].data.copy_(parameter.data)
        z, idx = torch.randn(3, 4), torch.tensor([0, 1, 2])
        torch.testing.assert_close(g(z, idx), other(z, inverse[idx]))

    def test_reject_bad_graph_and_preserve_all_nodes(self):
        for edges, weights in [(torch.tensor([[0], [3]]), [1.]),
                               (torch.tensor([[0], [0]]), [1.]),
                               (torch.tensor([[0, 0], [1, 1]]), [1., 1.]),
                               (torch.tensor([[0], [1]]), [-1.])]:
            with self.assertRaises(ValueError):
                ContextGraph(self.features, edges, weights, 4, 4)
        self.assertEqual(len(self.graph().features), 4)

    def base(self):
        return cellnet.build_model(n_genes=5, input_genes=np.arange(3), n_targets=3,
                    n_modalities=2, n_studies=1, dim=4, rank=2,
                    target_desc=self.features.numpy(), target_code='descriptors',
                    anchor_rank=2, anchor_U=np.ones((5, 2), dtype=np.float32),
                    gain_mode='fixed', common_head=True)

    def args(self):
        return (torch.randn(3, 4), torch.randn(3, 5), torch.tensor([0, 1, 2]),
                torch.tensor([0, 1, -1]), torch.tensor([0, 1, 0]),
                torch.randn(3, 5), torch.randn(3, 2))

    def test_real_cellnet_zero_graph_parity_with_nonzero_residual(self):
        base = self.base().eval()
        with torch.no_grad():
            base.delta_out.weight.normal_()
            base.delta_out.bias.normal_()
        wrapped = GraphCellNet(base, self.graph(False)).eval()
        args = self.args()
        for original, actual in zip(base(*args), wrapped(*args)):
            torch.testing.assert_close(original, actual, rtol=0, atol=0)

    def test_frozen_anchor_parity_and_state_roundtrip(self):
        model = GraphCellNet(self.base(), self.graph()).eval()
        args = self.args()
        torch.testing.assert_close(model(*args)[0], args[5], rtol=0, atol=0)
        with torch.no_grad():
            model.base.delta_out.weight.normal_()
        result = model(*args)
        restored = GraphCellNet(self.base(), self.graph(False)).eval()
        restored.load_state_dict(model.state_dict())
        for x, y in zip(result, restored(*args)):
            torch.testing.assert_close(x, y, rtol=0, atol=0)


if __name__ == '__main__':
    unittest.main()
