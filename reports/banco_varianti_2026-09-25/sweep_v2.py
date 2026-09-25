"""Seventh pass, after review: shrinkage measured with the production loader and fair comparisons.

The review of 25 September (claude2, run `20260925-005016-r11-review-bench-claude2` in the
agent hub, copied in `revisioni/` next to this script) found that `shrink_sweep.py`,
`noise_sim.py`, `controls.py` and `noise_sim2.py` recomputed the shrinkage from an SE that
``cd4_mix`` does not have (all NaN): CD4 became a vote for zero, and the variants were scored
on different targets. Their zk numbers are therefore confounded; `analyze.py`'s ``shrunk_g1``
(the cache's own shrinkage, k 4 on each CD4 condition) was not.

This pass:
* loads every source through stage 100's own `load_table` (imported from the script), so
  ``zshrink`` rebuilds ``cd4_mix`` from its three conditions, each shrunk with its SE;
* scores every arm on ONE target set per held-out source: targets where every arm predicts;
* adds ``raw_noCD4`` (the raw recipe without CD4) to separate source choice from shrinkage;
* reports paired per-target differences against ``raw`` with a bootstrap over targets
  (2,000 resamples, seed 20260925);
* repeats the comparison through a model of the trial-01 profile step (clip at 6 log2,
  compositional shift) and of the Poisson noise of a 400-cell pseudobulk, at amplitude rules
  that cannot blow up single genes: the t15 amplitude 0.394 on the shrunk effects, and the q99
  rule with |ln fc| capped at 2.

    scripts/py.cmd reports/banco_varianti_2026-09-25/sweep_v2.py --out reports/banco_varianti_2026-09-25/r7
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from analyze import DATA, FAMILY, SOURCES, pds_proxy  # noqa: E402
from noise_sim import rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage100", REPO / "scripts" / "100_build_context_effects.py")
stage100 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage100)

SEED = 20260925
N_BOOT = 2000
SEEDS = (1, 2, 3)


def pooled(cache, preds, targets, effect, k=None):
    tabs = [stage100.load_table(cache, s, effect, k) for s in preds]
    eff, den = mix(tabs, targets, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
    eff[den == 0] = 0.0
    return eff, den


def boot(diff, rng):
    idx = rng.integers(0, diff.size, size=(N_BOOT, diff.size))
    means = diff[idx].mean(axis=1)
    return float(diff.mean()), [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel if g in col])
    keep = np.ones(axis.size, dtype=bool)
    keep[panel_cols] = False
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_mean = basal[["A", "B", "C"]].mean(axis=1).to_numpy(dtype=float)
    xm = 0.05 * cpm_mean
    w_mean = xm / (1.0 + xm)

    summary, sim_rows = [], []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base = [t for t in panel if t in tidx]
        arms = {"raw": pooled(args.cache, preds, base, "raw")}
        for k in (4.0, 16.0, 64.0):
            arms[f"zk{int(k)}"] = pooled(args.cache, preds, base, "zshrink", k)
        if "cd4_mix" in preds and len(preds) > 1:
            arms["raw_noCD4"] = pooled(args.cache, [p for p in preds if p != "cd4_mix"], base, "raw")
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e, _ in arms.values()], axis=0)
        targets = [t for t, o in zip(base, ok) if o]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float64)
        per = {name: pds_proxy(e[ok], T, w_mean, panel_cols) for name, (e, _) in arms.items()}
        rng = np.random.default_rng(SEED)
        for name, v in per.items():
            mean_diff, ci = boot(v - per["raw"], rng) if name != "raw" else (0.0, [0.0, 0.0])
            summary.append({"held_out": held, "predictors": "+".join(preds), "targets": len(targets),
                            "arm": name, "pds_proxy": float(v.mean()), "minus_raw": mean_diff,
                            "minus_raw_ci95": ci, "share_targets_better": float((v > per["raw"]).mean())})

        # the same comparison through the trial-01 profile step and pseudobulk noise
        observed = arms["raw"][1][ok] > 0
        raw = arms["raw"][0][ok]
        q99_t15 = float(np.median(np.quantile(np.abs(raw * 0.394), 0.99, axis=1)))
        sim_arms = {"raw@0.394": raw * 0.394, "raw@0.788": raw * 0.788}
        for name in ("zk16", "zk64"):
            e = arms[name][0][ok]
            q99 = float(np.median(np.quantile(np.abs(e), 0.99, axis=1)))
            sim_arms[f"{name}@0.394"] = e * 0.394
            sim_arms[f"{name}@q99cap2"] = np.clip(e * q99_t15 / q99, -2.0, 2.0)
        sim_per = {name: [] for name in sim_arms}
        diag = {name: {"shift": [], "moved": []} for name in sim_arms}
        for c in ("A", "B", "C"):
            cpm = basal[c].to_numpy(dtype=float)
            x = 0.05 * cpm
            live = keep & (cpm > 0)
            Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(T), -20, 20))) - np.log1p(x))[:, live]
            for name, E in sim_arms.items():
                for seed in SEEDS:
                    noisy, cshift, real_ln = realise(E, cpm, observed, np.random.default_rng(seed))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, live]
                    sim_per[name].append(rank_pds(D, Tl))
                    diag[name]["shift"].append(float(np.median(np.abs(cshift))))
                    diag[name]["moved"].append(float(np.median((np.abs(real_ln) > 0.1).sum(axis=1))))
        ref = np.mean(sim_per["raw@0.394"], axis=0)
        for name, runs in sim_per.items():
            v = np.mean(runs, axis=0)
            mean_diff, ci = boot(v - ref, rng) if name != "raw@0.394" else (0.0, [0.0, 0.0])
            sim_rows.append({"held_out": held, "targets": len(targets), "arm": name, "pds_proxy_generator": float(v.mean()),
                             "minus_raw@0.394": mean_diff, "ci95": ci,
                             "median_abs_comp_shift_log2": float(np.mean(diag[name]["shift"])),
                             "median_genes_moved_gt_0.1ln": float(np.mean(diag[name]["moved"])),
                             "max_abs_ln_fc": float(np.abs(sim_arms[name]).max())})
        print(held, "done", flush=True)

    s = pd.DataFrame(summary)
    g = pd.DataFrame(sim_rows)
    s.to_csv(args.out / "no_noise.csv", index=False)
    g.to_csv(args.out / "generator_model.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/sweep_v2.py", "claim_type":
                   "effect-space proxy with stage 100's loader, one target set per held-out source, paired "
                   "bootstrap over targets; the generator arms use a model; not VCC scores",
                   "cache": str(args.cache), "seed": SEED, "n_boot": N_BOOT,
                   "no_noise": s.to_dict("records"), "generator_model": g.to_dict("records")}, f, indent=1)
    pd.set_option("display.width", 200)
    print(s.drop(columns=["predictors"]).round(4).to_string())
    print(g.round(4).to_string())


if __name__ == "__main__":
    main()
