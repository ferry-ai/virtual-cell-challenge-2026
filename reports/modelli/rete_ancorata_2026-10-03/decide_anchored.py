"""The rule of the transfer-anchored pilot (PROTOCOLLO.md §6, frozen at 4cb61d4), on the three pre-registered lines.

Inputs, per held-out line: the training folder (as the kernel leaves it), the lane A folder (bench_effects.py:
per_target_<line>.csv.gz) and the lane B table (the bench's scaled_local.csv of lane_b.py). Writes decision.json:
- technical acceptance per training: decide_pilot.technical with the arms of version 3 (ancorata, ancorata_mean and
  the evaluation-only ancora_sola) and the anchor checks the training recorded (config.json, manifest checks passed);
- primary, lane B: ancorata_shift - transfer_cells on the local six-member mean, passed when > 0 in at least two lines
  and the mean of the three > 0; a line without a technically accepted training makes it incomplete, not failed;
- guard, lane A: the mean over the three lines of (ancorata - transfer_cells) PDS on the C rows >= -0.02; primary
  passed and guard failed reads "non concluso";
- secondaries without a threshold: ancorata - ancora_sola and ancorata - ancorata_mean in both lanes, the J rows, every
  member of lane B.

    py.cmd decide_anchored.py --line H1 <training> <laneA> <laneB scaled_local.csv> --line HepG2 ... --line RPE1 ...
        --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import decide_pilot as DP

DP.ARMS_REQUIRED = ("ancorata", "ancorata_mean", "ancora_sola")
GUARD = -0.02
MEMBERS = ("PDS", "MSE", "NMAE", "FID", "REACH", "JAC", "avg")


def anchors_ok(train: Path) -> dict:
    cfg = json.loads((train / "config.json").read_text(encoding="utf-8")) if (train / "config.json").is_file() else {}
    anc = cfg.get("anchors") or {}
    checks = anc.get("manifest_checks") or {}
    return {"summary": anc, "passed": bool(anc) and bool(checks.get("passed"))}


def lane_b(table: pd.DataFrame, x: str, y: str, member: str = "avg") -> float:
    if x not in table.index or y not in table.index:
        return float("nan")
    return float(table.loc[x, member] - table.loc[y, member])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=4, action="append", required=True,
                   metavar=("GROUP", "TRAINING", "LANE_A", "LANE_B_TABLE"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    lines = [x[0] for x in a.line]
    if sorted(lines) != sorted(DP.PREREGISTERED) or len(set(lines)) != len(lines):
        raise SystemExit(f"the rule reads exactly the pre-registered lines {DP.PREREGISTERED}, got {lines}")
    need = math.ceil(2 / 3 * len(lines))
    tech, frames, tables = {}, {}, {}
    for g, train, lane, table in a.line:
        tech[g] = DP.technical(Path(train))
        tech[g]["anchors"] = anchors_ok(Path(train))
        tech[g]["accepted"] = bool(tech[g]["accepted"] and tech[g]["anchors"]["passed"])
        frames[g] = pd.read_csv(Path(lane) / f"per_target_{g}.csv.gz", keep_default_na=False, na_values=["", "nan", "NaN"])
        tables[g] = pd.read_csv(table, index_col=0)
    ok = {g: tech[g]["accepted"] for g in lines}
    nan = float("nan")
    primary = DP.rule({g: lane_b(tables[g], "ancorata_shift", "transfer_cells") if ok[g] else nan for g in lines}, need)
    guard_d = {g: DP.paired(frames[g], "ancorata", "transfer_cells", "pds") if ok[g] else nan for g in lines}
    guard_complete = all(np.isfinite(v) for v in guard_d.values())
    guard_mean = float(np.mean(list(guard_d.values()))) if guard_complete else nan
    guard = {"by_line": guard_d, "mean": guard_mean, "complete": guard_complete,
             "passed": bool(guard_complete and guard_mean >= GUARD), "threshold": GUARD}
    if not primary["complete"] or not guard_complete:
        outcome = "incompleto"
    elif primary["passed"] and guard["passed"]:
        outcome = "passa"
    elif primary["passed"]:
        outcome = "non concluso"
    else:
        outcome = "non passa"
    secondary = {
        "laneB_by_member": {m: {f"{x}-{y}": {g: lane_b(tables[g], x, y, m) for g in lines}
                                for x, y in (("ancorata_shift", "transfer_cells"), ("ancorata_shift", "ancora_sola_shift"),
                                             ("ancorata_shift", "ancorata_mean_shift"),
                                             ("ancorata_cells", "transfer_cells"),
                                             ("transfer_cells", "transfer_cells_r3"))}
                            for m in MEMBERS},
        "laneA_C_pds": {f"{x}-{y}": {g: DP.paired(frames[g], x, y, "pds") for g in lines}
                        for x, y in (("ancorata", "ancora_sola"), ("ancorata", "ancorata_mean"),
                                     ("ancora_sola", "transfer_cells"))},
        "laneA_J_pds": {f"{x}-{y}": {g: DP.paired(frames[g], x, y, "pds", cls="J") for g in lines}
                        for x, y in (("ancorata", "ancora_sola"), ("ancorata", "ancorata_mean"))}}
    result = {"protocol": "rete_ancorata_2026-10-03/PROTOCOLLO.md §6, frozen at 4cb61d4", "lines": lines,
              "technical": tech, "accepted": ok, "primary_laneB": primary, "guard_laneA": guard, "outcome": outcome,
              "secondary": secondary,
              "local_avg": {g: {k: round(float(v), 5) for k, v in tables[g]["avg"].items()} for g in lines}}
    a.out.mkdir(parents=True)
    (a.out / "decision.json").write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"outcome": outcome, "primary": {k: primary[k] for k in ("by_line", "macro", "lines_positive",
                                                                              "status")},
                      "guard": {k: guard[k] for k in ("by_line", "mean", "passed")}, "accepted": ok}, indent=1,
                     default=float))


if __name__ == "__main__":
    main()
