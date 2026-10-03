"""The lane B reading of the pilot on the three pre-registered lines (PROTOCOLLO.md §6: «Corsia B: gli stessi confronti
sul punteggio locale a sei membri, dove calcolato, con la stessa soglia»).

The arms of lane B as §5 defines them: each network arm's own cells ('<arm>_cells') and the transfer through the stage-45
generator ('transfer_cells'). Q1 = cells_cells - mean_cells, Q2 = cells_cells - transfer_cells, Q3 = cells_cells -
generic_cells, on the local six-member mean (column 'avg' of the bench's scaled_local.csv), with decide_pilot.rule: the
mean of the three lines > 0 and > 0 in at least two (Q3: the mean only). The expansion clause of lane B is Q2 (§6). The
networks' shifts through the same generator ('<arm>_shift') are reported apart, without a threshold: they were added to
lane B as a description, they are not §5's arms. A missing arm makes its comparison incomplete.

    py.cmd decide_lane_b.py --line H1 <scaled_local.csv> --line HepG2 <...> --line RPE1 <...> --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from decide_pilot import PREREGISTERED, rule

MEMBERS = ("PDS", "MSE", "NMAE", "FID", "REACH", "JAC", "avg")
REGISTERED = {"Q1_state": ("cells_cells", "mean_cells"), "Q2_transfer": ("cells_cells", "transfer_cells"),
              "Q3_target": ("cells_cells", "generic_cells")}
DESCRIPTIVE = {"shift_state": ("cells_shift", "mean_shift"), "shift_transfer": ("cells_shift", "transfer_cells"),
               "shift_target": ("cells_shift", "generic_shift")}


def delta(table: pd.DataFrame, x: str, y: str, member: str) -> float:
    if x not in table.index or y not in table.index:
        return float("nan")
    return float(table.loc[x, member] - table.loc[y, member])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=2, action="append", required=True, metavar=("GROUP", "SCALED_LOCAL"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    lines = [g for g, _ in a.line]
    if sorted(lines) != sorted(PREREGISTERED) or len(set(lines)) != len(lines):
        raise SystemExit(f"the rule reads exactly the pre-registered lines {PREREGISTERED}, got {lines}")
    tables = {g: pd.read_csv(f, index_col=0) for g, f in a.line}
    need = math.ceil(2 / 3 * len(PREREGISTERED))
    out = {"protocol": "PROTOCOLLO.md §5-6, lane B", "lines": lines, "inputs": dict(a.line),
           "local_avg": {g: {arm: round(float(v), 5) for arm, v in t["avg"].items()} for g, t in tables.items()},
           "registered": {}, "descriptive": {}}
    for block, comps in (("registered", REGISTERED), ("descriptive", DESCRIPTIVE)):
        for name, (x, y) in comps.items():
            per = {m: rule({g: delta(tables[g], x, y, m) for g in lines}, need) for m in MEMBERS}
            out[block][name] = {"arms": [x, y], "by_member": per}
    q1, q2, q3 = (out["registered"][k]["by_member"]["avg"] for k in REGISTERED)
    q3_ok = bool(q3["complete"] and q3["macro"] > 0)
    out["outcome"] = {"Q1_state": q1["status"], "Q2_transfer": q2["status"], "Q3_target_used": q3_ok,
                      "expansion_clause_lane_B": bool(q2["passed"]),
                      "note": "§6: the expansion clause of lane B is the network's cells above the transfer in at "
                              "least two of three lines (Q2 here)"}
    a.out.mkdir(parents=True)
    (a.out / "decision_lane_b.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    show = {k: {g: round(v, 3) for g, v in out["registered"][k]["by_member"]["avg"]["by_line"].items()}
            for k in REGISTERED}
    print(json.dumps({"by_line_avg": show, "outcome": out["outcome"]}, indent=1))


if __name__ == "__main__":
    main()
