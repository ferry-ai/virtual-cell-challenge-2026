"""The full Orion design and the file partition, on made-up data with known answers: with the k of orion_full_v1 every
eligible cell is selected with pi = 1, every control is kept and no cell failing the guide filter is; --part i/n splits
the frozen list into disjoint parts whose union is the whole list.

    python -m unittest test_full -v               (from this folder, with the project venv)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import campionamento_v2 as cv  # noqa: E402
import orion_job as oj  # noqa: E402


class Full(unittest.TestCase):
    def test_full_design_selects_every_eligible_cell(self):
        spec = json.loads((HERE / "specs/orion_full_v1.json").read_text(encoding="utf-8"))
        d = spec["design"]
        rng = np.random.default_rng(0)
        n = 3000
        obs = pd.DataFrame({"gem_file": rng.choice(["g1", "g2", "g3"], n),
                            "target": rng.choice([f"T{i}" for i in range(40)] + ["Non-Targeting"], n),
                            "pass_guide_filter": (rng.random(n) > 0.1).astype(int)},
                           index=[f"c{i}" for i in range(n)])
        obs["is_control"] = obs["target"] == "Non-Targeting"
        s = cv.select_orion(obs, "HCT116", d["salt"], d["k"], d["name"], None)
        ok = s["role"] != "excluded"
        self.assertEqual(int(ok.sum()), int((obs["pass_guide_filter"] == 1).sum()))
        self.assertTrue(s.loc[ok, "selected"].all())
        self.assertTrue((s.loc[ok, "pi"] == 1.0).all())
        self.assertFalse(s.loc[~ok, "selected"].any())

    def test_parts_are_disjoint_and_cover(self):
        files = [{"name": f"f{i}"} for i in range(109)]
        parts = [oj.part_of(files, f"{i}/4") for i in range(4)]
        names = [f["name"] for p in parts for f in p]
        self.assertEqual(sorted(names), sorted(f["name"] for f in files))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(oj.part_of(files, None), files)
        with self.assertRaises(ValueError):
            oj.part_of(files, "4/4")


if __name__ == "__main__":
    unittest.main()
