"""Controlled small cases for cell_data.py: each property the review of 30/09 asked for, with a known answer.

    python -m unittest test_cell_data -v          (from this folder)
"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cell_data as D  # noqa: E402

AXIS = {"TFAM", "LAT", "GFM1", "A", "B", "C", "D", "MT-CO1"}


class Labels(unittest.TestCase):
    def test_spellings_of_one_gene_meet(self):
        self.assertEqual(D.normalise("TFAM", AXIS), "TFAM")
        self.assertEqual(D.normalise("TFAM_+_60145205.23-P1P2|TFAM_-_60145223.23-P1P2", AXIS), "TFAM")
        self.assertEqual(D.normalise("LAT_2", AXIS), "LAT")
        self.assertEqual(D.normalise("GFM1|x", AXIS), "GFM1")

    def test_unresolved_label_stays_itself(self):
        self.assertEqual(D.normalise("p-sgELF1-2", AXIS), "p-sgELF1-2")
        self.assertEqual(D.normalise("62(mod)_pBA581", AXIS), "62(mod)_pBA581")


class Classes(unittest.TestCase):
    """A in K and H; B only in H; C hidden, in K and H; D hidden, only in K."""

    def setUp(self):
        self.hidden = {"C", "D"}
        self.trained = {"A"}            # perturbed in a training context and not hidden

    def cls(self, ctx, sym, ctrl=False):
        return D.classify(ctx, sym, ctrl, "H", self.hidden, self.trained)

    def test_effective_classes(self):
        self.assertEqual(self.cls("H", "A"), "C")
        self.assertEqual(self.cls("H", "B"), "J")          # never perturbed in training: new target, new context
        self.assertEqual(self.cls("H", "C"), "J")
        self.assertEqual(self.cls("K", "C"), "T")
        self.assertEqual(self.cls("K", "D"), "T")
        self.assertEqual(self.cls("K", "A"), "train")
        self.assertEqual(self.cls("H", "NTC", ctrl=True), "control_holdout")
        self.assertEqual(self.cls("K", "NTC", ctrl=True), "train")

    def test_split_draws_only_trainable_symbols(self):
        where = {"A": {("s1", "K"), ("s1", "H")}, "B": {("s1", "H")}, "C": {("s1", "K")}, "D": {("s2", "K")}}
        hidden, trainable = D.splits(where, "H", 0.5, 7)
        self.assertEqual(set(trainable), {"A", "C", "D"})
        self.assertTrue(hidden <= set(trainable))
        self.assertEqual(len(hidden), 2)
        self.assertEqual(hidden, D.splits(where, "H", 0.5, 7)[0])      # fixed by the seed


class Admission(unittest.TestCase):
    def test_thresholds_from_controls_and_reasons(self):
        rng = np.random.default_rng(0)
        lib = rng.integers(1000, 5000, 1000).astype(float)
        genes = rng.integers(500, 2000, 1000).astype(float)
        mito = rng.uniform(0.0, 0.05, 1000)
        t = D.thresholds_from_controls(lib, genes, mito)
        test_lib = np.array([10.0, 3000, 3000, 3000])
        test_genes = np.array([900.0, 1.0, 900, 900])
        test_mito = np.array([0.01, 0.01, 0.9, 0.01])
        ok, why = D.admit(test_lib, test_genes, test_mito, t)
        self.assertEqual(ok.tolist(), [False, False, False, True])
        self.assertEqual(why.tolist()[:3], ["counts_below_q01_of_controls", "genes_below_q01_of_controls",
                                            "mito_above_q99_of_controls"])

    def test_no_mito_rule_without_mt_genes(self):
        t = D.thresholds_from_controls(np.array([100.0, 200]), np.array([50.0, 60]), np.array([np.nan, np.nan]))
        self.assertIsNone(t["mito_max"])


class Sampling(unittest.TestCase):
    def test_one_epoch_visits_every_cell_once(self):
        shards = [("a", np.arange(0, 37)), ("b", np.arange(100, 111)), ("c", np.arange(500, 580)), ("d", [])]
        s = D.EpochSampler(shards, buffer=2, seed=3)
        seen = Counter()
        total = 37 + 11 + 80
        while sum(seen.values()) < total:
            for sid, r in s.batch(10):
                seen[(sid, r)] += 1
                if sum(seen.values()) == total:
                    break
        self.assertEqual(len(seen), total)
        self.assertEqual(max(seen.values()), 1)
        self.assertIn(s.epoch, (1, 2))                 # the batch that closes epoch 1 may open epoch 2

    def test_two_epochs_visit_every_cell_twice(self):
        shards = [("a", np.arange(0, 23)), ("b", np.arange(100, 131)), ("c", np.arange(500, 507))]
        s = D.EpochSampler(shards, buffer=2, seed=5)
        draws = []
        while len(draws) < 2 * 61:
            draws += s.batch(7)
        seen = Counter(draws[:2 * 61])
        self.assertEqual(len(seen), 61)
        self.assertEqual(set(seen.values()), {2})

    def test_study_weights_balance(self):
        w = D.study_weights({"big": 900, "small": 100})
        self.assertAlmostEqual(900 * w["big"], 100 * w["small"])


class Controls(unittest.TestCase):
    def test_same_line_two_studies_never_share(self):
        studies = np.array(["s1", "s1", "s2", "s2", "s1"])
        contexts = np.array(["K562"] * 5)
        ctrl = np.array([True, True, True, True, False])
        libs = np.array(["L1", "L2", "L1", "L1", "L1"])
        pools = D.control_rows_by_key(studies, contexts, ctrl, libs)
        self.assertEqual(set(pools), {"s1|K562", "s2|K562"})
        rng = np.random.default_rng(0)
        for _ in range(50):
            rows = D.draw_controls(pools, "s1|K562", "L1", 2, rng)
            self.assertTrue(set(rows.tolist()) <= {0, 1})
            rows = D.draw_controls(pools, "s2|K562", "L1", 2, rng)
            self.assertTrue(set(rows.tolist()) <= {2, 3})

    def test_own_library_first(self):
        pools = {"s|X": {"L1": np.arange(0, 10), "L2": np.arange(10, 12)}}
        rng = np.random.default_rng(1)
        self.assertTrue(set(D.draw_controls(pools, "s|X", "L1", 5, rng).tolist()) <= set(range(10)))
        both = set()
        for _ in range(30):
            both |= set(D.draw_controls(pools, "s|X", "L2", 5, rng).tolist())
        self.assertTrue(both & set(range(10)))          # too few in L2: the whole key is used


class Estimator(unittest.TestCase):
    def test_recovers_a_known_shift(self):
        rng = np.random.default_rng(0)
        G = 50
        p = rng.dirichlet(np.ones(G) * 2)
        f = np.ones(G); f[3] = 4.0; f[7] = 0.25
        q = p * f / (p * f).sum()
        ctrl = sp.csr_matrix(rng.multinomial(20000, p, size=400).astype(float))
        pert = sp.csr_matrix(rng.multinomial(20000, q, size=400).astype(float))
        m = np.ones(G, bool)
        s, ok = D.shift(D.mean_prop(pert, np.asarray(pert.sum(1)).ravel(), m),
                        D.mean_prop(ctrl, np.asarray(ctrl.sum(1)).ravel(), m), m)
        truth = np.log(q) - np.log(p)
        self.assertLess(np.abs(s[ok] - truth[ok])[[3, 7]].max(), 0.05)
        self.assertGreater(np.corrcoef(s[ok], truth[ok])[0, 1], 0.95)

    def test_unmeasured_genes_give_no_shift(self):
        m = np.array([True, False, True])
        s, ok = D.shift(np.array([0.5, 0.3, 0.2]), np.array([0.25, 0.5, 0.25]), m)
        self.assertEqual(ok.tolist(), [True, False, True])
        self.assertEqual(s[1], 0.0)


if __name__ == "__main__":
    unittest.main()
