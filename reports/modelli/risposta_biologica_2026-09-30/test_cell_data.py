"""Controlled small cases for cell_data.py: each property the review of 30/09 asked for, with a known answer.

The classes after Estimator cover the four points the owner kept open before any extended training (30/09, 23:39):
duplicates and collisions (Identity, FeatureCollisions), combined perturbations (CombinedPerturbations), phenotype
conservation in QC (PhenotypeGuard), control masks (ControlMasks). test_prepass.py runs the same rules end to end
through train_cellnet.py on synthetic shards.

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

AXIS = {"TFAM", "LAT", "GFM1", "A", "B", "C", "D", "MT-CO1", "CEBPA", "CEBPB", "CEBPE"}


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
        # 5 counts or 1 gene: no usable profile (absolute floor, never lifted); 100 counts against controls of
        # 1,000-5,000: far below them, a relative rule; 900 counts: low, but a plausible phenotype; 400 counts or
        # 200 genes: below the relative thresholds (every relative rule can be lifted by phenotype_guard)
        test_lib = np.array([5.0, 3000, 3000, 3000, 900, 400, 3000, 100])
        test_genes = np.array([900.0, 1.0, 900, 900, 900, 900, 200, 90])
        test_mito = np.array([0.01, 0.01, 0.9, 0.01, 0.08, 0.01, 0.01, 0.01])
        ok, why = D.admit(test_lib, test_genes, test_mito, t)
        self.assertEqual(ok.tolist(), [False, False, False, True, True, False, False, False])
        self.assertEqual(why.tolist(), [D.ABSOLUTE, D.ABSOLUTE, "mito_above_ceiling", "", "", "counts_below_floor",
                                        "genes_below_floor", "counts_far_below_controls"])

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


class CombinedPerturbations(unittest.TestCase):
    def test_a_combination_is_not_its_first_gene(self):
        self.assertEqual(D.parse_label("CEBPA_CEBPB", AXIS), ("combined", ("CEBPA", "CEBPB")))
        self.assertEqual(D.normalise("CEBPA_CEBPB", AXIS), "CEBPA+CEBPB")
        self.assertEqual(D.normalise("CEBPB+CEBPA", AXIS), "CEBPA+CEBPB")          # one canonical label per set
        self.assertEqual(D.normalise("CEBPA+CEBPB", AXIS), "CEBPA+CEBPB")          # idempotent

    def test_guides_of_one_gene_stay_single(self):
        self.assertEqual(D.parse_label("TFAM_+_60145205.23-P1P2|TFAM_-_60145223.23-P1P2", AXIS), ("single", ("TFAM",)))
        self.assertEqual(D.parse_label("CEBPE_ctrl", AXIS), ("single", ("CEBPE",)))
        self.assertEqual(D.parse_label("ctrl_ctrl", AXIS), ("unresolved", ()))

    def test_a_hidden_component_never_reaches_training(self):
        hidden, trained = {"CEBPB"}, {"CEBPA", "CEBPE"}
        self.assertEqual(D.classify_combined("K", ("CEBPA", "CEBPB"), "H", hidden, trained), "combined:T")
        self.assertEqual(D.classify_combined("K", ("CEBPA", "CEBPE"), "H", hidden, trained), "combined:train")
        self.assertEqual(D.classify_combined("H", ("CEBPA", "CEBPE"), "H", hidden, trained), "combined:C")
        self.assertEqual(D.classify_combined("H", ("CEBPA", "CEBPB"), "H", hidden, trained), "combined:J")
        self.assertEqual(D.classify_combined("H", ("CEBPA", "D"), "H", hidden, trained), "combined:J")   # D never trained


class Identity(unittest.TestCase):
    def rows(self, dense):
        return sp.csr_matrix(np.asarray(dense, float))

    def test_fingerprint_tells_counts_apart_and_ignores_storage_order(self):
        x = self.rows([[0, 3, 1, 0], [0, 3, 1, 0], [0, 3, 2, 0]])
        fp = D.fingerprints(x)
        self.assertEqual(fp[0], fp[1])
        self.assertNotEqual(fp[0], fp[2])
        unsorted = sp.csr_matrix((np.array([1.0, 3.0]), np.array([2, 1]), np.array([0, 2])), shape=(1, 4))
        self.assertEqual(D.fingerprints(unsorted)[0], fp[0])

    def test_duplicate_collision_version(self):
        k = D.hash64(["s1|L1|AAA", "s1|L1|BBB", "s1|L1|AAA", "s1|L1|BBB", "s1|L1|CCC", "s1|L1|CCC"])
        fp = np.array([10, 20, 10, 21, 30, 31], dtype=np.uint64)
        source = np.array([0, 0, 1, 0, 0, 1])
        st = D.identity(k, fp, source)
        # AAA again with its counts, even from another file: one cell; BBB with other counts in the same file: two
        # cells sharing a key; CCC with other counts from another file: another version of the same cell
        self.assertEqual(st.tolist(), ["new", "new", "duplicate", "collision", "new", "version"])

    def test_independent_cells_with_equal_counts_are_kept(self):
        k = D.hash64(["s1|L1|AAA", "s2|L7|QQQ", "s3|L2|ZZZ"])
        fp = np.array([10, 10, 10], dtype=np.uint64)
        self.assertEqual(D.identity(k, fp, np.array([0, 1, 2])).tolist(), ["new", "new", "new"])
        study = np.array(["s1", "s2", "s3"], dtype=object)
        self.assertEqual(D.content_matches(k, fp, np.ones(3, bool), study),
                         [{"studies": ["s1", "s2"], "cells": 1}, {"studies": ["s1", "s3"], "cells": 1}])
        self.assertEqual(D.content_matches(k, fp, np.array([True, True, False]), study),
                         [{"studies": ["s1", "s2"], "cells": 1}])     # a poor cell is not even reported

    def test_first_sighting_of_a_key_wins(self):
        k = D.hash64(["s|L|A", "s|L|A"])
        fp = np.array([1, 2], dtype=np.uint64)
        self.assertEqual(D.identity(k, fp, np.array([0, 1])).tolist(), ["new", "version"])
        self.assertEqual(D.identity(k, fp[::-1], np.array([1, 0])).tolist(), ["new", "version"])


class FeatureCollisions(unittest.TestCase):
    def test_two_features_on_one_gene_are_masked_not_summed(self):
        gene_of_axis = np.array([0, 1, 2, -1, 3])                  # axis position -> model gene
        official = np.array([0, 1, 1, 4, -1, 2])                    # two native features land on axis 1
        measured = np.array([True, True, True, True, True, False])  # the last feature is not measured
        col, mask, collided = D.feature_columns(official, measured, gene_of_axis, 4)
        self.assertEqual(col.tolist(), [0, -1, -1, 3, -1, -1])
        self.assertEqual(mask.tolist(), [True, False, False, True])
        self.assertEqual(collided.tolist(), [1])

    def test_no_collision_keeps_every_measured_feature(self):
        col, mask, collided = D.feature_columns(np.array([0, 1, 2]), np.ones(3, bool), np.array([0, 1, 2]), 3)
        self.assertEqual(col.tolist(), [0, 1, 2])
        self.assertTrue(mask.all())
        self.assertEqual(collided.size, 0)


class PhenotypeGuard(unittest.TestCase):
    """One key: 400 controls; knockdowns with a third and with a twelfth of the counts (severe: most cells far below
    every control); one with a mitochondrial phenotype; one normal group; 10% unusable droplets everywhere (5 counts);
    a group of unusable droplets only; a group of 4 cells."""

    def setUp(self):
        rng = np.random.default_rng(4)

        def cells(n, scale=1.0, mito=(0.01, 0.05)):
            lib = np.exp(rng.normal(8, 0.3, n)) * scale
            return lib, lib ** 0.8, rng.uniform(*mito, n)
        parts = {"NTC": cells(400), "KD_counts": cells(200, 0.35), "KD_severe": cells(200, 0.08),
                 "KD_mito": cells(200, mito=(0.2, 0.4)), "normal": cells(200),
                 "empties": (np.full(50, 5.0), np.full(50, 4.0), np.full(50, 0.02)), "tiny": cells(4, 0.3)}
        self.group = np.concatenate([[g] * len(v[0]) for g, v in parts.items()]).astype(object)
        self.lib = np.concatenate([v[0] for v in parts.values()])
        self.genes = np.concatenate([v[1] for v in parts.values()])
        self.mito = np.concatenate([v[2] for v in parts.values()])
        broken = rng.random(self.lib.size) < 0.1                     # unusable droplets, in every group alike
        self.lib[broken], self.genes[broken] = 5.0, 3.0
        self.broken = broken
        self.ctrl = self.group == "NTC"
        ok_c = self.ctrl & ~broken
        self.t = D.thresholds_from_controls(self.lib[ok_c], self.genes[ok_c], self.mito[ok_c])
        _, self.reason = D.admit(self.lib, self.genes, self.mito, self.t)
        self.keys = np.full(self.lib.size, "s|K", dtype=object)

    def rate(self, reason, g):
        sel = self.group == g
        return float((~np.isin(reason[sel], ["", "phenotype_guard"])).mean())

    def test_relative_rules_alone_remove_the_phenotypes(self):
        self.assertGreater(self.rate(self.reason, "KD_counts"), 0.15)
        self.assertGreater(self.rate(self.reason, "KD_severe"), 0.9)
        self.assertGreater(self.rate(self.reason, "KD_mito"), 0.8)

    def test_a_severe_knockdown_is_not_called_a_technical_failure(self):
        intact = (self.group == "KD_severe") & ~self.broken
        self.assertNotIn(D.ABSOLUTE, set(self.reason[intact]))
        self.assertIn("counts_far_below_controls", set(self.reason[intact]))

    def test_guard_keeps_the_phenotypes_above_the_absolute_floor(self):
        ok, reason, rows = D.phenotype_guard(self.reason, self.group, self.ctrl, self.keys)
        for g in ("KD_counts", "KD_severe", "KD_mito"):
            sel = (self.group == g) & ~self.broken
            self.assertTrue(ok[sel].all(), g)                           # every usable cell of the phenotype kept
            self.assertTrue((reason[(self.group == g) & self.broken] == D.ABSOLUTE).all())
        self.assertFalse(ok[self.group == "empties"].any())            # unusable droplets stay out
        selective = {r["group"] for r in rows if r["selective"]}
        self.assertEqual(selective, {"KD_counts", "KD_severe", "KD_mito"})
        self.assertLess(abs(self.rate(reason, "normal") - self.rate(reason, "NTC")), 0.08)

    def test_groups_below_n_min_are_not_guarded(self):
        _, reason, rows = D.phenotype_guard(self.reason, self.group, self.ctrl, self.keys)
        self.assertNotIn("tiny", {r["group"] for r in rows})
        self.assertTrue((reason[self.group == "tiny"] == self.reason[self.group == "tiny"]).all())

    def test_unguarded_cells_are_left_alone(self):
        guarded = self.group != "KD_mito"                               # e.g. unlabelled cells
        ok, reason, _ = D.phenotype_guard(self.reason, self.group, self.ctrl, self.keys, guarded=guarded)
        self.assertTrue((reason[self.group == "KD_mito"] == self.reason[self.group == "KD_mito"]).all())


class ControlMasks(unittest.TestCase):
    def test_key_mask_is_the_intersection(self):
        m1, m2 = np.array([1, 1, 1, 0], bool), np.array([1, 1, 0, 1], bool)
        km = D.key_masks([m1, m2, m1], [{"s|K"}, {"s|K"}, {"s|H"}])
        self.assertEqual(km["s|K"].tolist(), [True, True, False, False])
        self.assertEqual(km["s|H"].tolist(), m1.tolist())

    def test_shift_on_the_genes_both_measure(self):
        rng = np.random.default_rng(0)
        G = 10
        p = rng.dirichlet(np.ones(8) * 3)
        f = np.ones(8); f[2] = 3.0
        q = p * f / (p * f).sum()
        ctrl = np.zeros((300, G)); ctrl[:, :8] = rng.multinomial(5000, p, size=300)
        pert = np.zeros((300, G)); pert[:, :8] = rng.multinomial(5000, q, size=300)
        pert[:, 8:] = rng.poisson(4000, size=(300, 2))               # genes the controls' shard does not measure
        m_pert, m_ctrl = np.ones(G, bool), np.r_[np.ones(8, bool), np.zeros(2, bool)]
        s, ok, common = D.observed_shift(pert, m_pert, ctrl, m_ctrl)
        self.assertEqual(common.tolist(), m_ctrl.tolist())
        self.assertFalse(ok[8:].any())
        truth = np.log(q) - np.log(p)
        self.assertLess(np.abs(s[:8] - truth).max(), 0.05)            # libraries on the common genes: no dilution

    def test_context_encoder_ignores_genes_outside_each_row_mask(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch absent")
        import cellnet as CN
        torch.manual_seed(0)
        G = 12
        model = CN.build_model(G, 3, 1, 1, np.arange(G), dim=8, rank=4, target_code="identity")
        x = torch.rand(1, 5, G) * 10
        mask = torch.ones(1, 5, G, dtype=torch.bool)
        mask[0, 2, 7:] = False                                        # row 2 comes from a shard without genes 7..11
        lib = (x * mask).sum(-1)                                      # each row's counts on its own shard's genes
        z1, _ = model.context(x, mask, lib)
        x2 = x.clone(); x2[0, 2, 7:] = 1000.0
        z2, _ = model.context(x2, mask, (x2 * mask).sum(-1))
        self.assertTrue(torch.allclose(z1, z2))


if __name__ == "__main__":
    unittest.main()
