"""vcc2026.transfer_model: the learned magnitude channel of stage 104."""

import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.multisource import AxisTable  # noqa: E402
from vcc2026.transfer_model import (  # noqa: E402
    FEATURES, detectable_threshold, fit_magnitude_model, gene_priors, match_detectable, mixture_se, own_gene_mask,
    pair_features, percentile, reweight, training_rows,
)


class ReweightTests(unittest.TestCase):
    def test_exponent_zero_is_identity_and_a_flat_magnitude_changes_nothing(self):
        e = np.array([[1.0, -2.0, 0.5]], np.float32)
        np.testing.assert_allclose(reweight(e, np.array([[3.0, 0.1, 9.0]]), 0.0), e)
        np.testing.assert_allclose(reweight(e, np.array([[2.0, 2.0, 2.0]]), 0.5), e)

    def test_genes_the_model_expects_to_move_gain_weight_and_signs_stay(self):
        e = np.array([[1.0, -1.0, 1.0, -1.0]], np.float32)
        out = reweight(e, np.array([[4.0, 0.0, 1.0, 1.0]]), 0.5)      # mean |m| = 1.5
        np.testing.assert_allclose(out, e * np.sqrt(np.array([[4, 0, 1, 1]]) / 1.5), rtol=1e-6)
        self.assertTrue(np.all(np.sign(out[out != 0]) == np.sign(e[out != 0])))

    def test_a_target_with_no_predicted_movement_is_zeroed(self):
        self.assertTrue(np.all(reweight(np.ones((1, 3)), np.zeros((1, 3)), 0.25) == 0))

    def test_kept_entries_keep_weight_one(self):
        e = np.array([[2.0, -1.0, 1.0]], np.float32)
        keep = np.array([[True, False, False]])
        out = reweight(e, np.array([[9.0, 1.0, 2.0]]), 0.5, keep=keep)
        self.assertEqual(float(out[0, 0]), 2.0)
        self.assertAlmostEqual(float(out[0, 1]), -1.0 * np.sqrt(1.0 / 4.0), places=6)

    def test_own_gene_mask_marks_each_targets_gene(self):
        m = own_gene_mask(["B", "Z"], {"A": 0, "B": 1}, 2)
        np.testing.assert_array_equal(m, [[False, True], [False, False]])


class MatchTests(unittest.TestCase):
    def test_the_rescaled_effect_moves_as_many_detectable_genes_as_the_reference(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 0.3, size=(20, 200)).astype(np.float32)
        eff = (ref * rng.uniform(0.1, 3, size=ref.shape)).astype(np.float32) * 0.1
        cpm = np.full(200, 50.0)
        thr = detectable_threshold(cpm)
        gate = cpm >= 5
        out, s = match_detectable(eff, ref, thr, gate)
        med = lambda E: np.median(((np.abs(E) > thr) & gate).sum(axis=1))
        self.assertLessEqual(abs(med(out) - med(ref)), 1.0)
        self.assertGreater(s, 1.0)

    def test_the_offset_stays_outside_the_scale(self):
        rng = np.random.default_rng(2)
        ref = rng.normal(0, 0.3, size=(20, 200)).astype(np.float32)
        off = np.zeros_like(ref)
        off[:, :3] = -1.0                                           # a cis head on three genes
        cpm = np.full(200, 50.0)
        thr, gate = detectable_threshold(cpm), cpm >= 5
        eff = ref * 0.2
        out, s = match_detectable(eff, ref, thr, gate, offset=off)
        np.testing.assert_allclose(out, eff * s + off, rtol=1e-5, atol=1e-6)
        med = lambda E: np.median(((np.abs(E) > thr) & gate).sum(axis=1))
        self.assertLessEqual(abs(med(out) - med(ref)), 1.0)

    def test_threshold_is_four_poisson_sds_of_a_400_cell_mean(self):
        # 50 CPM at 20,000 UMI per cell: mu = 1 count; 4 / sqrt(400 * 1) = 0.2
        self.assertAlmostEqual(float(detectable_threshold(np.array([50.0]))[0]), 0.2)


class FeatureTests(unittest.TestCase):
    def test_percentile_keeps_unmeasured_genes_missing(self):
        p = percentile(np.array([1.0, np.nan, 10.0, 100.0]))
        self.assertTrue(np.isnan(p[1]))
        self.assertLess(p[0], p[2])
        self.assertLess(p[2], p[3])

    def test_mixture_se_follows_the_pooling_weights(self):
        a = AxisTable("a", ["T"], np.array([[1.0]], np.float32), np.array([[1.0]], np.float32),
                      np.array([[0.2]], np.float32), np.array([100]), {})
        b = AxisTable("b", ["T"], np.array([[3.0]], np.float32), np.array([[3.0]], np.float32),
                      np.array([[0.4]], np.float32), np.array([300]), {})
        ra, rb = 100 / 200, 300 / 400
        want = np.sqrt((ra * 0.2) ** 2 + (rb * 0.4) ** 2) / (ra + rb)
        self.assertAlmostEqual(float(mixture_se([a, b], ["T"], 1)[0, 0]), want, places=6)

    def test_gene_priors_leave_excluded_targets_out(self):
        chunk = {"targets": np.array(["P", "X"]), "shrunk": np.array([[1.0, 0.0], [9.0, 9.0]]),
                 "raw": np.array([[4.0, 0.0], [9.0, 9.0]]), "se": np.ones((2, 2))}
        pri = gene_priors([chunk], {"X"}, 2)
        np.testing.assert_allclose(pri["gene_common"], [1.0, 0.0])
        np.testing.assert_allclose(pri["gene_resp"], [1.0, 0.0])     # |z| = 4 >= 3 on gene 0 only

    def test_features_and_training_rows_have_the_declared_shape_and_centred_labels(self):
        rng = np.random.default_rng(1)
        G, targets = 6, ["T1", "T2", "T3"]
        tabs = []
        for name in ("s1", "s2"):
            raw = rng.normal(size=(3, G)).astype(np.float32)
            tabs.append(AxisTable(name, targets, raw, raw, np.full((3, G), 0.5, np.float32), np.full(3, 50), {}))
        col = {f"g{i}": i for i in range(G)}
        F = pair_features(tabs, tabs, [np.full((3, G), 0.5, np.float32)] * 2, targets, col, np.arange(1, G + 1.0),
                          [np.arange(1, G + 1.0)] * 2, {k: np.zeros(G) for k in ("gene_resp", "gene_common", "gene_spread")},
                          np.zeros((3, G)), np.zeros((3, G)), np.array([0]))
        self.assertEqual(set(F), set(FEATURES))
        self.assertTrue(all(np.shape(F[k]) == (3, G) for k in FEATURES))
        y = np.array([[1.0] * G, [2.0] * G, [3.0] * G], np.float32)
        X, yc, w = training_rows(F, y, np.ones(G, np.float32), 100, rng)
        self.assertEqual(X.shape, (3 * G, len(FEATURES)))
        np.testing.assert_allclose(np.sort(np.unique(yc)), [-1.0, 0.0, 1.0])   # centred per gene over targets
        *_, rows = training_rows(F, y, np.ones(G, np.float32), 100, rng, with_rows=True)
        np.testing.assert_array_equal(np.bincount(rows), [G, G, G])

    def test_held_out_targets_cannot_move_training_features_when_centred_on_training_targets(self):
        # the audit of 26/09 (reports/audit_piani_dati_2026-09-26/, section 4.1): a source's common
        # response computed over every target lets a held-out target's value reach a training row
        G, col = 3, {"g0": 0, "g1": 1, "g2": 2}

        def feats(test_value, centre_on):
            raw = np.array([[1.0, 0.5, -0.2], [test_value, 1.0, 0.3]], np.float32)
            tab = AxisTable("s", ["train", "test"], raw, raw, np.full((2, G), 0.5, np.float32), np.array([80, 80]), {})
            return pair_features([tab], [tab], [np.full((1, G), 0.5, np.float32)], ["train"], col, np.ones(G),
                                 [np.ones(G)], {k: np.zeros(G) for k in ("gene_resp", "gene_common", "gene_spread")},
                                 np.zeros((1, G)), np.zeros((1, G)), np.array([], dtype=int), centre_on=centre_on)

        a, b = feats(2.0, ["train"]), feats(12.0, ["train"])
        for k in FEATURES:
            np.testing.assert_array_equal(np.asarray(a[k]), np.asarray(b[k]), err_msg=k)
        self.assertFalse(np.array_equal(feats(2.0, None)["m_shr"], feats(12.0, None)["m_shr"]))


class FitTests(unittest.TestCase):
    def test_grouped_early_stopping_holds_out_whole_groups(self):
        rng = np.random.default_rng(3)
        X = rng.normal(size=(4000, 3)).astype(np.float32)
        y = (X[:, 0] + rng.normal(0, 0.1, 4000)).astype(np.float32)
        model = fit_magnitude_model(X, y, np.ones(4000, np.float32), 0, groups=np.repeat(np.arange(40), 100))
        self.assertGreaterEqual(model.n_iter_, 1)
        self.assertGreater(np.corrcoef(model.predict(X), X[:, 0])[0, 1], 0.9)


if __name__ == "__main__":
    unittest.main()
