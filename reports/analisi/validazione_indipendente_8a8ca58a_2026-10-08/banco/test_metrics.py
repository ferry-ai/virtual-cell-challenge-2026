"""Tests of the level-A measures on synthetic effects: parity with the live library, and the controls.

    .\\scripts\\py.cmd -m unittest reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/test_metrics.py
"""
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "src"))

import metrics as M  # noqa: E402
from vcc2026.multisource import AxisTable, transfer_report  # noqa: E402


def fixture(seed=0, T=40, G=400, noise=0.6):
    rng = np.random.default_rng(seed)
    truth = rng.normal(0, 1, (T, G)) * (rng.random((T, G)) < 0.2) + rng.normal(0, 0.3, G)[None, :]
    se = np.full((T, G), 0.2)
    raw = truth + rng.normal(0, 0.2, (T, G))
    shrunk = raw * 0.8
    for arr in (raw, shrunk, se):
        arr[:, :7] = np.nan                      # genes the truth never measured
    raw[3, 50:60] = shrunk[3, 50:60] = np.nan    # and a few pairs of one target
    pred = 0.5 * truth + rng.normal(0, noise, (T, G))
    observed = rng.random((T, G)) < 0.97
    pred = np.where(observed, pred, 0.0)
    return pred, observed, shrunk.astype(np.float32), raw.astype(np.float32), se.astype(np.float32)


class Parity(unittest.TestCase):
    def test_medians_equal_the_live_transfer_report(self):
        pred, observed, shrunk, raw, se = fixture()
        targets = [f"T{i}" for i in range(pred.shape[0])]
        exclude = [10, 11, 12]
        truth = AxisTable("truth", targets, shrunk, raw, se, np.full(len(targets), 100))
        report = transfer_report(pred, observed.astype(float), truth, targets, exclude_cols=exclude, heads=(10, 50))
        valid = M.valid_pairs(observed, shrunk, raw, se, exclude)
        mine = M.per_target(pred, valid, shrunk, raw, se)
        self.assertEqual(report["targets"], pred.shape[0])
        self.assertEqual(report["genes_shared_by_all"], int(valid.all(axis=0).sum()))
        self.assertAlmostEqual(report["pds_proxy_mean"], float(mine["disc"].mean()), places=12)
        self.assertAlmostEqual(report["median"]["pearson_centred"], float(np.nanmedian(mine["r_spec"])), places=12)
        self.assertAlmostEqual(report["median"]["purity_top50"], float(np.nanmedian(mine["sign50"])), places=12)
        self.assertAlmostEqual(report["median"]["reach_proxy"], float(np.nanmedian(mine["reach"])), places=12)
        self.assertEqual(report["median"]["n_conf"], float(np.median(mine["n_conf"])))


class Controls(unittest.TestCase):
    def setUp(self):
        self.pred, self.observed, self.shrunk, self.raw, self.se = fixture(noise=0.05)
        self.valid = M.valid_pairs(self.observed, self.shrunk, self.raw, self.se, [])

    def test_a_specific_prediction_ranks_its_own_truth_first_and_the_shuffle_does_not(self):
        good = M.per_target(self.pred, self.valid, self.shrunk, self.raw, self.se)
        self.assertGreater(good["disc"].mean(), 0.99)
        perm = M.shuffled_rows(self.pred.shape[0])
        self.assertFalse((perm == np.arange(perm.size)).any())
        valid = M.valid_pairs(self.observed[perm], self.shrunk, self.raw, self.se, [])
        bad = M.per_target(self.pred[perm], valid, self.shrunk, self.raw, self.se)
        self.assertLess(abs(bad["disc"].mean() - 0.5), 0.12)
        self.assertLess(np.nanmean(bad["r_spec"]), 0.1)
        gap = M.paired_bootstrap(good["disc"], bad["disc"])
        self.assertTrue(gap["resolved"] and gap["lo"] > 0)

    def test_the_null_prediction_sits_exactly_at_one_half(self):
        zero = np.zeros_like(self.pred)
        null = M.per_target(zero, self.valid, self.shrunk, self.raw, self.se)
        self.assertTrue(np.allclose(null["disc"], 0.5))
        self.assertTrue(np.allclose(null["mse_ratio"], 1.0))
        self.assertTrue(np.allclose(null["nmae_conf"][np.isfinite(null["nmae_conf"])], 1.0))

    def test_the_mean_only_prediction_has_no_specific_signal(self):
        mean = np.repeat(self.pred.mean(axis=0, keepdims=True), self.pred.shape[0], axis=0)
        flat = M.per_target(mean, self.valid, self.shrunk, self.raw, self.se)
        self.assertLess(abs(flat["disc"].mean() - 0.5), 0.05)
        summary = M.arm_summary(mean, self.valid, self.raw, self.valid.all(axis=0),
                                np.full(mean.shape[0], -1), self.observed)
        self.assertAlmostEqual(summary["common_share_pred"], 1.0, places=9)

    def test_identical_arms_give_a_zero_unresolved_difference(self):
        a = M.per_target(self.pred, self.valid, self.shrunk, self.raw, self.se)
        for m in M.MEASURES:
            r = M.paired_bootstrap(a[m], a[m])
            self.assertEqual(r["mean"], 0.0)
            self.assertFalse(r["resolved"])

    def test_the_bootstrap_is_reproducible_and_the_macro_keeps_the_fold_weighting(self):
        rng = np.random.default_rng(5)
        a, b = rng.normal(0.1, 1, 200), rng.normal(0.0, 1, 200)
        r1, r2 = M.paired_bootstrap(a, b), M.paired_bootstrap(a, b)
        self.assertEqual((r1["lo"], r1["hi"]), (r2["lo"], r2["hi"]))
        small = M.paired_bootstrap(a[:20] + 1.0, b[:20])
        both = M.macro([r1, small])
        self.assertAlmostEqual(both["mean"], (r1["mean"] + small["mean"]) / 2, places=12)
        self.assertEqual(both["folds"], 2)
        self.assertNotIn("boot", M.strip(r1))

    def test_own_gene_pairs_are_read_from_the_declared_columns(self):
        own = np.arange(self.pred.shape[0]) + 20
        s = M.arm_summary(self.pred, self.valid, self.raw, self.valid.all(axis=0), own, self.observed)
        expected = sum(bool(self.observed[i, j]) and bool(np.isfinite(self.raw[i, j])) for i, j in enumerate(own))
        self.assertEqual(s["own_gene"]["pairs"], expected)


if __name__ == "__main__":
    unittest.main()
