"""What the D-056 bench measured, member by member, re-read from its stored outputs (no new computation of scores).

For each of the five held-out lines of reports/modelli/ibrido_selettivo_2026-10-04/esito/lanes_*_r1/laneB:
- the six scaled local members of transfer, ibrido_selettivo, rete, miscela_fissa and transfer_prod_J, the raw values
  of replicate and baseline and their difference (the denominator of the local scale), the members that fall outside
  [0, 1], the raw MSE against the baseline's (a scaled MSE of exactly 0 is a truncation);
- ibrido_selettivo - transfer per member, its contribution to the mean of six, and the same difference on the five
  members without JAC;
- targets, control pool, DE calls of the real cells and of each arm.
Across lines: the bench score of PROTOCOLLO §9 recomputed, and its sensitivity (without K562, without JAC, with JAC
clipped to [-1, 1]) labelled as sensitivity, not as a new rule; the sign of each member's local difference against the
official t30 - t25; lane A's PDS of the C rows; the selector's out-of-fold benefit on rows.

    .\\scripts\\py.cmd reports/modelli/diagnosi_t30_2026-10-04/bench_members.py --out <new json>
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ESITO = REPO / "reports/modelli/ibrido_selettivo_2026-10-04/esito"
COMPARISON = REPO / "reports/invii/prediction_t30_2026-10-04/comparison.json"
LINES = {"H1": "dev", "HepG2": "dev", "RPE1": "dev", "Jurkat": "conf", "K562": "conf"}
RAW = {"PDS": "pds_cosine", "MSE": "expr_mse_unbiased_capped_norm", "NMAE": "de_wilcoxon_lfc_nmae",
       "FID": "de_wilcoxon_direction_fidelity_yield_raw", "REACH": "de_wilcoxon_direction_reach_raw",
       "JAC": "de_wilcoxon_sig_jaccard"}
OFFICIAL = {"PDS": "score_pds", "MSE": "score_mse", "NMAE": "score_nmae", "FID": "score_fid", "REACH": "score_reach",
            "JAC": "score_jac"}
ARMS = ("transfer", "ibrido_selettivo", "rete", "miscela_fissa", "transfer_prod_J")
NO_JAC = [m for m in RAW if m != "JAC"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    official = json.loads(COMPARISON.read_text(encoding="utf-8"))["scaled_published"]["t30_minus_t25"]
    decision = json.loads((ESITO / "decision_full_r1/decision.json").read_text(encoding="utf-8"))
    lolo = json.loads((ESITO / "selector_lolo_r1/summary.json").read_text(encoding="utf-8"))
    lines = {}
    for name, role in LINES.items():
        b = json.loads((ESITO / f"lanes_{name.lower()}_r1/laneB/bench/bench.json").read_text(encoding="utf-8"))
        res = b["results"]
        scaled = {arm: {m: float(res[arm]["scaled_local"][RAW[m]]) for m in RAW} for arm in ARMS}
        raw = {arm: {m: float(res[arm]["raw"][RAW[m]]) for m in RAW} for arm in (*ARMS, "replicate", "baseline")}
        denom = {m: raw["replicate"][m] - raw["baseline"][m] for m in RAW}
        delta = {m: scaled["ibrido_selettivo"][m] - scaled["transfer"][m] for m in RAW}
        avg = {arm: float(np.mean(list(v.values()))) for arm, v in scaled.items()}
        avg5 = {arm: float(np.mean([v[m] for m in NO_JAC])) for arm, v in scaled.items()}
        lines[name] = {
            "role": role, "n_targets": b["n_targets"], "control_pool": b["control_pool"], "real_n_conf": b["real_n_conf"],
            "n_sig_per_target": {arm: res[arm]["n_sig_per_target"] for arm in (*ARMS, "replicate", "baseline")},
            "scaled": scaled, "raw": raw, "scale_denominator_replicate_minus_baseline": denom,
            "members_outside_0_1": {arm: {m: v for m, v in scaled[arm].items() if v < 0 or v > 1} for arm in ARMS},
            "mse": {"scaled_all_arms_zero": all(scaled[arm]["MSE"] == 0 for arm in ARMS),
                    "raw_baseline": raw["baseline"]["MSE"], "raw_transfer": raw["transfer"]["MSE"],
                    "raw_hybrid": raw["ibrido_selettivo"]["MSE"],
                    "arms_worse_than_baseline": [arm for arm in ARMS if raw[arm]["MSE"] > raw["baseline"]["MSE"]],
                    "raw_hybrid_minus_transfer": raw["ibrido_selettivo"]["MSE"] - raw["transfer"]["MSE"]},
            "avg": avg, "avg_without_JAC": avg5,
            "hybrid_minus_transfer": {"members": delta, "contribution_to_avg": {m: v / 6 for m, v in delta.items()},
                                      "avg": avg["ibrido_selettivo"] - avg["transfer"],
                                      "avg_without_JAC": avg5["ibrido_selettivo"] - avg5["transfer"],
                                      "share_of_avg_gain_from_JAC": (delta["JAC"] / 6)
                                      / (avg["ibrido_selettivo"] - avg["transfer"]),
                                      "raw_members": {m: raw["ibrido_selettivo"][m] - raw["transfer"][m] for m in RAW}},
            "prod_minus_all_baseline": avg["transfer_prod_J"] - avg["transfer"],
            "laneA_C_pds": {arm: decision["lines"][name]["laneA_C"][arm]["pds"]
                            for arm in ("transfer", "ibrido_selettivo", "rete", "transfer_prod_J")},
            "sign_agrees_with_official_t30_minus_t25": {
                m: bool(np.sign(delta[m]) == np.sign(official[OFFICIAL[m]])) for m in RAW if m != "MSE"}}
    hy = [lines[n]["avg"]["ibrido_selettivo"] for n in LINES]
    tr = [lines[n]["avg"]["transfer"] for n in LINES]
    no_k = [n for n in LINES if n != "K562"]

    def clipped(arm):
        return float(np.mean([np.mean([lines[n]["scaled"][arm][m] if m != "JAC" else
                                       float(np.clip(lines[n]["scaled"][arm][m], -1, 1)) for m in RAW]) for n in LINES]))

    summary = {
        "bench_score_section_9": {"ibrido_selettivo": float(np.mean(hy)), "transfer": float(np.mean(tr)),
                                  "matches_registration": abs(float(np.mean(hy)) - 0.13364541485749845) < 1e-12},
        "sensitivity_not_a_rule": {
            "without_K562": {"ibrido_selettivo": float(np.mean([lines[n]["avg"]["ibrido_selettivo"] for n in no_k])),
                             "transfer": float(np.mean([lines[n]["avg"]["transfer"] for n in no_k]))},
            "without_JAC": {"ibrido_selettivo": float(np.mean([lines[n]["avg_without_JAC"]["ibrido_selettivo"]
                                                               for n in LINES])),
                            "transfer": float(np.mean([lines[n]["avg_without_JAC"]["transfer"] for n in LINES]))},
            "JAC_clipped_to_-1_1": {"ibrido_selettivo": clipped("ibrido_selettivo"), "transfer": clipped("transfer")}},
        "mean_hybrid_minus_transfer_by_member": {m: float(np.mean([lines[n]["hybrid_minus_transfer"]["members"][m]
                                                                   for n in LINES])) for m in RAW},
        "official_t30_minus_t25_by_member": {m: official[OFFICIAL[m]] for m in RAW},
        "lines_agreeing_in_sign_with_official": {
            m: int(sum(lines[n]["sign_agrees_with_official_t30_minus_t25"][m] for n in LINES))
            for m in RAW if m != "MSE"},
        "selector_out_of_fold_rows": {n: {k: lolo["lines"][n]["oof_benefit"]["ibrido"]["selector"][k]
                                          for k in ("rows", "mean_gain", "mean_relative_gain", "share_rows_improved",
                                                    "w_mean")} for n in lolo["lines"]},
        "selector_fit_rows_by_line": {n: lolo["lines"][n]["oof_benefit"]["ibrido"]["selector"]["rows"]
                                      for n in lolo["lines"]},
        "noise": ("one bench seed and one generator stream per arm: the arms after the first differing target draw "
                  "different noise, and no repeated seed measures how much an arm difference moves by itself")}
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "lines": lines, "summary": summary,
           "note": "re-read of stored bench outputs in local scale; not VCC scores; sensitivities are not rules"}
    a.out.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=float))
    for n in LINES:
        x = lines[n]
        print(n, {k: round(v, 4) for k, v in x["hybrid_minus_transfer"]["members"].items()},
              "avg", round(x["hybrid_minus_transfer"]["avg"], 4), "noJAC", round(x["hybrid_minus_transfer"]["avg_without_JAC"], 4),
              "denJAC", round(x["scale_denominator_replicate_minus_baseline"]["JAC"], 4),
              "laneA", x["laneA_C_pds"], "mse", x["mse"]["arms_worse_than_baseline"])


if __name__ == "__main__":
    main()
