"""guards.py on cases with known answers (PROTOCOLLO.md §3 and §5).

    python -m unittest test_guards -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guards as GD  # noqa: E402


def sums(shifts, base, n):
    """Sums over n cells of proportions whose log ratio to `base` is `shift` (renormalised)."""
    p = base * np.exp(shifts)
    p /= p.sum(-1, keepdims=True)
    return p * n


class Guards(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.P, self.G = 8, 300
        base = rng.dirichlet(np.ones(self.G) * 3)
        self.base = np.tile(base, (self.P, 1))
        self.true = rng.normal(0, 0.5, (self.P, self.G))
        self.anchor = 0.6 * self.true + rng.normal(0, 0.3, (self.P, self.G))
        self.n = np.full(self.P, 50.0)
        self.keys = ["k1"] * 4 + ["k2"] * 4
        self.mask = np.ones((self.P, self.G), bool)

    def run_check(self, pred):
        obs = sums(self.true, self.base, self.n[:, None])
        pm = sums(pred, self.base, self.n[:, None])
        pa = sums(self.anchor, self.base, self.n[:, None])
        pb = self.base * self.n[:, None]
        return GD.check(obs, pm, pa, pb, self.n, self.keys, self.base, self.mask, min_cells=20, min_pairs=3)

    def test_network_equal_to_anchor(self):
        m = self.run_check(self.anchor)
        self.assertAlmostEqual(m["ratio"], 0.0, places=6)
        self.assertAlmostEqual(m["rank_diff"], 0.0, places=6)
        self.assertAlmostEqual(m["benefit"], 0.0, places=6)
        self.assertEqual(GD.breaches(m), [])

    def test_perfect_network_beats_the_anchor(self):
        m = self.run_check(self.true)
        self.assertGreater(m["benefit"], 0.1)
        self.assertLessEqual(m["rank_N"], m["rank_A"])
        self.assertEqual(m["rank_N"], 0.0)

    def test_common_shift_is_caught(self):
        rng = np.random.default_rng(1)
        common = rng.normal(0, 1.5, self.G)
        m = self.run_check(self.anchor + common[None, :])
        self.assertGreater(m["common_share"], 0.9)
        self.assertGreater(m["ratio"], 1.0)
        self.assertIn("common", GD.breaches(m))
        self.assertIn("ratio", GD.breaches(m))

    def test_a_shuffled_network_loses_discrimination(self):
        pred = self.anchor[[1, 2, 3, 0, 5, 6, 7, 4]] * 3
        m = self.run_check(pred)
        self.assertGreater(m["rank_diff"], 0.05)
        self.assertIn("discrimination", GD.breaches(m))

    def test_too_few_cells(self):
        obs = sums(self.true, self.base, 5.0)
        m = GD.check(obs, obs, obs, self.base * 5, np.full(self.P, 5.0), self.keys, self.base, self.mask, min_cells=20)
        self.assertEqual(m["pairs_used"], 0)
        self.assertEqual(GD.breaches(m), [])

    def test_choose_pairs(self):
        cands = [(f"key{k}", f"S{s}", k, s, 100) for k in range(5) for s in range(60)]
        a = GD.choose_pairs(cands, 0.2, 4, 15)
        b = GD.choose_pairs(list(reversed(cands)), 0.2, 4, 15)
        self.assertEqual(a, b)                                    # independent of the order of the candidates
        self.assertLessEqual(len(a), 15)
        per = {}
        for p in a:
            per[p["key"]] = per.get(p["key"], 0) + 1
            self.assertLess(p["hash"], 0.2)
        self.assertTrue(all(v <= 4 for v in per.values()))
        self.assertEqual([p["hash"] for p in a], sorted(p["hash"] for p in a))


if __name__ == "__main__":
    unittest.main()
