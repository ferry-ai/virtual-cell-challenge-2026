"""The rule of the pilot (PROTOCOLLO.md §6), applied to the outputs of the trainings and of lane A.

Inputs, per held-out line: the training output folder (coverage.json, train_log.jsonl, <arm>/eval.json, verify.json and
kernel_done.json of the kernel when present) and the lane A folder of bench_effects.py. Writes decision.json:
technical acceptance per training, collapse per arm, Q1 (cells - mean), Q2 (cells - transfer_cells), Q3
(cells - generic) on the PDS of the C rows, with the secondary indices and the J rows reported, and the expansion
outcome. Nothing here is tuned on the results: thresholds are the protocol's.

    py.cmd decide_pilot.py --line H1 <training> <laneA> --line HepG2 <training> <laneA> --line RPE1 <training> <laneA>
        --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

METRICS = ("pds", "cos_spec", "cos", "mse_ratio", "sign_sig")
LOWER = {"mse_ratio"}
COLLAPSE = 1e-3                     # pi_q50 of the perturbed cells at the last logged step (PROTOCOLLO §6)
RESP_MIN = 0.01                     # amendment 2.1 (PROTOCOLLO §8): or the gate at its floor, or no responsibility
SHARE_TOL = 0.02                    # loss shares of the line groups within this of 1/G


def technical(train: Path) -> dict:
    out = {}
    cov = json.loads((train / "coverage.json").read_text(encoding="utf-8")) if (train / "coverage.json").is_file() else None
    out["coverage_present"] = cov is not None
    if cov:
        out["leakage_passed"] = bool(cov["leakage_check"]["passed"])
        shares = cov.get("loss_shares", {}).get("by_group", {})
        g = len(shares)
        out["loss_shares_by_group"] = shares
        out["loss_shares_within_tolerance"] = bool(g and all(abs(v - 1 / g) <= SHARE_TOL for v in shares.values()))
        out["epochs_done"] = cov.get("epochs_done")
    verify = train / "verify.json"
    if verify.is_file():
        v = json.loads(verify.read_text(encoding="utf-8"))
        out["shards_differ"] = v.get("differ", v.get("bad"))
    done = train / "kernel_done.json"
    if done.is_file():
        out["return_code"] = json.loads(done.read_text(encoding="utf-8")).get("return_code")
    evals = {}
    for d in sorted(p for p in train.iterdir() if (p / "eval.json").is_file()):
        s = json.loads((d / "eval.json").read_text(encoding="utf-8"))["summary"]
        evals[d.name] = bool(s["evaluation"]["complete"])
    out["evaluation_complete"] = evals
    last, resp = {}, {}
    floor = 0.0
    cfg = train / "config.json"
    if cfg.is_file():
        floor = float(json.loads(cfg.read_text(encoding="utf-8"))["args"].get("pi_floor", 0.0))
    log = train / "train_log.jsonl"
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("msg") == "step":
                arms = r.get("arms") or {"main": r}
                for arm, v in arms.items():
                    if v.get("pi_q50") is not None:
                        last[arm] = v["pi_q50"]
                        resp[arm] = v.get("responsibility_mean")
    out["pi_q50_last"], out["responsibility_last"], out["pi_floor"] = last, resp, floor
    # the letter of §6 (pi_q50 < 1e-3) cannot fire with a floor; amendment §8: the gate at its floor or no responsibility
    out["collapsed"] = sorted(a for a, v in last.items()
                              if v < COLLAPSE or v <= floor + COLLAPSE or (resp.get(a) is not None and resp[a] < RESP_MIN))
    health = train / "health.json"
    out["health"] = json.loads(health.read_text(encoding="utf-8")) if health.is_file() else None
    out["accepted"] = bool(cov and out.get("leakage_passed") and out.get("loss_shares_within_tolerance")
                           and (out["health"] is None or out["health"].get("passed"))
                           and not out.get("shards_differ") and out.get("return_code") in (0, None)
                           and evals and all(evals.values()))
    return out


def paired(df: pd.DataFrame, a: str, b: str, metric: str, cls: str = "C") -> float:
    """Mean over the line's rows of a - b (oriented: higher is better), rows where both are finite."""
    sub = df[df.cls == cls]
    x = sub[sub.arm == a].set_index(["table", "target_key"])[metric]
    y = sub[sub.arm == b].set_index(["table", "target_key"])[metric]
    d = (x - y.reindex(x.index)).dropna()
    if metric in LOWER:
        d = -d
    return float(d.mean()) if len(d) else float("nan")


def rule(deltas: dict, need: int) -> dict:
    v = [x for x in deltas.values() if np.isfinite(x)]
    macro = float(np.mean(v)) if v else float("nan")
    pos = int(sum(x > 0 for x in v))
    return {"by_line": deltas, "macro": macro, "lines_positive": pos, "lines": len(v),
            "passed": bool(v and macro > 0 and pos >= need)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=3, action="append", required=True, metavar=("GROUP", "TRAINING", "LANE_A"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    tech, frames = {}, {}
    for g, train, lane in a.line:
        tech[g] = technical(Path(train))
        frames[g] = pd.read_csv(Path(lane) / f"per_target_{g}.csv.gz", keep_default_na=False,
                                na_values=["", "nan", "NaN"])
    lines = [g for g, _, _ in a.line]
    need = math.ceil(2 / 3 * len(lines))
    usable = {g: tech[g]["accepted"] for g in lines}
    comparisons = {"Q1_state": ("cells", "mean"), "Q2_transfer": ("cells", "transfer_cells"),
                   "Q3_target": ("cells", "generic"), "transfer_all": ("cells", "transfer_all"),
                   "generic_pseudobulk": ("cells", "generic_pseudobulk")}
    result = {"protocol": "PROTOCOLLO.md §6", "lines": lines, "technical": tech, "usable": usable, "comparisons": {}}
    for name, (x, y) in comparisons.items():
        per_metric = {}
        for m in METRICS:
            deltas = {}
            for g in lines:
                bad = set(tech[g]["collapsed"]) & {x, y}
                deltas[g] = (float("nan") if (not usable[g] or bad) else paired(frames[g], x, y, m))
            per_metric[m] = rule(deltas, need)
        j = {g: paired(frames[g], x, y, "pds", cls="J") for g in lines} if name in ("Q1_state", "Q3_target") else None
        result["comparisons"][name] = {"arms": [x, y], "C": per_metric, "J_pds_by_line": j}
    q = result["comparisons"]
    q3_ok = q["Q3_target"]["C"]["pds"]["macro"] > 0
    expand = q["Q1_state"]["C"]["pds"]["passed"] or q["Q2_transfer"]["C"]["pds"]["passed"]
    result["outcome"] = {"Q3_target_used": bool(q3_ok),
                         "Q1_state_passed": q["Q1_state"]["C"]["pds"]["passed"],
                         "Q2_transfer_passed": q["Q2_transfer"]["C"]["pds"]["passed"],
                         "interpretable": bool(q3_ok),
                         "expand_on_lane_A": bool(expand and q3_ok),
                         "lane_B": "applied separately where computed (PROTOCOLLO §5-6)"}
    a.out.mkdir(parents=True)
    (a.out / "decision.json").write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    print(json.dumps(result["outcome"], indent=1))


if __name__ == "__main__":
    main()
