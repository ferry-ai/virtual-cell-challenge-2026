"""nested_rule.py on hand-made groups tables: each status of a level and each kind of recommended level.

    python -m unittest test_nested_rule -v     (from this folder, with the project venv)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nested_rule as NR  # noqa: E402

CAPS = [32, 64, 128]


def unit(name, groups, cells, halves, r, sign=0.95, targets=30, guides=4, guides_kept=None):
    """`groups` equal groups of a unit: r maps a cap to the r_spec of that level."""
    rows = []
    for i in range(groups):
        row = {"key": f"{name}|ctx", "unit": name, "target": f"T{i}", "cells": cells, "strata": 8, "libraries": 2,
               "guides": guides, "genes_compared": 5000, "targets_in_key": targets, "r_halves": 0.9,
               "sign_top_halves": 0.9, "r_spec_halves": halves, "sign_top_spec_halves": 0.9}
        for c in CAPS:
            whole = cells <= c
            row.update({f"cells_{c}": min(cells, c), f"r_{c}": 0.99, f"sign_top_{c}": 0.99, f"overlap_top_{c}": 0.9,
                        f"rmse_{c}": 0.01, f"r_spec_{c}": 1.0 if whole else r[c],
                        f"sign_top_spec_{c}": 1.0 if whole else sign, f"overlap_top_spec_{c}": 0.8, f"strata_{c}": 8,
                        f"guides_{c}": (guides_kept or {}).get(c, guides)})
        rows.append(row)
    return rows


class Rule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = (unit("A::s", 30, 200, 0.8, {32: 0.70, 64: 0.92, 128: 0.97})
                + unit("B::s", 30, 20, 0.8, {})
                + unit("C::s", 30, 200, 0.2, {32: 0.3, 64: 0.4, 128: 0.5})
                + unit("D::s", 30, 1000, 0.8, {32: 0.3, 64: 0.45, 128: 0.6})
                + unit("E::s", 30, 200, 0.8, {32: 0.95, 64: 0.96, 128: 0.97}, guides=40, guides_kept={32: 30, 64: 39})
                + unit("F::s", 30, 200, 0.8, {32: 0.95, 64: 0.96, 128: 0.97}, targets=3)
                + unit("G::s", 30, 200, 0.8, {32: 0.95, 64: 0.96, 128: 0.97}, sign=0.5)
                + unit("H::s", 10, 200, 0.8, {32: 0.95, 64: 0.96, 128: 0.97}))
        cls.df = pd.DataFrame(rows)
        cls.doc = NR.decide(cls.df, CAPS)

    def status(self, u):
        return {c: self.doc["units"][u]["levels"][str(c)]["status"] for c in CAPS}

    def test_smallest_sufficient_level(self):
        self.assertEqual(self.status("A::s"), {32: "insufficient", 64: "sufficient", 128: "sufficient"})
        self.assertEqual(self.doc["units"]["A::s"]["recommended"], {"level": 64, "why": "sufficient"})

    def test_whole_groups_lose_nothing(self):
        self.assertEqual(self.status("B::s")[32], "no_loss")
        self.assertEqual(self.doc["units"]["B::s"]["recommended"], {"level": 32, "why": "no_loss"})

    def test_not_measurable_is_not_judged(self):
        self.assertEqual(set(self.status("C::s").values()), {"not_judgeable"})
        self.assertEqual(self.doc["units"]["C::s"]["recommended"], {"level": 128, "why": "not_judgeable"})
        self.assertEqual(self.doc["units"]["C::s"]["levels"]["32"]["groups_not_measurable"], 30)

    def test_above_the_largest_cap(self):
        self.assertEqual(set(self.status("D::s").values()), {"insufficient"})
        self.assertEqual(self.doc["units"]["D::s"]["recommended"], {"level": None, "why": "above"})

    def test_guides_guard(self):
        lv = self.doc["units"]["E::s"]["levels"]
        self.assertEqual([lv[str(c)]["guard_passed"] for c in CAPS], [False, False, True])
        self.assertEqual(self.doc["units"]["E::s"]["recommended"], {"level": 128, "why": "sufficient"})

    def test_few_targets_or_few_groups_not_judged(self):
        self.assertEqual(set(self.status("F::s").values()), {"not_judgeable"})       # no generic response to remove
        self.assertEqual(set(self.status("H::s").values()), {"not_judgeable"})       # 10 groups read, below MIN_GROUPS

    def test_sign_threshold(self):
        self.assertEqual(set(self.status("G::s").values()), {"insufficient"})

    def test_totals(self):
        t = self.doc["totals"]
        self.assertEqual(t["cells_full"], int(self.df["cells"].sum()))
        self.assertEqual(t["32"], int(self.df["cells_32"].sum()))
        # A at 64, B whole, C at 128 (not judgeable), D above (all its cells), E at 128, F at 128, G above, H at 128
        want = (30 * 64) + (30 * 20) + (30 * 128) + (30 * 1000) + (30 * 128) + (30 * 128) + (30 * 200) + (10 * 128)
        self.assertEqual(t["at_recommended_levels"], want)

    def test_r_pred(self):
        self.assertAlmostEqual(float(NR.r_pred(200, 0.5, 128)), 0.9177, places=3)
        self.assertAlmostEqual(float(NR.r_pred(200, 0.8, 64)), 0.8994, places=3)
        self.assertAlmostEqual(float(NR.r_pred(200, 0.5, 200)), 1.0, places=9)

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.df.to_csv(d / "groups.csv.gz", index=False, compression="gzip")
            run = lambda *extra: subprocess.run([sys.executable, str(HERE / "nested_rule.py"), "--groups",
                                                 str(d / "groups.csv.gz"), *map(str, extra)],
                                                capture_output=True, text=True)
            (d / "train.json").write_text(json.dumps({"classes": "train", "holdout_group": "LINE"}), encoding="utf-8")
            (d / "all.json").write_text(json.dumps({"classes": "all", "holdout_group": "LINE"}), encoding="utf-8")
            r = run("--manifest", d / "train.json", "--out", d / "out")
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            doc = json.loads((d / "out" / "decision.json").read_text(encoding="utf-8"))
            self.assertEqual((doc["rule"], doc["fold_holdout_group"], doc["exploratory"]), (NR.RULE, "LINE", False))
            self.assertIn("| `A::s` |", (d / "out" / "decision.md").read_text(encoding="utf-8"))
            self.assertNotEqual(run("--manifest", d / "train.json", "--out", d / "out").returncode, 0)   # never over
            # a table that read every class decides nothing: refused, or described as exploratory
            self.assertNotEqual(run("--manifest", d / "all.json", "--out", d / "out_all").returncode, 0)
            self.assertNotEqual(run("--out", d / "out_none").returncode, 0)            # no manifest, no decision
            self.assertFalse((d / "out_all").exists() or (d / "out_none").exists())
            e = run("--manifest", d / "all.json", "--exploratory", "--out", d / "out_expl")
            self.assertEqual(e.returncode, 0, e.stderr[-2000:])
            self.assertFalse((d / "out_expl" / "decision.json").exists())
            self.assertTrue(json.loads((d / "out_expl" / "exploratory.json").read_text(encoding="utf-8"))["exploratory"])
            self.assertIn("non utilizzabile", (d / "out_expl" / "exploratory.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
