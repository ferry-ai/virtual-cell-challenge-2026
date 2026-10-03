"""The rule of the version 4 pilot (PROTOCOLLO.md §5 and §7 of this folder), on the three pre-registered lines.

A copy of version 3's reader (reports/modelli/rete_ancorata_2026-10-03/decide_anchored.py) with the acceptance and
the references of version 4. Inputs, per held-out line: the training folder (as the kernel leaves it), the lane A
folder (bench_effects.py: per_target_<line>.csv.gz) and the lane B table (the bench's scaled_local.csv of lane_b.py).
Writes decision.json:
- technical acceptance per training (§5): decide_pilot.technical with the arms of version 4 (its loss-share check is
  replaced by exposure.json: every complete window and the run within the tolerance, every unit drawn), the evaluation
  complete for the trained arms and ancora_sola, and the anchors recorded by the training: manifest checks passed and
  regime-J table means;
- primary, lane B: ancorata_shift - transfer_all_J on the local six-member mean, passed when > 0 in at least two lines
  and the mean of the three > 0; a line without a technically accepted training makes it incomplete, not failed;
- guard, lane A: the mean over the three lines of (ancorata - transfer_all_J) PDS on the C rows >= -0.02; primary
  passed and guard failed reads "non concluso";
- secondaries without a threshold (§7).

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
REFERENCE = "transfer_all_J"
MEMBERS = ("PDS", "MSE", "NMAE", "FID", "REACH", "JAC", "avg")


def anchors_ok(train: Path) -> dict:
    cfg = json.loads((train / "config.json").read_text(encoding="utf-8")) if (train / "config.json").is_file() else {}
    anc = cfg.get("anchors") or {}
    checks = anc.get("manifest_checks") or {}
    commons = anc.get("commons") or {}
    return {"summary": anc, "regime_J": commons.get("regime") == "J",
            "passed": bool(anc) and bool(checks.get("passed")) and commons.get("regime") == "J"}


def exposure_ok(train: Path) -> dict:
    f = train / "exposure.json"
    if not f.is_file():
        return {"present": False, "passed": False}
    e = json.loads(f.read_text(encoding="utf-8"))
    return {"present": True, "passed": bool(e.get("passed")), "run_max_abs_deviation": e.get("run_max_abs_deviation"),
            "complete_windows": e.get("complete_windows"), "windows_out_of_rule": len(e.get("windows_out_of_rule", [])),
            "units_never_drawn": e.get("units_never_drawn")}


def technical(train: Path) -> dict:
    out = DP.technical(train)
    out["exposure"] = exposure_ok(train)
    out["anchors"] = anchors_ok(train)
    # version 4: exposure.json replaces the run-level loss shares of version 3 (which pass also for a run that read a
    # unit only at the end); the other items of decide_pilot.technical are kept
    out["accepted"] = bool(out.get("coverage_present") and out.get("leakage_passed") and out["exposure"]["passed"]
                           and (out["health"] or {}).get("passed") and out["verify_present"]
                           and not out.get("shards_differ") and out["return_code"] == 0
                           and all(out["evaluation_complete"].values()) and out["anchors"]["passed"])
    return out


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
        tech[g] = technical(Path(train))
        frames[g] = pd.read_csv(Path(lane) / f"per_target_{g}.csv.gz", keep_default_na=False, na_values=["", "nan", "NaN"])
        tables[g] = pd.read_csv(table, index_col=0)
    ok = {g: tech[g]["accepted"] for g in lines}
    nan = float("nan")
    primary = DP.rule({g: lane_b(tables[g], "ancorata_shift", REFERENCE) if ok[g] else nan for g in lines}, need)
    guard_d = {g: DP.paired(frames[g], "ancorata", REFERENCE, "pds") if ok[g] else nan for g in lines}
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
    pairs_b = (("ancorata_shift", REFERENCE), ("ancorata_shift", "ancora_sola_shift"),
               ("ancorata_shift", "ancorata_mean_shift"), ("ancorata_shift", "transfer_cells_J"),
               ("ancorata_shift", "transfer_prod_J"), ("ancorata_cells", REFERENCE),
               ("transfer_all_J", "transfer_cells_J"), ("transfer_all_J", "transfer_prod_J"))
    pairs_a = (("ancorata", "ancora_sola"), ("ancorata", "ancorata_mean"), ("ancora_sola", REFERENCE),
               ("ancorata", "transfer_cells_J"), ("ancorata", "transfer_prod_J"), ("transfer_all_J", "transfer_cells_J"),
               ("transfer_all_J", "transfer_prod_J"))
    secondary = {
        "laneB_by_member": {m: {f"{x}-{y}": {g: lane_b(tables[g], x, y, m) for g in lines} for x, y in pairs_b}
                            for m in MEMBERS},
        "laneA_C_pds": {f"{x}-{y}": {g: DP.paired(frames[g], x, y, "pds") for g in lines} for x, y in pairs_a},
        "laneA_J_pds": {f"{x}-{y}": {g: DP.paired(frames[g], x, y, "pds", cls="J") for g in lines}
                        for x, y in (("ancorata", "ancora_sola"), ("ancorata", "ancorata_mean"))}}
    result = {"protocol": "rete_ancorata_v4_2026-10-03/PROTOCOLLO.md §5 and §7", "lines": lines, "technical": tech,
              "accepted": ok, "primary_laneB": primary, "guard_laneA": guard, "outcome": outcome,
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
