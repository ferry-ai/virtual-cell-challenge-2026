"""The floor on the responder probability (1/10: the identity arm of rlab-cellnet-r3 collapsed to pi = 1e-10, after
which its shift had no gradient): pi stays in [floor, 1 - floor], the shift keeps a gradient when the responder head
is saturated at zero, and without the option the model is the one of the earlier trainings.

    python -m unittest test_pi_floor -v          (from this folder, with the project venv)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402


def saturated(pi_floor):
    import torch
    torch.manual_seed(0)
    m = CN.build_model(30, 5, 1, 1, np.arange(8), dim=8, rank=4, target_code="identity", pi_floor=pi_floor)
    with torch.no_grad():
        m.pi_head.bias.fill_(-1000.0)                 # the responder head saturated at zero, as after the collapse
        m.delta_out.weight.normal_(0, 0.1)
    z, beta = torch.randn(6, 8), torch.randn(6, 30)
    delta, pi = m(z, beta, torch.arange(6) % 5, torch.full((6,), -1), torch.zeros(6, dtype=torch.long))
    x = torch.poisson(torch.full((6, 30), 3.0))
    lib, mask, theta = x.sum(-1), torch.ones(6, 30, dtype=torch.bool), torch.full((6, 30), 5.0)
    ll0 = CN.cell_loglik(x, lib, beta, mask, theta)
    ll1 = CN.cell_loglik(x, lib, beta + delta, mask, theta)
    mix = torch.logsumexp(torch.stack([torch.log(pi.clamp_min(1e-6)) + ll1,
                                       torch.log((1 - pi).clamp_min(1e-6)) + ll0]), 0)
    mix.sum().backward()
    return pi.detach(), float(m.delta_out.weight.grad.abs().sum())


class PiFloor(unittest.TestCase):
    def test_floor_bounds_pi_and_keeps_the_shift_learning(self):
        pi, grad = saturated(0.05)
        self.assertTrue(bool((pi >= 0.05 - 1e-7).all() and (pi <= 0.95 + 1e-7).all()))
        self.assertGreater(grad, 1e-4)

    def test_without_floor_the_saturated_head_almost_stops_the_shift(self):
        # the loss clamps pi at 1e-6, so the shift's gradient is not zero but thousands of times smaller
        pi, grad = saturated(0.0)
        _, grad_floor = saturated(0.05)
        self.assertLess(float(pi.max()), 1e-6)
        self.assertGreater(grad_floor, 1000 * grad)


if __name__ == "__main__":
    unittest.main()
