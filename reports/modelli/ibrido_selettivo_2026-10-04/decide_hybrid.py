"""The reading rules of the D-056 hybrid v1 (PROTOCOLLO.md §8–§10), written before any output of the protocol was read.

Inputs, per line: its role (dev or conf), the training's acceptance.json (accept_training.py), lane A summary.json
and lane B scaled_local.csv (hybrid_lanes.py), and lane B's parity.json. Writes decision.json:
- technical: each line accepted (§10) and lane B parity passed (ibrido_w0 cells equal to transfer's);
- development (dev lines, selector leave-one-line-out): passed when ibrido_selettivo - transfer on the local six-member
  mean is > 0 in at least 2 of the 3 dev lines with mean > 0 AND the mean weight on lane B targets is >= 0.05 on the
  lines; 'selector at zero' when the mean weight is < 0.05 on every dev line (no neural contribution shown, whatever
  the scores);
- confirmation (conf lines, frozen selector): ibrido_selettivo - transfer > 0 on every evaluated conf line, with the
  lane A guard (C-row PDS ibrido_selettivo - transfer >= -0.02); one line reads 'confirmed on one line';
- secondaries without thresholds: rete - transfer, miscela_fissa - transfer, ibrido_selettivo - miscela_fissa,
  rete - rete_mean (state contribution), selettivo_mean - transfer, the members one by one, the transfer references;
- the bench score of §9 for each arm: the mean over the pre-registered lines (dev with leave-one-line-out weights and
  conf with the frozen system) of the six-member local mean, equal weight per line; complete only when every line
  has the arm; eligible for grading at >= 0.100, which is not a promotion.

    python decide_hybrid.py --line H1 dev <train fetched dir> <laneA dir> <laneB dir> --line ... --out <new dir>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

THRESH_W = 0.05
GUARD = -0.02
GRADING = 0.100
MEMBERS = ("PDS", "MSE", "NMAE", "FID", "REACH", "JAC", "avg")
ARMS = ("transfer", "ibrido_w0", "rete", "miscela_fissa", "ibrido_selettivo", "rete_mean", "selettivo_mean",
        "transfer_cells_J", "transfer_prod_J")


def read_line(name, role, train, lane_a, lane_b):
    acc = json.loads((Path(train) / "acceptance.json").read_text(encoding="utf-8"))
    sa = json.loads((Path(lane_a) / "summary.json").read_text(encoding="utf-8"))
    sc = pd.read_csv(Path(lane_b) / "bench" / "scaled_local.csv", index_col=0)
    par = json.loads((Path(lane_b) / "parity.json").read_text(encoding="utf-8"))
    bench = json.loads((Path(lane_b) / "bench" / "bench.json").read_text(encoding="utf-8"))
    wmean = (bench.get("meta") or bench).get("weights", {}).get("w_selective_mean", {}) if isinstance(bench, dict) else {}
    return {"name": name, "role": role, "accepted": bool(acc["accepted"]), "parity": bool(par["cells_equal"]),
            "avg": {arm: float(sc.loc[arm, "avg"]) for arm in sc.index if arm in ARMS},
            "members": {arm: {m: float(sc.loc[arm, m]) for m in MEMBERS} for arm in sc.index if arm in ARMS},
            "laneA_C": sa["means"]["C"], "laneA_J": sa["means"].get("J", {}),
            "w_selective_ibrido_laneA": sa.get("w_selective_ibrido"), "w_fixed": sa.get("w_fixed"),
            "w_selective_mean_laneB": wmean, "acceptance": acc}


def diff(lines, a, b):
    return {L["name"]: (L["avg"][a] - L["avg"][b]) if a in L["avg"] and b in L["avg"] else None for L in lines}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=5, action="append", required=True,
                   metavar=("NAME", "ROLE", "TRAIN", "LANE_A", "LANE_B"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    lines = [read_line(*x) for x in a.line]
    dev = [L for L in lines if L["role"] == "dev"]
    conf = [L for L in lines if L["role"] == "conf"]
    technical = {L["name"]: {"accepted": L["accepted"], "parity": L["parity"]} for L in lines}
    ok = all(v["accepted"] and v["parity"] for v in technical.values())

    def wmean(L):
        v = L["w_selective_mean_laneB"].get("ibrido") if L["w_selective_mean_laneB"] else None
        return v if v is not None else (L["w_selective_ibrido_laneA"] or {}).get("mean")

    out = {"protocol": "reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md §8–§10", "technical": technical,
           "technical_ok": ok, "lines": {L["name"]: {k: L[k] for k in ("role", "avg", "members", "laneA_C", "laneA_J",
                                                                           "w_fixed", "w_selective_ibrido_laneA",
                                                                           "w_selective_mean_laneB")} for L in lines}}
    if dev:
        d = diff(dev, "ibrido_selettivo", "transfer")
        vals = [v for v in d.values() if v is not None]
        w = {L["name"]: wmean(L) for L in dev}
        at_zero = all(v is not None and v < THRESH_W for v in w.values())
        passed = (len(vals) == len(dev) and sum(v > 0 for v in vals) >= 2 and sum(vals) / len(vals) > 0
                  and all(v is not None and v >= THRESH_W for v in w.values()))
        out["development"] = {"selective_minus_transfer": d, "mean": sum(vals) / len(vals) if vals else None,
                              "lines_positive": sum(v > 0 for v in vals), "mean_weight": w,
                              "outcome": ("selettore a zero" if at_zero else
                                          "contributo neurale nello sviluppo" if passed else "non passa"),
                              "rule": "§8: > 0 in >= 2 of 3 dev lines, mean > 0, mean weight >= 0.05 on the lines"}
    if conf:
        d = diff(conf, "ibrido_selettivo", "transfer")
        guard = {L["name"]: (L["laneA_C"].get("ibrido_selettivo", {}).get("pds", float("nan"))
                             - L["laneA_C"].get("transfer", {}).get("pds", float("nan"))) for L in conf}
        good = all(v is not None and v > 0 for v in d.values()) and all(g >= GUARD for g in guard.values())
        out["confirmation"] = {"selective_minus_transfer": d, "laneA_guard": guard,
                               "outcome": ("confermato su una linea" if good and len(conf) == 1 else
                                           "confermato" if good else "non confermato"),
                               "mean_weight": {L["name"]: wmean(L) for L in conf}}
    out["secondary"] = {"rete-transfer": diff(lines, "rete", "transfer"),
                        "miscela_fissa-transfer": diff(lines, "miscela_fissa", "transfer"),
                        "selettivo-miscela_fissa": diff(lines, "ibrido_selettivo", "miscela_fissa"),
                        "rete-rete_mean": diff(lines, "rete", "rete_mean"),
                        "selettivo_mean-transfer": diff(lines, "selettivo_mean", "transfer"),
                        "transfer_cells_J-transfer_prod_J": diff(lines, "transfer_cells_J", "transfer_prod_J"),
                        "transfer-transfer_prod_J": diff(lines, "transfer", "transfer_prod_J")}
    score = {}
    for arm in ARMS:
        vals = [L["avg"].get(arm) for L in lines]
        complete = all(v is not None for v in vals)
        s = sum(vals) / len(vals) if complete else None
        score[arm] = {"score": s, "complete": complete, "lines": [L["name"] for L in lines],
                      "eligible_for_grading": bool(complete and ok and s is not None and s >= GRADING)}
    out["bench_score_section_9"] = score
    a.out.mkdir(parents=True)
    (a.out / "decision.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k in ("technical_ok", "development", "confirmation")}, indent=1))


if __name__ == "__main__":
    main()
