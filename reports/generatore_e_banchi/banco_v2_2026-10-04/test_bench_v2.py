"""Tests of bench_v2.py that need no scorer: the per-block random streams, the arm loader, the paired statistics.

    .\\scripts\\py.cmd -m unittest reports/generatore_e_banchi/banco_v2_2026-10-04/test_bench_v2.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_v2 as B  # noqa: E402


class Streams(unittest.TestCase):
    def test_a_block_stream_depends_on_seed_and_target_only(self):
        a = B.block_rng(1, 0, "MTOR").integers(0, 1 << 30, 8)
        self.assertTrue(np.array_equal(a, B.block_rng(1, 0, "MTOR").integers(0, 1 << 30, 8)))
        self.assertFalse(np.array_equal(a, B.block_rng(1, 1, "MTOR").integers(0, 1 << 30, 8)))
        self.assertFalse(np.array_equal(a, B.block_rng(1, 0, "PTEN").integers(0, 1 << 30, 8)))
        self.assertFalse(np.array_equal(a, B.block_rng(2, 0, "MTOR").integers(0, 1 << 30, 8)))

    def test_an_unchanged_target_gives_the_same_cells_when_another_target_changes(self):
        from vcc2026.config import challenge
        rng = np.random.default_rng(0)
        g, labels = 60, ["T1", "T2", "T3"]
        basal = rng.gamma(2.0, 50.0, g)
        libs = rng.integers(2000, 6000, 40)
        lfc = rng.normal(0, 0.3, (3, g)).astype(np.float32)
        obs = np.ones((3, g), bool)
        other = lfc.copy()
        other[0, :30] += 0.8                               # only the first target changes (not a uniform shift)
        ch = challenge()
        one = B.generate(basal, lfc, obs, libs, labels, 25, 7, 0, ch, None)
        two = B.generate(basal, other, obs, libs, labels, 25, 7, 0, ch, None)
        self.assertGreater((one[:25] != two[:25]).nnz, 0)
        self.assertEqual((one[25:] != two[25:]).nnz, 0)
        swapped = B.generate(basal, lfc[::-1], obs, libs, labels[::-1], 25, 7, 0, ch, None)
        self.assertEqual((one[:25] != swapped[50:]).nnz, 0)   # the order of the targets does not matter


class Loader(unittest.TestCase):
    def test_missing_targets_and_genes_are_unobserved_and_values_follow_the_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arm.npz"
            lfc = np.array([[1.0, 2.0, np.nan], [4.0, 5.0, 6.0]], np.float32)
            obs = np.array([[True, False, True], [True, True, True]])
            np.savez(path, targets=np.array(["B", "A"]), genes=np.array(["g2", "g0", "g9"]), lfc=lfc, observed=obs)
            got, mask = B.load_arm(path, ["A", "B", "C"], np.array(["g0", "g1", "g2"]))
        np.testing.assert_array_equal(got[0], [5.0, 0.0, 4.0])
        np.testing.assert_array_equal(mask[0], [True, False, True])
        np.testing.assert_array_equal(got[1], [0.0, 0.0, 1.0])       # g0 not observed for B
        np.testing.assert_array_equal(mask[1], [False, False, True])
        self.assertFalse(mask[2].any())                               # target C is not in the file


class Paired(unittest.TestCase):
    def test_paired_differences_are_taken_at_the_same_seed(self):
        res = {}
        for k, (x, y) in enumerate([(0.30, 0.20), (0.50, 0.41), (0.10, 0.02)]):
            for arm, v in (("a", x), ("b", y)):
                res[f"{arm}@s{k}"] = {"scaled_local": {r: v for r in B.MEMBERS.values()},
                                      "raw": {r: v for r in B.MEMBERS.values()}}
        out = B.paired(res, [("a", "b")], 3)["a:b"]
        np.testing.assert_allclose(out["six"]["values"], [0.10, 0.09, 0.08], atol=1e-12)
        self.assertAlmostEqual(out["six"]["mean"], 0.09)
        self.assertTrue(out["six"]["resolved"])
        self.assertAlmostEqual(out["members"]["PDS"]["sd"], 0.01)


if __name__ == "__main__":
    unittest.main()
