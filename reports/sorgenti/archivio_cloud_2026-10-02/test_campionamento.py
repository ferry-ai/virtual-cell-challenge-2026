"""Tests of the outcome-blind samples: determinism, order invariance, pi, controls, exclusions, no use of counts."""
import unittest

import numpy as np
import pandas as pd

from campionamento import select_cd4, select_orion, summary


def cd4_fixture(seed: int = 0) -> pd.DataFrame:
    """Cells shaped like the measured D1_Rest obs: guide groups, types, lanes, low_quality."""
    rng = np.random.default_rng(seed)
    rows = []
    for g, n in (("STAT6-1", 25), ("STAT6-2", 4), ("VIM-1", 12)):
        rows += [("targeting single sgRNA", "targeting", g, g.split("-")[0])] * n
    rows += [("targeting single sgRNA", "non-targeting", "NTC-086", "NTC")] * 7
    rows += [("no sgRNA", None, None, None)] * 5
    rows += [("multi sgRNA", "targeting", "multi_sgRNA", None)] * 3
    df = pd.DataFrame(rows, columns=["guide_group", "guide_type", "guide_id", "perturbed_gene_id"])
    df["lane_id"] = rng.choice(["CD4i_R1L01", "CD4i_R1L02"], len(df))
    df["low_quality"] = False
    df.loc[df.index[:2], "low_quality"] = True  # two STAT6-1 cells are low quality
    df.index = [f"BC{i:05d}" for i in range(len(df))]
    return df


class TestCD4(unittest.TestCase):
    def test_counts_pi_and_roles(self):
        s = select_cd4(cd4_fixture(), "D1_Rest", "salt-a", k=10)
        sel = s[s.selected]
        self.assertEqual(len(s), 56)  # every cell keeps a row
        ctl = s[s.role == "control"]
        self.assertTrue(ctl.selected.all() and (ctl.pi == 1).all() and len(ctl) == 7)
        g1 = s[(s.role == "targeted") & (s.guide_id == "STAT6-1")]
        self.assertEqual(len(g1), 23)  # 25 minus the two low-quality cells
        self.assertEqual(int(g1.selected.sum()), 10)
        self.assertTrue(np.allclose(g1.pi, 10 / 23))
        g2 = s[(s.role == "targeted") & (s.guide_id == "STAT6-2")]
        self.assertTrue(g2.selected.all() and (g2.pi == 1).all())
        exc = s[s.role == "excluded"]
        self.assertEqual(sorted(exc.reason.unique()), ["low_quality", "multi sgRNA", "no sgRNA"])
        self.assertTrue((exc.pi == 0).all() and not exc.selected.any())
        self.assertEqual(len(sel), 7 + 10 + 4 + 10)

    def test_deterministic_and_order_invariant(self):
        a = select_cd4(cd4_fixture(), "D1_Rest", "salt-a", k=10)
        obs = cd4_fixture().sample(frac=1.0, random_state=3)
        b = select_cd4(obs, "D1_Rest", "salt-a", k=10)
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))

    def test_salt_changes_the_sample_and_counts_are_ignored(self):
        a = select_cd4(cd4_fixture(), "D1_Rest", "salt-a", k=10)
        c = select_cd4(cd4_fixture(), "D1_Rest", "salt-b", k=10)
        self.assertNotEqual(set(a[a.selected].cell), set(c[c.selected].cell))
        obs = cd4_fixture()
        obs["total_counts"] = np.arange(len(obs))[::-1]  # an outcome column must not change anything
        d = select_cd4(obs, "D1_Rest", "salt-a", k=10)
        self.assertEqual(set(a[a.selected].cell), set(d[d.selected].cell))

    def test_summary(self):
        s = summary(select_cd4(cd4_fixture(), "D1_Rest", "salt-a", k=10))
        self.assertEqual(s["selected"], 31)
        self.assertEqual(s["targeted_strata"], 3)


class TestOrion(unittest.TestCase):
    def test_cap_per_target_over_gem_files(self):
        rows = [("gem01", "TP53", 1, False)] * 30 + [("gem02", "TP53", 1, False)] * 20 + \
               [("gem01", "MYC", 1, False)] * 5 + [("gem02", "NTC", 1, True)] * 9 + [("gem02", "MYC", 0, False)] * 4
        obs = pd.DataFrame(rows, columns=["gem_file", "target", "pass_guide_filter", "is_control"])
        obs.index = [f"C{i}" for i in range(len(obs))]
        s = select_orion(obs, "HCT116", "salt-o", k=40)
        tp = s[(s.role == "targeted") & (s.target == "TP53")]
        self.assertEqual(int(tp.selected.sum()), 40)
        self.assertTrue(np.allclose(tp.pi, 40 / 50))
        self.assertEqual(set(tp.gem_file), {"gem01", "gem02"})
        self.assertTrue(s[s.role == "control"].selected.all())
        self.assertEqual(int((s.role == "excluded").sum()), 4)


if __name__ == "__main__":
    unittest.main()
