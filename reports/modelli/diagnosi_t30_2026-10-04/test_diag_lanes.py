"""Tests of the effect arithmetic of diag_lanes.py on synthetic arrays (no cube, no scorer).

    .\\scripts\\py.cmd -m unittest reports/modelli/diagnosi_t30_2026-10-04/test_diag_lanes.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diag_lanes as D  # noqa: E402


def synthetic(seed=0, n=40, g=300):
    rng = np.random.default_rng(seed)
    T_all = rng.normal(0, 0.1, (n, g)).astype(np.float32)
    T_prod = (T_all + rng.normal(0, 0.05, (n, g))).astype(np.float32)
    T_all[:, :10] = np.nan                      # genes the anchor does not define
    T_prod[3] = np.nan                          # a target the recipe's sources do not have
    R = (rng.normal(0, 0.03, (n, g)) + rng.normal(0, 0.02, (1, g))).astype(np.float32)
    R[5, 20:40] = np.nan
    w = rng.uniform(0.1, 0.5, n)
    return T_all, T_prod, R, w


class EffectArms(unittest.TestCase):
    def setUp(self):
        self.T_all, self.T_prod, self.R, self.w = synthetic()
        self.eff, self.diag = D.build_effects(self.T_all, self.T_prod, self.R, self.w, 0.65)

    def test_parity_arm_is_the_baseline_bit_for_bit(self):
        self.assertTrue(np.array_equal(self.eff["all_w0"], self.T_all.astype(np.float64), equal_nan=True))

    def test_bench_case_is_the_hybrid_of_the_original_lane(self):
        self.assertTrue(np.array_equal(self.eff["all_wR"], D.HL.hybrid(self.T_all, self.R, self.w), equal_nan=True))

    def test_specific_plus_common_is_the_whole_correction_where_the_anchor_is_defined(self):
        ok = np.isfinite(self.T_all)
        whole = self.eff["all_wR"] - self.T_all
        parts = (self.eff["all_wRspec"] - self.T_all) + (self.eff["all_wRcom"] - self.T_all)
        np.testing.assert_allclose(parts[ok], whole[ok], atol=2e-7)

    def test_specific_part_has_no_common_component_and_dose_reaches_the_requested_share(self):
        spec, com = D.split_common(self.R, np.isfinite(self.T_all))
        self.assertLess(D.common_share(spec), 1e-10)
        self.assertAlmostEqual(self.diag["common_share_dose"], 0.65, places=4)
        self.assertGreater(self.diag["dose_factor"], 0)

    def test_arms_keep_the_support_of_their_baseline(self):
        for name, lfc in self.eff.items():
            base = self.T_all if name.startswith("all") else self.T_prod
            self.assertTrue(np.array_equal(np.isfinite(lfc), np.isfinite(base)), name)
        self.assertEqual(self.diag["targets_without_T_prod"], 1)

    def test_x15_scales_the_whole_effect(self):
        ok = np.isfinite(self.T_prod)
        np.testing.assert_allclose(self.eff["prod_wR_x15"][ok], 1.5 * self.eff["prod_wR"][ok], rtol=1e-12)

    def test_a_correction_without_common_component_has_no_dose_arm(self):
        spec, com = D.split_common(self.R, np.isfinite(self.T_all))
        with self.assertRaises(SystemExit):
            D.dose_factor(spec, np.zeros_like(com), 0.65)


if __name__ == "__main__":
    unittest.main()
