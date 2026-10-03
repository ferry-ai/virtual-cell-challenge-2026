"""The responder gate (version 2): log-weights from the gate's logit, with or without a floor on pi.

- The counterexample of the audit of r3 (reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md): with pi = 1e-8, a
  response component better than the baseline (log-likelihoods -1 and -2), the clamped formula of version 1 gives a
  descent step that closes the gate further; the log-sigmoid formula reopens it.
- The floor still bounds pi and keeps the shift learning when the responder head is saturated at zero.

    python -m unittest test_pi_floor -v          (from this folder, with the project venv)
"""
from __future__ import annotations

import math
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
    delta, gate = m(z, beta, torch.arange(6) % 5, torch.full((6,), -1), torch.zeros(6, dtype=torch.long))
    x = torch.poisson(torch.full((6, 30), 3.0))
    lib, mask, theta = x.sum(-1), torch.ones(6, 30, dtype=torch.bool), torch.full((6, 30), 5.0)
    ll0 = CN.cell_loglik(x, lib, beta, mask, theta)
    ll1 = CN.cell_loglik(x, lib, beta + delta, mask, theta)
    mix = CN.mixture_loglik(gate, ll1, ll0, pi_floor)
    mix.sum().backward()
    return m.pi_of(gate).detach(), float(m.delta_out.weight.grad.abs().sum())


class Gate(unittest.TestCase):
    def test_counterexample_of_the_audit_reopens_the_gate(self):
        import torch
        logit = torch.tensor([math.log(1e-8 / (1 - 1e-8))], dtype=torch.float64, requires_grad=True)
        ll1, ll0 = torch.tensor([-1.0], dtype=torch.float64), torch.tensor([-2.0], dtype=torch.float64)
        # version 1: log(pi.clamp_min(1e-6)) has zero derivative below the clamp
        pi = torch.sigmoid(logit)
        old = -torch.logsumexp(torch.stack([torch.log(pi.clamp_min(1e-6)) + ll1,
                                            torch.log((1 - pi).clamp_min(1e-6)) + ll0]), 0).sum()
        g_old, = torch.autograd.grad(old, logit)
        new = -CN.mixture_loglik(logit, ll1, ll0).sum()
        g_new, = torch.autograd.grad(new, logit)
        self.assertGreater(float(g_old), 0.0)          # a descent step lowers the logit: the gate closes further
        self.assertLess(float(g_new), 0.0)             # a descent step raises it: the better response reopens it
        self.assertAlmostEqual(float(g_new), -(math.e - 1) * 1e-8, delta=1e-12)

    def test_log_weights_match_the_probabilities(self):
        import torch
        z = torch.linspace(-60, 60, 121, dtype=torch.float64)
        for floor in (0.0, 0.05):
            lp, lq = CN.gate_logs(z, floor)
            pi = floor + (1 - 2 * floor) * torch.sigmoid(z)
            one_minus = floor + (1 - 2 * floor) * torch.sigmoid(-z)     # 1 - pi without cancellation
            self.assertTrue(torch.allclose(torch.exp(lp), pi, rtol=1e-12, atol=1e-300))
            self.assertTrue(torch.allclose(torch.exp(lq), one_minus, rtol=1e-12, atol=1e-300))
            self.assertTrue(bool(torch.isfinite(lp).all() and torch.isfinite(lq).all()))

    def test_floor_bounds_pi_and_keeps_the_shift_learning(self):
        pi, grad = saturated(0.05)
        self.assertTrue(bool((pi >= 0.05 - 1e-7).all() and (pi <= 0.95 + 1e-7).all()))
        self.assertGreater(grad, 1e-4)

    def test_without_floor_the_saturated_head_almost_stops_the_shift(self):
        # pi = sigmoid(-1000): the shift's gradient through pi * exp(ll1) vanishes, with or without a clamp
        pi, grad = saturated(0.0)
        _, grad_floor = saturated(0.05)
        self.assertLess(float(pi.max()), 1e-6)
        self.assertGreater(grad_floor, 1000 * grad)


class DeltaBound(unittest.TestCase):
    def test_shifts_stay_within_the_bound_and_keep_a_gradient(self):
        import torch
        torch.manual_seed(0)
        m = CN.build_model(30, 5, 1, 1, np.arange(8), dim=8, rank=4, target_code="identity", delta_bound=6.0)
        with torch.no_grad():
            m.delta_out.weight.normal_(0, 50.0)          # a raw shift far beyond the bound, as in the pilot r1
        z, beta = torch.randn(6, 8), torch.randn(6, 30)
        delta, _ = m(z, beta, torch.arange(6) % 5, torch.full((6,), -1), torch.zeros(6, dtype=torch.long))
        self.assertLessEqual(float(delta.abs().max()), 6.0 + 1e-5)
        delta.sum().backward()
        self.assertGreater(float(m.delta_out.weight.grad.abs().sum()), 0.0)
        m0 = CN.build_model(30, 5, 1, 1, np.arange(8), dim=8, rank=4, target_code="identity")
        self.assertEqual(m0.delta_bound, 0.0)


if __name__ == "__main__":
    unittest.main()
