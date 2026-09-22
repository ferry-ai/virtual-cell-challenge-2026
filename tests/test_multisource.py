"""Tests for `vcc2026.multisource`.

Each test pins a way a multi-source transfer could return plausible wrong numbers:

* a donor's knockdown compared with another donor's controls (donor effects leak in);
* an unmeasured (target, gene) pair counted as a vote for zero;
* centring that subtracts one source's common response from another;
* a sign-purity proxy that reads the truth's ranking instead of the prediction's.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.multisource import AxisTable, _purity_depth, effects_from_pseudobulk, mix  # noqa: E402
from vcc2026.predictor_sc import SourceEffects  # noqa: E402


def _rows(rng, base, n_cells, scale=1.0):
    lam = base * n_cells * 2000 * scale          # ~2,000 UMI per cell
    return rng.poisson(lam).astype(float)


class PseudobulkEffectTests(unittest.TestCase):
    def test_donor_baselines_cancel_and_the_knockdown_is_found(self):
        rng = np.random.default_rng(0)
        g = 400
        base = rng.gamma(2.0, 1.0, size=g)
        base[7] = 0.01 * base.sum()                 # a well-measured knockdown gene
        base /= base.sum()
        donor_shift = {"d1": np.exp(rng.normal(0, 0.8, g)), "d2": np.exp(rng.normal(0, 0.8, g))}
        rows, meta = [], []
        for d, shift in donor_shift.items():
            prof = base * shift
            prof /= prof.sum()
            for _ in range(20):                     # controls, 20 rows of 100 cells
                rows.append(_rows(rng, prof, 100)); meta.append(("non-targeting", d, 100))
            kd = prof.copy(); kd[7] *= 0.25; kd /= kd.sum()
            for _ in range(2):                      # target rows, only in its own donor mix
                rows.append(_rows(rng, kd, 300)); meta.append(("T1", d, 300))
        obs = pd.DataFrame(meta, columns=["target", "donor", "n_cells"]).assign(condition="Rest")
        src = effects_from_pseudobulk(sp.csr_matrix(np.vstack(rows)), obs, [f"g{i}" for i in range(g)],
                                      targets=["T1", "missing"], condition="Rest")
        self.assertEqual(src.targets, ["T1"])
        self.assertAlmostEqual(float(src.raw[0, 7]), np.log(0.25), delta=0.15)
        others = np.delete(src.raw[0], 7)
        self.assertLess(float(np.median(np.abs(others))), 0.1)   # large donor shifts must cancel


class MixTests(unittest.TestCase):
    def _table(self, name, targets, rows, n):
        rows = np.asarray(rows, dtype=np.float32)
        return AxisTable(name, targets, rows, rows, np.ones_like(rows), np.asarray(n, dtype=float))

    def test_unmeasured_pairs_do_not_vote_zero(self):
        a = self._table("a", ["T"], [[1.0, np.nan, 2.0]], [1e6])
        b = self._table("b", ["T"], [[3.0, 5.0, np.nan]], [1e6])
        eff, w = mix([a, b], ["T"], gamma=0.0)
        np.testing.assert_allclose(eff[0], [2.0, 5.0, 2.0], rtol=1e-4)
        c = self._table("c", ["U"], [[1.0, 1.0, 1.0]], [10])
        eff, w = mix([c], ["T"])
        self.assertTrue((w == 0).all() and (eff == 0).all())

    def test_centring_uses_each_source_own_common_response(self):
        a = self._table("a", ["T", "U"], [[2.0, 0.0], [0.0, 0.0]], [1e9, 1e9])   # common a = [1, 0]
        b = self._table("b", ["T", "U"], [[0.0, 4.0], [0.0, 0.0]], [1e9, 1e9])   # common b = [0, 2]
        eff, _ = mix([a, b], ["T"], gamma=1.0)
        np.testing.assert_allclose(eff[0], [0.5, 1.0], rtol=1e-6)

    def test_reliability_weights_follow_cells(self):
        a = self._table("a", ["T"], [[1.0]], [100])     # reliability 0.5
        b = self._table("b", ["T"], [[4.0]], [300])     # reliability 0.75
        eff, _ = mix([a, b], ["T"], reliability_scale=100.0)
        self.assertAlmostEqual(float(eff[0, 0]), (0.5 * 1 + 0.75 * 4) / 1.25, places=5)


class ShrinkAndShareTests(unittest.TestCase):
    def test_z_shrink_keeps_strong_effects_and_kills_weak_ones(self):
        from vcc2026.multisource import z_shrink
        eff = np.array([-2.46, 0.3, 0.3, 0.0])
        se = np.array([0.2, 0.3, 0.05, 0.1])
        out = z_shrink(eff, se, k=4.0)
        self.assertGreater(abs(out[0]), 0.95 * 2.46)          # z = 12: kept (a single-normal prior crushed it)
        self.assertAlmostEqual(out[1], 0.3 * 1 / 5, places=6)  # z = 1: one fifth
        self.assertAlmostEqual(out[2], 0.3 * 36 / 40, places=6)  # z = 6: nine tenths kept
        self.assertEqual(out[3], 0.0)

    def test_shared_signal_recovers_a_known_split(self):
        from vcc2026.multisource import shared_signal
        rng = np.random.default_rng(3)
        T, G = 60, 500
        s = rng.normal(0, 1.0, (T, G))
        a_rows = s + rng.normal(0, 1.0, (T, G))                # V_a = 1
        b_rows = s + rng.normal(0, 2.0, (T, G))                # V_b = 4
        tg = [f"T{i}" for i in range(T)]
        mk = lambda n, r: AxisTable(n, tg, r.astype(np.float32), r.astype(np.float32),
                                    np.ones_like(r, dtype=np.float32), np.full(T, 1e6))
        out = shared_signal(mk("a", a_rows), mk("b", b_rows), tg)
        self.assertAlmostEqual(out["weight_a"], 0.8, delta=0.03)   # V_b / (V_a + V_b)
        # best amplitude: V_s / (V_s + w^2 V_a + (1-w)^2 V_b) = 1 / (1 + 0.64 + 0.16)
        self.assertAlmostEqual(out["amplitude"], 1 / 1.8, delta=0.03)


class PurityTests(unittest.TestCase):
    def test_depth_is_the_deepest_prefix_at_the_floor(self):
        pred = np.array([1, 1, -1, 1, 1, 1, 1, 1, 1, 1, -1, -1])
        obs = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(_purity_depth(pred, obs, 0.9), 10)        # 9/10 at depth 10
        self.assertEqual(_purity_depth(-obs, obs, 0.9), 0)


if __name__ == "__main__":
    unittest.main()
