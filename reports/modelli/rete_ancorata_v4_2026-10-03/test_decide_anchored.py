"""The rule of the version 4 pilot on made-up outputs with known answers: primary (lane B) and guard (lane A) together
pass; a passing primary with a failed guard reads "non concluso"; a line whose exposure receipt failed, or whose anchors
were not of regime J, is not accepted and the outcome is "incompleto"; a primary positive in one line only does not
pass; the reference is transfer_all_J, not version 3's transfer_cells.

    python -m unittest test_decide_anchored -v    (from this folder, with the project venv; seconds)
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
LINES = ("H1", "HepG2", "RPE1")


def fake(root: Path, g: str, lane_b: dict, pds: dict, exposure=True, regime="J"):
    kernel = root / f"kernel_{g}"
    train = kernel / "train"
    train.mkdir(parents=True)
    (kernel / "kernel_done.json").write_text(json.dumps({"return_code": 0}), encoding="utf-8")
    (train / "verify.json").write_text(json.dumps({"differ": []}), encoding="utf-8")
    (train / "coverage.json").write_text(json.dumps({"leakage_check": {"passed": True}, "epochs_done": 2.0,
                                                     "loss_shares": {"by_group": {"A": 0.9, "B": 0.1}}}), encoding="utf-8")
    (train / "exposure.json").write_text(json.dumps({"passed": exposure, "complete_windows": 60,
                                                     "windows_out_of_rule": [], "run_max_abs_deviation": 0.001,
                                                     "units_never_drawn": []}), encoding="utf-8")
    (train / "config.json").write_text(json.dumps({"args": {"pi_floor": "0.01", "health_check_step": "5000"},
                                                   "anchors": {"rows": 10, "manifest_checks": {"passed": True},
                                                               "commons": {"regime": regime}}}), encoding="utf-8")
    (train / "health.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    for arm in ("ancorata", "ancorata_mean", "ancora_sola"):
        (train / arm).mkdir()
        (train / arm / "eval.json").write_text(json.dumps({"summary": {"evaluation": {"complete": True}}}),
                                               encoding="utf-8")
    (train / "train_log.jsonl").write_text(json.dumps({"msg": "step", "arms": {
        a: {"pi_q50": 1.0, "responsibility_mean": 1.0} for a in ("ancorata", "ancorata_mean")}}) + "\n", encoding="utf-8")
    lane = root / f"laneA_{g}"
    lane.mkdir()
    rng = np.random.default_rng(0)
    rows = [{"table": "t", "target_key": f"K{i}", "cls": "C" if i < 30 else "J", "arm": arm,
             "pds": pds.get(arm, 0.8) + rng.normal(0, 0.001), "cos_spec": 0.1, "cos": 0.2, "mse_ratio": 1.0,
             "sign_sig": 0.5}
            for i in range(40) for arm in ("ancorata", "ancorata_mean", "ancora_sola", "transfer_all_J",
                                           "transfer_cells_J", "transfer_prod_J")]
    pd.DataFrame(rows).to_csv(lane / f"per_target_{g}.csv.gz", index=False, compression="gzip")
    arms = {"replicate": 1.0, "baseline": 0.0, "transfer_all_J": 0.25, "transfer_cells_J": 0.30, "transfer_prod_J": 0.2,
            "ancorata_shift": 0.25, "ancorata_mean_shift": 0.2, "ancora_sola_shift": 0.24, "ancorata_cells": -0.1,
            "ancorata_mean_cells": -0.2, **lane_b}
    table = pd.DataFrame({m: arms for m in ("PDS", "MSE", "NMAE", "FID", "REACH", "JAC", "avg")})
    table.to_csv(root / f"scaled_{g}.csv")
    return [g, str(train), str(lane), str(root / f"scaled_{g}.csv")]


def decide(lines, out):
    args = [sys.executable, str(HERE / "decide_anchored.py"), "--out", str(out)]
    for line in lines:
        args += ["--line", *line]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        raise AssertionError(proc.stderr[-2000:])
    return json.loads((out / "decision.json").read_text(encoding="utf-8"))


class Rule(unittest.TestCase):
    def run_case(self, b, pds, bad_exposure=None, bad_regime=None):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lines = [fake(d, g, {"ancorata_shift": b[i]}, pds, exposure=(g != bad_exposure),
                          regime="C" if g == bad_regime else "J") for i, g in enumerate(LINES)]
            return decide(lines, d / "out")

    def test_passes_against_its_anchor_not_transfer_cells(self):
        # 0.27/0.26/0.26 beat transfer_all_J (0.25) but not transfer_cells_J (0.30): the rule reads transfer_all_J
        r = self.run_case([0.27, 0.26, 0.26], {"ancorata": 0.80, "transfer_all_J": 0.81})
        self.assertEqual(r["outcome"], "passa")
        self.assertLess(r["secondary"]["laneB_by_member"]["avg"]["ancorata_shift-transfer_cells_J"]["H1"], 0)

    def test_passing_the_pilot_is_not_a_promotion(self):
        # amendment §10.4: beating transfer_all_J (0.25) passes the pilot; transfer_prod_J at 0.28 is not beaten
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lines = [fake(d, g, {"ancorata_shift": v, "transfer_prod_J": 0.28}, {"ancorata": 0.80,
                                                                              "transfer_all_J": 0.81})
                     for g, v in zip(LINES, (0.27, 0.26, 0.26))]
            r = decide(lines, d / "out")
        self.assertEqual(r["outcome"], "passa")
        self.assertFalse(r["promotion_requirement"]["met"])
        r2 = self.run_case([0.27, 0.26, 0.26], {"ancorata": 0.80, "transfer_all_J": 0.81})
        self.assertTrue(r2["promotion_requirement"]["met"])       # transfer_prod_J at 0.20 in the default table

    def test_guard_fails(self):
        r = self.run_case([0.27, 0.26, 0.24], {"ancorata": 0.70, "transfer_all_J": 0.81})
        self.assertEqual(r["outcome"], "non concluso")
        self.assertFalse(r["guard_laneA"]["passed"])

    def test_exposure_or_regime_make_it_incomplete(self):
        r = self.run_case([0.27, 0.26, 0.26], {"ancorata": 0.80, "transfer_all_J": 0.81}, bad_exposure="HepG2")
        self.assertFalse(r["accepted"]["HepG2"])
        self.assertEqual(r["outcome"], "incompleto")
        r = self.run_case([0.27, 0.26, 0.26], {"ancorata": 0.80, "transfer_all_J": 0.81}, bad_regime="RPE1")
        self.assertFalse(r["accepted"]["RPE1"])
        self.assertEqual(r["outcome"], "incompleto")

    def test_one_line_does_not_pass(self):
        r = self.run_case([0.30, 0.20, 0.20], {"ancorata": 0.80, "transfer_all_J": 0.81})
        self.assertEqual(r["primary_laneB"]["lines_positive"], 1)
        self.assertEqual(r["outcome"], "non passa")


if __name__ == "__main__":
    unittest.main()
