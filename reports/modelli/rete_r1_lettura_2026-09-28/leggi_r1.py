"""Read the r1 rule of the multi-context network (reports/modelli/rete_contesti_2026-09-27/RISULTATI.md, fixed at 22:03
on 27/09) on score_pred.py's outputs for the seed-averaged run folders, and the seed-sign condition on the three
seeds' own metrics.json.

The rule, transcribed:
* E1 (truths k562, cd4_Rest, orion_hct116, orion_hek293t, kolf), context use net - blind on the combined proxy, all
  targets: passes if positive on >= 4 of 5, with the interval above zero on >= 2 and no interval entirely below
  -0.002 (reversed signs pass the reverse). Candidate net - excl: the same rule. Diagnostic: net - swap.
* E2 per pair (orion_hct116 + orion_hek293t; cd4_Rest + cd4_Stim48hr): the network's mean correlation of predicted and
  observed differences passes if its interval is above zero and the mean exceeds the permutations' 97.5 % quantile;
  both pairs pass, or one (partial).
* J (k562, orion_hct116): net - fallback (partners) passes if positive on both, interval above zero on >= 1.
* The rule holds only if the sign of net - blind is the same in the three seeds on >= 4 of the 5 E1 truths. score_pred
  scores the seed average only; the per-seed sign here is the one of each seed's own metrics.json (effect-space
  skill, train.py's diagnostic) - a different measure from the combined proxy, declared as such in the report.

    scripts/py.cmd reports/modelli/rete_r1_lettura_2026-09-28/leggi_r1.py --scores <score_r1_avg> \
        --seeds <out_r1_s0_v2> <r1-s1 metrics root> <r1-s2 metrics root> --out <new dir>
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

import pandas as pd

E1 = {"e1_k562": "k562", "e1_cd4": "cd4_Rest", "e1_hct116": "orion_hct116", "e1_hek293t": "orion_hek293t",
      "e1_kolf": "kolf"}
E2 = {"e2_orion": ("orion_hct116", "orion_hek293t"), "e2_cd4": ("cd4_Rest", "cd4_Stim48hr")}
J = {"j_k562": "k562", "j_hct116": "orion_hct116"}
FLOOR = -0.002


def ci(v) -> list:
    return v if isinstance(v, list) else ast.literal_eval(str(v))


def row(scores: Path, design: str, truth: str, arm: str, against: str) -> dict | None:
    f = scores / design / "summary.csv"
    if not f.exists():
        return None
    s = pd.read_csv(f)
    r = s[(s.held_out == truth) & (s.stratum == "all") & (s.arm == arm) & (s.against == against)]
    if r.empty:
        return None
    r = r.iloc[0]
    lo, hi = ci(r.combined_ci95)
    return {"design": design, "truth": truth, "contrast": f"{arm}-{against}", "mean": float(r.combined_minus),
            "lo": float(lo), "hi": float(hi), "targets": int(r.targets)}


def e1_rule(rows: list) -> dict:
    pos = sum(r["mean"] > 0 for r in rows)
    neg = sum(r["mean"] < 0 for r in rows)
    ci_up = sum(r["lo"] > 0 for r in rows)
    ci_down = sum(r["hi"] < 0 for r in rows)
    below = sum(r["hi"] < FLOOR for r in rows)
    above_rev = sum(r["lo"] > -FLOOR for r in rows)
    return {"truths": len(rows), "positive": pos, "ci_above_0": ci_up, "ci_entirely_below_-0.002": below,
            "passes": bool(len(rows) == 5 and pos >= 4 and ci_up >= 2 and below == 0),
            "reverse_passes": bool(len(rows) == 5 and neg >= 4 and ci_down >= 2 and above_rev == 0)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--seeds", type=Path, nargs=3, required=True, help="folders with <design>_s<k>/metrics.json")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    out, table = {}, []
    for contrast in (("net", "blind"), ("net", "excl"), ("net", "swap"), ("own_m", "excl")):
        rows = [r for d, t in E1.items() if (r := row(args.scores, d, t, *contrast)) is not None]
        table += rows
        out[f"E1 {contrast[0]}-{contrast[1]}"] = {"rows": rows, **e1_rule(rows)}
    j_rows = [r for d, t in J.items() if (r := row(args.scores, d, t, "net", "partners")) is not None]
    table += j_rows
    out["J net-partners"] = {"rows": j_rows,
                             "passes": bool(len(j_rows) == 2 and all(r["mean"] > 0 for r in j_rows)
                                            and any(r["lo"] > 0 for r in j_rows))}
    e2 = {}
    for d, pair in E2.items():
        f = args.scores / d / "e2.csv"
        if not f.exists():
            continue
        s = pd.read_csv(f)
        net = s[s.arm == "net"] if "arm" in s.columns else s
        e2[d] = net.to_dict(orient="records")
    out["E2"] = e2
    seeds = {}
    for d in E1:
        signs = []
        for k, root in enumerate(args.seeds):
            m = root / f"{d}_s{k}" / "metrics.json"
            if m.exists():
                j = json.loads(m.read_text())
                ctx = j["contexts"][E1[d]]
                signs.append(float(ctx["contrasts"]["net-blind"]["all"]["skill"]["mean"]))
        seeds[d] = signs
    same = {d: (len(v) == 3 and (all(x > 0 for x in v) or all(x < 0 for x in v))) for d, v in seeds.items()}
    out["seed_signs_effect_space"] = {"per_design": seeds, "same_sign": same,
                                      "holds_on_4_of_5": bool(sum(same.values()) >= 4)}
    pd.DataFrame(table).to_csv(args.out / "contrasts.csv", index=False)
    with (args.out / "readout.json").open("x", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    for k, v in out.items():
        if isinstance(v, dict) and "passes" in v:
            print(k, {kk: vv for kk, vv in v.items() if kk != "rows"})
    print("E2", json.dumps(e2, default=str)[:1500])
    print("seeds", out["seed_signs_effect_space"])


if __name__ == "__main__":
    main()
