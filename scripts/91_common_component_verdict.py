"""Stage 91: apply `configs/common_component_rule.yaml` -- KEEP or DISCARD the common component.

Four benches: a tune and an eval bench on HepG2 (stage 75, t03's recipe) and on the official
targets in K562 (stage 73, no-effect base). On each tune bench the weight w* maximising the
bench's metric is chosen; on the matching eval bench, at w* only, the variant must beat both
the base arm and its own permuted control by `min_gain`. Both benches must pass.

    python scripts/91_common_component_verdict.py --rule configs/common_component_rule.yaml \
        --run <MyDrive/vcc2026/runs/common_2026-09-18> \
        --t03-status reports/trial_2026-09-17/status_0TbVAwhVTj6UYpaU2v9d.json \
        --anchors reports/anchors_2026-09-17/anchors.json --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

MEMBERS = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae",
           "de_wilcoxon_direction_fidelity_yield_raw", "de_wilcoxon_direction_reach_raw",
           "de_wilcoxon_sig_jaccard"]


def predicted_official(bench: dict, arm: str, base_arm: str, status: dict, anchors: dict) -> float:
    """Stage 84's formula with the base arm as calibration point (t03's own recipe)."""
    res = bench["results"]
    total = 0.0
    for m in MEMBERS:
        a = anchors.get(m)
        if a is None:           # mse: anchors unsolved, clipped to 0 in every scored entry
            continue
        pred = res[arm]["raw"][m] * status[m] / res[base_arm]["raw"][m]
        total += (pred - a["baseline"]) / (a["replicate"] - a["baseline"])
    return total / len(MEMBERS)


def local_avg(bench: dict, arm: str) -> float:
    return bench["results"][arm]["scaled_local"]["avg"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rule", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True, help="directory holding hepg2_tune/ hepg2_eval/ k562_tune/ k562_eval/")
    p.add_argument("--t03-status", type=Path, required=True)
    p.add_argument("--anchors", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "verdict.json").exists():
        raise SystemExit(f"{args.out} already holds a verdict; choose a new --out")
    rule = yaml.safe_load(args.rule.read_text(encoding="utf-8"))
    status = json.loads(args.t03_status.read_text(encoding="utf-8-sig"))
    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))["anchors"]
    grid, gain = [float(w) for w in rule["grid"]], float(rule["min_gain"])
    dirs = {"hepg2": ("hepg2_tune", "hepg2_eval"), "k562_official": ("k562_tune", "k562_eval")}

    out: dict[str, dict] = {}
    problems: list[str] = []
    for name, spec in rule["benches"].items():
        tune = json.loads((args.run / dirs[name][0] / "bench.json").read_text(encoding="utf-8"))
        ev = json.loads((args.run / dirs[name][1] / "bench.json").read_text(encoding="utf-8"))
        base = spec["base_arm"]

        def metric(bench, arm, _name=name, _base=base):
            if _name == "hepg2":
                return predicted_official(bench, arm, _base, status, anchors)
            return local_avg(bench, arm)

        def arm_name(template, w):
            return template.replace("{w}", _wstr(w))

        # validity
        overlap = set(tune.get("targets", [])) & set(ev.get("targets", []))
        if not tune.get("targets") or not ev.get("targets"):
            problems.append(f"{name}: a bench did not record its targets")
        if overlap:
            problems.append(f"{name}: {len(overlap)} targets shared by tune and eval")
        for b, lbl in ((tune, "tune"), (ev, "eval")):
            ct = b.get("common_term") or {}
            if "n_excluded" not in ct:
                problems.append(f"{name}.{lbl}: no common_term record")
        needed_tune = [base] + [arm_name(spec["variant_arm"], w) for w in grid]
        needed_eval = needed_tune + [arm_name(spec["control_arm"], w) for w in grid]
        for arms, b, lbl in ((needed_tune, tune, "tune"), (needed_eval, ev, "eval")):
            missing = [a for a in arms if a not in b["results"]]
            if missing:
                problems.append(f"{name}.{lbl}: missing arms {missing}")
        if any(pr.startswith(name) for pr in problems):
            out[name] = {"passes": False, "void": True}
            continue

        # tune: w* over {0} U grid, ties to the smaller w
        scores = {0.0: metric(tune, base)} | {w: metric(tune, arm_name(spec["variant_arm"], w)) for w in grid}
        best = max(scores.values())
        w_star = min(w for w, s in scores.items() if s == best)
        # eval at w* only; the rest reported
        table = {}
        for w in grid:
            v, c = arm_name(spec["variant_arm"], w), arm_name(spec["control_arm"], w)
            table[_wstr(w)] = {"variant": metric(ev, v), "control": metric(ev, c),
                               "d_base": metric(ev, v) - metric(ev, base), "d_perm": metric(ev, v) - metric(ev, c),
                               "sig_t_variant": ev["results"][v]["n_sig_per_target"],
                               "sig_t_control": ev["results"][c]["n_sig_per_target"]}
        d = table.get(_wstr(w_star)) if w_star > 0 else None
        passes = bool(d) and d["d_base"] >= gain and d["d_perm"] >= gain
        out[name] = {"metric": spec["metric"].strip()[:80] + "...", "tune_scores": {_wstr(k): v for k, v in scores.items()},
                     "w_star": w_star, "eval_base": metric(ev, base),
                     "eval_at_w_star": d, "passes": passes,
                     "eval_all_w_not_decisive": table,
                     "sig_t_base_eval": ev["results"][base]["n_sig_per_target"],
                     "targets": {"tune": len(tune["targets"]), "eval": len(ev["targets"])},
                     "common_term": {"tune": tune.get("common_term"), "eval": ev.get("common_term")}}

    keep = not problems and all(v.get("passes") for v in out.values())
    verdict = "KEEP" if keep else "DISCARD"
    weight = min(out[n]["w_star"] for n in out) if keep else None
    payload = {"stage": "91_common_component_verdict", "finished_utc": datetime.now(timezone.utc).isoformat(),
               "rule": str(args.rule), "rule_version": rule.get("version"),
               "rule_md5": hashlib.md5(args.rule.read_bytes()).hexdigest(),
               "run": str(args.run), "t03_status": str(args.t03_status), "min_gain": gain,
               "validity_problems": problems, "benches": out, "verdict": verdict, "weight_for_submission": weight}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "verdict.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for n, v in out.items():
        if v.get("void"):
            print(f"{n}: VOID")
            continue
        d = v["eval_at_w_star"]
        print(f"{n}: w*={v['w_star']:g} tune={ {k: round(s, 4) for k, s in v['tune_scores'].items()} }")
        print(f"   eval base={v['eval_base']:+.4f} " + (f"d_base={d['d_base']:+.4f} d_perm={d['d_perm']:+.4f} "
              f"sig/t {v['sig_t_base_eval']:.0f}->{d['sig_t_variant']:.0f} (perm {d['sig_t_control']:.0f})"
              if d else "(w*=0: nothing to evaluate)") + f"  -> {'PASS' if v['passes'] else 'FAIL'}")
    for pr in problems:
        print("  problem:", pr)
    print(f"VERDICT: {verdict}" + (f"  (weight {weight:g})" if weight else ""))
    print(f"wrote {args.out / 'verdict.json'}")


def _wstr(w: float) -> str:
    """Arm names carry the grid values as written in the rule: 0.1, 0.25, 0.5, 1.0, 2.0."""
    if w == 0:
        return "0"
    return f"{w:.2f}".rstrip("0") if w < 1 else f"{w:.1f}"


if __name__ == "__main__":
    main()
