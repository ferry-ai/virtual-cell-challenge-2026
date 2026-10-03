"""Fixtures proving that aliases, duplicate cells or sources, modalities, held-out groups and hidden targets cannot
inflate coverage. The fold expectations were computed outside Python (printf | sha256sum, 3/10), so they also check
that the copied hash rule is R-LEAD's.

    python -m unittest test_coverage_audit -v      (from this folder)
"""
import json
import sys
import unittest
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import coverage_audit as ca  # noqa: E402

RULES = {"contexts": {"K562": "K562", "HEK293": "HEK293T", "HEK293T": "HEK293T", "HepG2": "HepG2", "RPE1": "RPE1",
                      "A549": "A549", "Jurkat": "Jurkat", "H1": "H1"},
         "study_prefixes": {"dixit2016_": "K562", "hipsci_": "iPSC"}, "related": {}}
N_CTRL = 5


def cells(study, context, target, n, modality="CRISPRi", tag=""):
    control = target == "NTC"
    return [{"cell_key": f"{study}|lib|{context}:{target}:{tag}{i}", "study": study, "context": context,
             "modality": modality, "target": target, "control_kind": "NTC" if control else "none"} for i in range(n)]


def key(study, context, modality="CRISPRi", **targets):
    """One (study, context) with its controls and n cells per target."""
    rows = cells(study, context, "NTC", N_CTRL, modality)
    for t, n in targets.items():
        rows += cells(study, context, t, n, modality)
    return rows


def run(rows, rules=RULES, **kw):
    count_kw = {k: kw.pop(k) for k in ("republications",) if k in kw}
    counts, excl = ca.count_cells(pd.DataFrame(rows), min_controls=N_CTRL, **count_kw)
    return ca.audit(counts, rules, **kw), excl


class TestFoldRule(unittest.TestCase):
    def test_folds_equal_the_shell_computed_ones(self):
        expect = {"ENSG00000141510": 1, "ENSG00000136997": 2, "ENSG00000012048": 4, "ENSG00000171862": 1,
                  "SYM:G1": 4, "SYM:G2": 1, "SYM:G3": 0, "SYM:G4": 0, "SYM:G5": 2, "SYM:G7": 3, "SYM:G8": 0,
                  "SYM:G10": 0, "SYM:G12": 4}
        self.assertEqual({k: ca.target_fold(k, 5) for k in expect}, expect)


class TestCoverage(unittest.TestCase):
    def test_alias_is_one_target_not_two(self):
        rows = key("a", "K562", TCEB1=20) + key("b", "HepG2", ELOC=20)
        res, _ = run(rows, aliases={"TCEB1": "ELOC"})
        h = res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]
        self.assertEqual((h["targets"], h["1"], h["2"]), (1, 0, 1))
        res, _ = run(rows)                                         # without the alias map: two targets, one group each
        h = res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]
        self.assertEqual((h["targets"], h["1"], h["2"]), (2, 2, 0))

    def test_alias_in_the_same_group_adds_no_support(self):
        rows = key("a", "K562", TCEB1=20) + key("dixit2016_k562_ko", "K562 day 7", ELOC=20)
        res, _ = run(rows, aliases={"TCEB1": "ELOC"})
        h = res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]
        self.assertEqual((h["targets"], h["1"], h["2"]), (1, 1, 0))

    def test_the_source_ensembl_id_joins_two_spellings(self):
        a = key("a", "K562", FAM208A=20)
        b = key("b", "HepG2", TASOR=20)
        for r in a + b:
            r["target_id"] = "ENSG00000163946" if r["target"] != "NTC" else "NTC"
        res, _ = run(a + b)
        self.assertEqual(res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]["2"], 1)

    def test_duplicate_cells_count_once(self):
        rows = key("a", "K562", G1=8)
        rows += cells("a", "K562", "G1", 8)                       # the same eight cell keys, published twice
        res, excl = run(rows)
        self.assertEqual(int(excl.loc[excl.reason == "duplicate_cell", "cells"].sum()), 8)
        self.assertEqual(res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]["targets"], 0)

    def test_a_republished_study_is_not_a_second_source(self):
        rows = key("replogle_k562", "K562", G1=12) + key("scp_replogle_k562", "K562", G1=12)
        res, excl = run(rows, republications={"scp_replogle_k562": "replogle_k562"})
        self.assertEqual(int(excl.loc[excl.reason == "republication", "cells"].sum()), 12 + N_CTRL)
        m = res["target_by_group"]
        self.assertEqual((int(m.n_admitted.sum()), int(m.studies.max())), (12, 1))

    def test_modalities_are_counted_apart(self):
        rows = key("a", "K562", G1=20) + key("b", "A549", modality="KO", G1=20)
        res, _ = run(rows)
        h = res["summary"]["histogram_targets_by_training_groups"]
        self.assertEqual((h["all_modalities"]["2"], h["CRISPRi"]["1"], h["CRISPRi"]["2"]), (1, 1, 0))

    def test_a_held_out_group_leaves_with_every_study_and_state(self):
        rows = (key("replogle", "K562", G1=20, G2=20) + key("dixit2016_k562_ko", "K562 day 7", G1=20, G2=20)
                + key("c", "HepG2", G1=20))
        res, _ = run(rows, holdout_groups=["K562"])
        self.assertNotIn("K562", res["summary"]["training_groups"])
        self.assertEqual(dict(res["support"]["all_modalities"]), {"SYM:G1": 1})   # G2 lived only in K562: untaught
        roles = res["labels"].groupby("role")["n_admitted"].sum()
        self.assertEqual(int(roles["held_out_group"]), 80)

    def test_related_groups_leave_together(self):
        rules = {**RULES, "related": {"HEK293T": ["HepG2"]}}
        rows = key("a", "HEK293T", G1=20) + key("b", "HepG2", G1=20) + key("c", "K562", G1=20)
        res, _ = run(rows, rules=rules, holdout_groups=["HEK293T"])
        self.assertEqual(dict(res["support"]["all_modalities"]), {"SYM:G1": 1})

    def test_hidden_targets_are_removed_in_every_group(self):
        rows = []
        for study, ctx in (("a", "K562"), ("b", "HepG2"), ("c", "RPE1")):
            rows += key(study, ctx, G3=20, G1=20)                  # G3 is in fold 0, G1 in fold 4
        res, _ = run(rows, hidden_fold=0, n_folds=5)
        self.assertEqual(dict(res["support"]["all_modalities"]), {"SYM:G1": 3})
        res, _ = run(rows)
        self.assertEqual(dict(res["support"]["all_modalities"]), {"SYM:G1": 3, "SYM:G3": 3})

    def test_cells_donors_and_contexts_do_not_add_support(self):
        rows = []
        for donor in ("eipl_1", "fiaj_1", "iudw_1"):
            rows += key("hipsci_targeted_19", donor, G1=500)
        res, _ = run(rows)
        h = res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]
        self.assertEqual((h["1"], h["2"], h["3"]), (1, 0, 0))
        self.assertEqual(int(res["target_by_group"].contexts.iloc[0]), 3)

    def test_too_few_cells_is_no_support(self):
        res, _ = run(key("a", "K562", G1=9) + key("b", "HepG2", G1=20))
        self.assertEqual(dict(res["support"]["all_modalities"]), {"SYM:G1": 1})

    def test_a_context_without_a_rule_is_refused_not_promoted(self):
        rows = key("frangieh2021_melanoma_ko", "Control", modality="KO", G1=20)
        with self.assertRaises(ValueError):
            run(rows)
        res, _ = run(rows, allow_unmapped=True)
        self.assertEqual(res["summary"]["training_groups"], ["UNMAPPED:frangieh2021_melanoma_ko|Control"])
        self.assertEqual(len(res["summary"]["unmapped_contexts"]), 1)

    def test_a_key_without_controls_teaches_nothing(self):
        rows = cells("a", "K562", "NTC", 2) + cells("a", "K562", "G1", 50)
        res, excl = run(rows)
        self.assertEqual(int(excl.loc[excl.reason == "key_without_controls", "cells"].sum()), 52)
        self.assertEqual(res["summary"]["histogram_targets_by_training_groups"]["all_modalities"]["targets"], 0)

    def test_unassigned_and_combined_labels_are_no_targets(self):
        rows = key("a", "K562", G1=20) + cells("a", "K562", "UNASSIGNED", 30) + cells("a", "K562", "G1+G2", 30)
        res, _ = run(rows)
        self.assertEqual(dict(res["support"]["all_modalities"]), {"SYM:G1": 1})
        roles = res["labels"].groupby("role")["n_admitted"].sum()
        self.assertEqual((int(roles["unassigned"]), int(roles["combined"])), (30, 30))


class TestExpandedRules(unittest.TestCase):
    def test_the_proposed_map_agrees_with_the_pilot_and_names_the_third_wave(self):
        rules = json.loads((HERE / "line_groups_expanded_v1.json").read_text(encoding="utf-8"))
        pilot = json.loads((ca.REPO / "reports/modelli/rete_cellulare_2026-10-03/line_groups.json")
                           .read_text(encoding="utf-8"))
        for ctx, grp in pilot["contexts"].items():
            self.assertEqual(ca.group_of("any", ctx, rules), grp)
        for prefix, grp in pilot["study_prefixes"].items():
            self.assertEqual(ca.group_of(prefix + "x", "eipl_1", rules), grp)
        expect = {("dixit2016_k562_ko", "K562 day 7"): "K562", ("xu2023_hek293_crispri", "HEK293"): "HEK293T",
                  ("datlinger2017_jurkat_ko", "stimulated"): "Jurkat", ("frangieh2021_melanoma_ko", "IFNγ"):
                  "Melanoma_Frangieh2021", ("orion_hct116", "HCT116"): "HCT116",
                  ("cd4_marson2025", "CD4T D1 Rest"): "CD4T", ("shifrut2018_tcells_ko", "D1_stim"):
                  "PrimaryT_Shifrut2018"}
        for (study, ctx), grp in expect.items():
            self.assertEqual(ca.group_of(study, ctx, rules), grp)


if __name__ == "__main__":
    unittest.main()
