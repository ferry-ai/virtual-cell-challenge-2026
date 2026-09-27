"""Paired contrasts between arms of the HepG2 bench scored with the real metrics (stage 75, Colab job 046).

Reads the job's outputs (``bench.json`` and the ``per_pert_<arm>.csv`` files, long format: perturbation,
metric, value), checks that the mean of each member's per-target values reproduces the aggregate the job
reported, then for each contrast A - B puts the per-target differences on the scale of the local anchors
(replicate = 1, baseline = 0: divided by replicate - baseline, sign flipped for nMAE, where lower is better) and
bootstraps targets (the same resample for every member; NaN-aware means, nMAE exists for fewer targets). The
mean over members counts the MSE member as 0: it is clipped at 0 in every arm. Local anchors on a half-depth
truth, not VCC scores.

    scripts/py.cmd reports/banco_hepg2_v2_2026-09-26/confronti.py --job-dir <runs/bench_hepg2_v2_2026-09-26/h001> \
        --out reports/banco_hepg2_v2_2026-09-26/r1/confronti.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

MEMBERS = {  # per-target metric -> (aggregate key in bench.json, higher is better)
    "pds_cosine": ("pds_cosine", True),
    "de_wilcoxon_lfc_nmae": ("de_wilcoxon_lfc_nmae", False),
    "de_wilcoxon_direction_fidelity_yield_raw": ("de_wilcoxon_direction_fidelity_yield_raw", True),
    "de_wilcoxon_direction_reach_raw": ("de_wilcoxon_direction_reach_raw", True),
    "de_wilcoxon_sig_jaccard": ("de_wilcoxon_sig_jaccard", True),
}
N_MEMBERS = 6          # the MSE member adds 0 to every difference
CONTRASTS = [
    ("g0:t19like_a2.0", "g0:t19like_a1.0"),
    ("g0:t16like_a2.0", "g0:t16like_a1.0"),
    ("g0:t19like_a1.0", "g0:t16like_a1.0"),
    ("g0:t19like_a1.0+cisonly_a1.0", "g0:t19like_a1.0"),
    ("g0:t19like_a1.0+cisonly_a2.0", "g0:t19like_a1.0"),
    ("g0:t16like_a1.0+cisonly_a1.0", "g0:t16like_a1.0"),
    ("g0:t19like_a1.0", "g0:t19like_a0.5"),
    ("g0:t16like_a1.0", "g0:t16like_a0.5"),
]
N_BOOT = 2000


def per_target(job: Path, arm: str) -> pd.DataFrame:
    name = arm.replace(":", " ")
    frame = pd.read_csv(job / f"per_pert_{name}.csv")
    return frame.pivot_table(index="perturbation", columns="metric", values="value", aggfunc="first")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    bench = json.loads((args.job_dir / "bench.json").read_text(encoding="utf-8"))
    res = bench["results"]
    anchor_r, anchor_b = res["replicate"]["raw"], res["baseline"]["raw"]
    tables = {arm: per_target(args.job_dir, arm) for a_b in CONTRASTS for arm in a_b}
    checks = []
    for arm, tab in tables.items():
        for metric, (key, _) in MEMBERS.items():
            got, want = float(np.nanmean(tab[metric])), float(res[arm]["raw"][key])
            checks.append(abs(got - want))
    print(f"aggregate check: max |mean of per-target - reported| = {max(checks):.2e}")
    rng = np.random.default_rng(20260927)
    rows = []
    for a, b in CONTRASTS:
        ta, tb = tables[a], tables[b]
        targets = ta.index.intersection(tb.index)
        diffs = {}
        for metric, (key, higher) in MEMBERS.items():
            scale = anchor_r[key] - anchor_b[key]
            d = (ta.loc[targets, metric] - tb.loc[targets, metric]).to_numpy(float) / scale
            diffs[metric] = d
        n = len(targets)
        idx = rng.integers(0, n, size=(N_BOOT, n))
        boot_avg = np.zeros(N_BOOT)
        row = {"arm": a, "against": b, "targets": n}
        for metric, d in diffs.items():
            est = float(np.nanmean(d))
            draws = np.nanmean(d[idx], axis=1)
            boot_avg += draws / N_MEMBERS
            row[f"{metric}"] = est
            row[f"{metric}_ci95"] = [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]
        row["mean_of_members"] = float(sum(np.nanmean(d) for d in diffs.values()) / N_MEMBERS)
        row["mean_of_members_ci95"] = [float(np.quantile(boot_avg, 0.025)), float(np.quantile(boot_avg, 0.975))]
        rows.append(row)
        print(f"{a} - {b}: mean {row['mean_of_members']:+.4f} "
              f"({row['mean_of_members_ci95'][0]:+.4f}..{row['mean_of_members_ci95'][1]:+.4f}), n={n}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
