"""r4: does the two-channel gain of r3 survive the generator's profile step and pseudobulk noise?

Uses the predictions r3 saved (processed/lct_r3_predictions_2026-09-26: t20like and lct_c per
held-out task, nested folds). Arms: t20like and t20_rw<a> = t20like x (|lct_c| / its per-target
mean)^a, a = 0.25, 0.5, scaled to t20like's median detectable genes; both passed through the model
of the trial-01 profile step and a 400-cell pseudobulk (reports/banco_varianti_2026-09-25/noise_sim2.
realise; A, B, C basal profiles; seeds 1-3), PDS on log1p deltas (noise_sim.rank_pds), panel genes
excluded. Paired bootstrap over targets. Proxies, not VCC scores.

    scripts/py.cmd reports/trasferimento_appreso_2026-09-26/generator_check_r3.py --out reports/trasferimento_appreso_2026-09-26/r4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))

from cis_bench import DATA, SEED, boot  # noqa: E402
from noise_sim import rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402

TASKS = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", type=Path, default=DATA / "processed/lct_r3_predictions_2026-09-26")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    keep = np.ones(axis.size, dtype=bool)
    keep[[col[g] for g in panel if g in col]] = False
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_mean = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    mu = cpm_mean * 20000 / 1e6
    thr = np.where(mu > 0, 4.0 / np.sqrt(400 * np.maximum(mu, 1e-12)), np.inf)
    gate = cpm_mean >= 5.0
    det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))
    rng = np.random.default_rng(SEED)
    rows = []
    for task in TASKS:
        z = np.load(args.pred / f"{task}.npz")
        t20, P, T = z["t20like"].astype(np.float32), z["lct_c"].astype(np.float32), z["truth"]
        mag = np.abs(P)
        mean = mag.mean(axis=1, keepdims=True)
        target_det = det(t20)
        arms = {"t20like": t20}
        for a in (0.25, 0.5):
            E = t20 * np.power(np.divide(mag, mean, out=np.zeros_like(mag), where=mean > 0), a)
            lo, hi = 1e-3, 1e4
            for _ in range(50):
                mid = np.sqrt(lo * hi)
                lo, hi = (mid, hi) if det(mid * E) < target_det else (lo, mid)
            arms[f"t20_rw{a}"] = E * np.sqrt(lo * hi)
        observed = np.abs(t20) > 0
        res = {}
        for name, E in arms.items():
            runs = []
            for c in ("A", "B", "C"):
                cpm = basal[c].to_numpy(dtype=float)
                x = 0.05 * cpm
                live = keep & (cpm > 0)
                Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(T), -20, 20))) - np.log1p(x))[:, live]
                for seed in (1, 2, 3):
                    noisy, _, _ = realise(E, cpm, observed, np.random.default_rng([seed, ord(c)]))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, live]
                    runs.append(rank_pds(D, Tl))
            res[name] = np.mean(runs, axis=0)
        for name, v in res.items():
            row = {"held_out": task, "arm": name, "targets": int(v.size), "pds_gen": float(v.mean())}
            if name != "t20like":
                d, ci = boot(v - res["t20like"], rng)
                row["minus_t20like"], row["ci95"] = d, ci
            rows.append(row)
        print(task, "done", flush=True)
    s = pd.DataFrame(rows)
    s.to_csv(args.out / "generator_check.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_appreso_2026-09-26/generator_check_r3.py",
                   "claim_type": "generator-model proxies against held-out public sources; not VCC scores", "rows": rows}, fh, indent=1)
    print(s.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
