"""The measuring path of the bench on small synthetic effects: structure, contrasts, controls and audits.

    .\\scripts\\py.cmd -m unittest reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/test_bench_core.py
"""
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bench_core as core  # noqa: E402

PANEL = [f"G{i}" for i in range(30)]
AXIS = PANEL + [f"X{i}" for i in range(270)]
FOLDS = {"C-ONE": {"lineage": "ONE", "truth": [{"table": "one", "role": "primary"}]},
         "C-TWO": {"lineage": "TWO", "truth": [{"table": "two", "role": "primary"},
                                               {"table": "two_stim", "role": "stimulus"}]}}
ARMS = ["T0", "R1", "T1", "P4"]


def world(seed=1):
    rng = np.random.default_rng(seed)
    n, g = len(PANEL), len(AXIS)
    tables, effects = {}, {}
    for name, targets in (("one", PANEL[:28]), ("two", PANEL[2:]), ("two_stim", PANEL[2:20])):
        signal = rng.normal(0, 1, (len(targets), g)) * (rng.random((len(targets), g)) < 0.25)
        raw = signal + rng.normal(0, 0.15, signal.shape)
        se = np.full(signal.shape, 0.15)
        raw[:, -5:] = np.nan
        tables[name] = {"targets": targets, "shrunk": (raw * 0.9).astype(np.float32), "raw": raw.astype(np.float32),
                        "se": se.astype(np.float32), "n_cells": np.full(len(targets), 80), "signal": signal}
    for fid, truth in (("C-ONE", "one"), ("C-TWO", "two")):
        full = np.zeros((n, g))
        pos = {t: i for i, t in enumerate(tables[truth]["targets"])}
        for i, t in enumerate(PANEL):
            if t in pos:
                full[i] = tables[truth]["signal"][pos[t]]
        observed = np.ones((n, g), bool)
        observed[:, 290:293] = False
        base = np.where(observed, 0.6 * full + rng.normal(0, 0.5, full.shape), 0.0).astype(np.float32)
        better = base.copy()
        better[5:8] = np.where(observed[5:8], 0.6 * full[5:8] + rng.normal(0, 0.05, full[5:8].shape), 0.0)
        worse = np.where(observed, 0.6 * full + rng.normal(0, 1.5, full.shape), 0.0).astype(np.float32)
        shifted = (base + np.where(observed, 0.4, 0.0)).astype(np.float32)
        effects[("T0", fid)] = (base, observed)
        effects[("R1", fid)] = (better, observed)
        effects[("T1", fid)] = (better, observed)
        effects[("P4", fid)] = (worse, observed)
        effects[("T0~gamma0", fid)] = (shifted, observed)
        effects[("T0~nocis", fid)] = (base.copy(), observed)
    return tables, effects


class Measure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, cls.effects = world()
        cls.results, cls.macro, cls.shuffle, cls.rows = core.measure(
            FOLDS, ARMS, cls.effects, cls.tables.__getitem__, PANEL, AXIS, log=lambda m: None)

    def test_every_fold_truth_and_label_is_reported(self):
        self.assertEqual(sorted(self.results), ["C-ONE", "C-TWO"])
        self.assertEqual(sorted(self.results["C-TWO"]["truth"]), ["two", "two_stim"])
        block = self.results["C-ONE"]["truth"]["one"]
        self.assertEqual(block["targets"], 28)
        labels = set(block["arms"])
        self.assertEqual(labels, {"T0", "R1", "T1", "P4", "T0~gamma0", "T0~nocis", "T0~shuffle", "T1~shuffle",
                                  "T0~meanonly", "T0~null"})
        expected_rows = (28 + 28 + 18) * len(labels)
        self.assertEqual(len(self.rows), expected_rows)
        self.assertEqual(len(self.rows[0]), len(core.CSV_HEADER))

    def test_the_contrast_counts_only_the_targets_that_changed(self):
        k1 = self.results["C-ONE"]["truth"]["one"]["contrasts"]["K1"]
        self.assertEqual(k1["targets_changed"], 3)
        self.assertEqual(k1["changed"], ["G5", "G6", "G7"])
        sub = k1["measures"]["r_spec"]["changed_only"]
        self.assertEqual(sub["n"], 3)
        self.assertGreater(sub["mean"], 0.1)
        same = self.results["C-ONE"]["truth"]["one"]["contrasts"]["c_nocis"]
        self.assertEqual(same["targets_changed"], 0)
        self.assertEqual(same["measures"]["disc"]["all"]["mean"], 0.0)

    def test_more_noise_is_read_as_worse_and_the_macro_spans_both_folds(self):
        k0 = self.macro["K0"]["measures"]
        self.assertEqual(k0["r_spec"]["folds"], 2)
        self.assertTrue(k0["r_spec"]["resolved"] and k0["r_spec"]["lo"] > 0)
        self.assertTrue(k0["mse_ratio"]["resolved"] and k0["mse_ratio"]["hi"] < 0)

    def test_the_shuffle_takes_discrimination_to_chance(self):
        for fid in FOLDS:
            s = self.shuffle[fid]
            self.assertGreater(s["T0_disc"], 0.95)
            self.assertLess(abs(s["shuffle_disc"] - 0.5), 0.15)
            self.assertTrue(s["difference"]["resolved"])

    def test_a_common_shift_shows_in_the_common_share_and_not_in_the_specific_part(self):
        arms = self.results["C-ONE"]["truth"]["one"]["arms"]
        self.assertGreater(arms["T0~gamma0"]["common_share_pred"], arms["T0"]["common_share_pred"] + 0.1)
        self.assertAlmostEqual(arms["T0~gamma0"]["r_spec"], arms["T0"]["r_spec"], places=6)
        self.assertAlmostEqual(arms["T0~null"]["disc"], 0.5, places=9)
        # the targets' own genes are left out of the measures and read apart, one pair per target
        self.assertEqual(arms["T0"]["own_gene"]["pairs"], 28)


class Audits(unittest.TestCase):
    def test_a_copy_of_a_table_is_found_and_unrelated_tables_are_not(self):
        tables, _ = world()
        tables = {k: {kk: vv for kk, vv in v.items() if kk != "signal"} for k, v in tables.items()}
        tables["one_again"] = dict(tables["one"], shrunk=tables["one"]["shrunk"] * 1.01)
        pairs = {(p["a"], p["b"]): p for p in core.table_audit(tables, np.isin(np.asarray(AXIS), np.asarray(PANEL)))}
        self.assertGreater(pairs[("one", "one_again")]["cosine_median"], 0.999)
        self.assertLess(abs(pairs[("one", "two")]["cosine_median"]), 0.2)

    def test_two_tables_of_one_lineage_are_not_two_lineages(self):
        manifest = {"lineages": {"L1": {"tables": ["a", "a2"]}, "L2": {"tables": ["b"]}},
                    "arms": {"X": {"sources": ["a", "a2", "b"]}, "Y": {"sources": ["a", "b"]}}}
        targets = {"a": PANEL[:20], "a2": PANEL[10:25], "b": PANEL}
        audit = core.vote_audit(manifest, targets, PANEL)
        self.assertEqual(audit["X"]["targets_with_a_lineage_voting_more_than_once"], 10)
        self.assertEqual(audit["X"]["repeated_votes_by_lineage"], {"L1": 10})
        self.assertEqual(audit["Y"]["targets_with_a_lineage_voting_more_than_once"], 0)
        self.assertEqual(audit["X"]["votes_total"] - audit["X"]["lineage_votes_total"], 10)


if __name__ == "__main__":
    unittest.main()
