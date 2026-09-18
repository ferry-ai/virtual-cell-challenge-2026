"""Tests for the target- and context-conditioned effect predictors (src/vcc2026/conditioned.py).

Each test pins a way the predictor could produce a plausible wrong number:

* a hand-written gradient that is wrong, so training "works" on the wrong objective;
* a network that cannot represent a context-dependent response, or that ignores the context
  (the ablation it will be judged by must be able to detect that);
* a linear baseline that does not recover a linear gate;
* a neighbour descriptor that leaks the target's own label.
"""

from __future__ import annotations

import gzip
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.conditioned import ConditionedNet, ConditionedRidge, neighbour_mean, string_partners  # noqa: E402


def gated_problem(seed=0, n=400, g=60, d=6):
    """y = y_src on genes with phi0 > 0 (expressed in the query), 0 elsewhere, plus a target term."""
    rng = np.random.default_rng(seed)
    phi = rng.normal(size=(g, 3))
    x = rng.normal(size=(n, d))
    y_src = rng.normal(size=(n, g))
    m = np.ones(n)
    w = rng.normal(size=(d, g)) * 0.3
    y = y_src * (phi[:, 0] > 0)[None, :] + np.tanh(x) @ w
    return x, phi, y_src, m, y


class NetTests(unittest.TestCase):
    def test_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(1)
        x, phi, ys, m, y = gated_problem(n=7, g=5, d=4)
        net = ConditionedNet(4, 5, hidden=6, k=3, gate_hidden=4, seed=2)
        for p in net.p.values():
            p[...] = rng.normal(0, 0.5, p.shape)
        _, g = net.loss_and_grads(x, phi, ys, m, y)
        eps = 1e-6
        for name, arr in net.p.items():
            for idx in list(np.ndindex(arr.shape))[:4]:
                old = arr[idx]
                arr[idx] = old + eps
                lp = np.mean((net.forward(x, phi, ys, m) - y) ** 2)
                arr[idx] = old - eps
                lm = np.mean((net.forward(x, phi, ys, m) - y) ** 2)
                arr[idx] = old
                self.assertAlmostEqual(g[name][idx], (lp - lm) / (2 * eps), places=5, msg=f"{name}{idx}")

    def test_learns_a_context_gate_and_the_ablation_sees_it(self):
        x, phi, ys, m, y = gated_problem()
        rng = np.random.default_rng(3)
        tr, va = np.arange(300), np.arange(300, 400)

        def batches():
            i = rng.choice(tr, 64, replace=False)
            return x[i], phi, ys[i], m[i], y[i]

        net = ConditionedNet(x.shape[1], phi.shape[0], hidden=32, k=8, gate_hidden=16, seed=0)
        net.fit(batches, [(x[va], phi, ys[va], m[va], y[va])], lr=1e-2, l2=0.0, steps=3000, check_every=100,
                patience=10)
        mse = np.mean((net.forward(x[va], phi, ys[va], m[va]) - y[va]) ** 2)
        plain = np.mean((ys[va] - y[va]) ** 2)                # transfer everything, amplitude 1
        wrong = phi[rng.permutation(phi.shape[0])]              # the same genes, another context's state
        ablated = np.mean((net.forward(x[va], wrong, ys[va], m[va]) - y[va]) ** 2)
        self.assertLess(mse, 0.35 * plain)
        self.assertGreater(ablated, 2 * mse)


class RidgeTests(unittest.TestCase):
    def test_recovers_a_linear_gate(self):
        rng = np.random.default_rng(4)
        n, g, d = 200, 40, 5
        phi = rng.normal(size=(g, 3))
        x = rng.normal(size=(n, d))
        ys = rng.normal(size=(n, g))
        m = np.ones(n)
        y = ys * (0.8 + 0.5 * phi[:, 0])[None, :] + x @ rng.normal(size=(d, g))
        r = ConditionedRidge(alpha=1e-6).fit([(x, phi, ys, m, y)])
        np.testing.assert_allclose(r.a, [0.8, 0.5, 0.0, 0.0], atol=0.05)
        self.assertLess(np.mean((r.forward(x, phi, ys, m) - y) ** 2), 0.01)


class DescriptorTests(unittest.TestCase):
    def test_neighbours_never_use_the_targets_own_label(self):
        labels = {"A": np.array([1.0, 0.0]), "B": np.array([0.0, 1.0]), "C": np.array([5.0, 5.0])}
        partners = {"A": {"A", "B"}, "C": {"A", "B", "C"}, "Z": {"Q"}}
        out, n = neighbour_mean(["A", "C", "Z"], partners, labels, 2)
        np.testing.assert_allclose(out[0], [0.0, 1.0])       # A: only B, not itself
        np.testing.assert_allclose(out[1], [0.5, 0.5])       # C: A and B, not its own 5s
        self.assertEqual(list(n), [1, 2, 0])                  # Z has no labelled partner

    def test_string_partners_threshold_and_symmetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            info, links = Path(tmp) / "info.gz", Path(tmp) / "links.gz"
            with gzip.open(info, "wt") as f:
                f.write("#id\tname\tsize\tannot\np1\tA\t1\tx\np2\tB\t1\tx\np3\tC\t1\tx\n")
            with gzip.open(links, "wt") as f:
                f.write("protein1 protein2 combined_score\np1 p2 900\np2 p3 150\n")
            part = string_partners(links, info, min_score=400)
        self.assertEqual(part, {"A": {"B"}, "B": {"A"}})


if __name__ == "__main__":
    unittest.main()
