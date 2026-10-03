"""The pilot's rule on made-up outputs with known answers: Q1 passes when cells beat mean in two lines of three with a
positive mean; a collapsed arm makes its comparisons missing, not negative; a training with loss shares off by more
than 0.02 is not usable.

    python -m unittest test_decide_pilot -v       (from this folder, with the project venv)
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
ARMS = ("cells", "mean", "generic", "transfer_cells", "transfer_all", "generic_pseudobulk")


def fake_line(root: Path, g: str, pds: dict, shares=(0.5, 0.5), pi_q50=None):
    train, lane = root / f"train_{g}", root / f"lane_{g}"
    train.mkdir()
    lane.mkdir()
    (train / "coverage.json").write_text(json.dumps({
        "leakage_check": {"passed": True}, "epochs_done": 2.0,
        "loss_shares": {"by_group": {"A": shares[0], "B": shares[1]}}}), encoding="utf-8")
    for arm in ("cells", "mean", "generic"):
        (train / arm).mkdir()
        (train / arm / "eval.json").write_text(json.dumps({"summary": {"evaluation": {"complete": True}}}),
                                               encoding="utf-8")
    pq = pi_q50 or {}
    (train / "train_log.jsonl").write_text(json.dumps({"msg": "step", "arms": {
        arm: {"pi_q50": pq.get(arm, 0.5), "responsibility_mean": 0.0 if pq.get(arm) == 0.01 else 0.4}
        for arm in ("cells", "mean", "generic")}}) + "\n", encoding="utf-8")
    (train / "config.json").write_text(json.dumps({"args": {"pi_floor": "0.01"}}), encoding="utf-8")
    rng = np.random.default_rng(0)
    rows = []
    for i in range(40):
        for arm in ARMS:
            base = pds.get(arm, 0.6)
            rows.append({"table": "t", "target_key": f"K{i}", "cls": "C" if i < 30 else "J", "arm": arm,
                         "pds": base + rng.normal(0, 0.01), "cos_spec": 0.1, "cos": 0.2, "mse_ratio": 1.0,
                         "sign_sig": 0.5})
    pd.DataFrame(rows).to_csv(lane / f"per_target_{g}.csv.gz", index=False, compression="gzip")
    return [g, str(train), str(lane)]


def decide(lines, out):
    args = [sys.executable, str(HERE / "decide_pilot.py"), "--out", str(out)]
    for line in lines:
        args += ["--line", *line]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        raise AssertionError(proc.stderr[-2000:])
    return json.loads((out / "decision.json").read_text(encoding="utf-8"))


class Rule(unittest.TestCase):
    def test_q1_two_of_three(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lines = [fake_line(d, "H1", {"cells": 0.70, "mean": 0.60, "generic": 0.5}),
                     fake_line(d, "HepG2", {"cells": 0.70, "mean": 0.65, "generic": 0.5}),
                     fake_line(d, "RPE1", {"cells": 0.60, "mean": 0.62, "generic": 0.5})]
            r = decide(lines, d / "out")
            q1 = r["comparisons"]["Q1_state"]["C"]["pds"]
            self.assertEqual(q1["lines_positive"], 2)
            self.assertTrue(q1["passed"])
            self.assertTrue(r["outcome"]["Q3_target_used"])
            self.assertTrue(r["outcome"]["expand_on_lane_A"])

    def test_one_of_three_fails(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lines = [fake_line(d, "H1", {"cells": 0.70, "mean": 0.60}),
                     fake_line(d, "HepG2", {"cells": 0.60, "mean": 0.65}),
                     fake_line(d, "RPE1", {"cells": 0.60, "mean": 0.62})]
            self.assertFalse(decide(lines, d / "out")["comparisons"]["Q1_state"]["C"]["pds"]["passed"])

    def test_collapse_and_shares_make_lines_missing(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lines = [fake_line(d, "H1", {"cells": 0.70, "mean": 0.60}, pi_q50={"mean": 1e-5}),
                     fake_line(d, "HepG2", {"cells": 0.70, "mean": 0.60}, shares=(0.6, 0.4)),
                     fake_line(d, "RPE1", {"cells": 0.70, "mean": 0.60})]
            r = decide(lines, d / "out")
            self.assertEqual(r["technical"]["H1"]["collapsed"], ["mean"])
            self.assertFalse(r["usable"]["HepG2"])
            q1 = r["comparisons"]["Q1_state"]["C"]["pds"]
            self.assertEqual(q1["lines"], 1)                      # only RPE1 counts
            self.assertFalse(q1["passed"])                        # one positive line is less than two


class GateAtTheFloor(unittest.TestCase):
    def test_the_pilot_r1_case_is_a_collapse(self):
        # pi_q50 = 0.01 = the floor, responsibility 0: the letter of §6 (pi_q50 < 1e-3) missed it; §8 catches it
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            floor = {"cells": 0.01, "mean": 0.01, "generic": 0.01}
            lines = [fake_line(d, g, {"cells": 0.70, "mean": 0.60}, pi_q50=floor) for g in ("H1", "HepG2", "RPE1")]
            r = decide(lines, d / "out")
            self.assertEqual(r["technical"]["H1"]["collapsed"], ["cells", "generic", "mean"])
            self.assertEqual(r["comparisons"]["Q1_state"]["C"]["pds"]["lines"], 0)
            self.assertFalse(r["outcome"]["expand_on_lane_A"])


if __name__ == "__main__":
    unittest.main()
