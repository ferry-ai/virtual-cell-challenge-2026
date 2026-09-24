"""Fourth pass: does the shrinkage gain survive the generator's sampling noise and amplitude?

The official PDS is computed on generated cells, not on effects. This pass adds a model of
that step to the PDS proxy of analyze.py:

* predicted delta, per official context: log1p(x * exp(a * e + eps)) - log1p(x), with
  x = 0.05 * CPM (bulk_target_sum 5e4), ``a`` the amplitude, ``e`` the pooled effect and
  eps ~ N(0, 1 / (n * mu)) the Poisson noise of a pseudobulk mean over n = 400 generated
  cells at mu = CPM * 20,000 / 1e6 counts per cell (library size variance ignored);
* held-out truth: the same log1p map of the held-out source's raw effect, NaN -> 0.

Variants: the t15 recipe (raw effects) at amplitudes 0.197, 0.394, 0.788 and 1.576 (t11, t15,
t16 and the next doubling), and local shrinkage zk16 / zk64 at the amplitude that gives the
t15 median q99 |a * e| (0.229) and at twice it. Three noise seeds. A model, not a
measurement of the generator: it ignores overdispersion, library sizes and the zero
inflation that drives the Wilcoxon calls.

    scripts/py.cmd reports/banco_varianti_2026-09-25/noise_sim.py --out reports/banco_varianti_2026-09-25/r4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analyze import DATA, FAMILY, SOURCES  # noqa: E402
from shrink_sweep import table  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402

N_CELLS = 400
UMI = 20000.0
Q99_T15 = 0.229091
SEEDS = (1, 2, 3)


def rank_pds(A, B):
    na = np.linalg.norm(A, axis=1)
    nb = np.linalg.norm(B, axis=1)
    cos = (A @ B.T) / np.maximum(np.outer(na, nb), 1e-12)
    d = np.diag(cos)
    n = cos.shape[0]
    greater = (cos > d[:, None]).sum(axis=1)
    ties = (cos == d[:, None]).sum(axis=1) - 1
    return 1.0 - (greater + 0.5 * ties) / max(n - 1, 1)


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
    keep = np.ones(axis.size, dtype=bool)
    keep[[col[g] for g in panel if g in col]] = False
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)

    rows = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = table(args.cache, held, None)
        tidx = truth.index()
        base_targets = [t for t in panel if t in tidx]
        pooled = {}
        for name, k in (("raw", None), ("zk16", 16.0), ("zk64", 64.0)):
            tabs = [table(args.cache, s, k) for s in preds]
            P, den = mix(tabs, base_targets, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
            P[den == 0] = 0.0
            pooled[name] = P
        has = np.abs(pooled["raw"]).sum(axis=1) > 0
        targets = [t for t, h in zip(base_targets, has) if h]
        T = np.nan_to_num(truth.raw[np.array([tidx[t] for t in targets])].astype(np.float64))
        arms = [("raw", a) for a in (0.197, 0.394, 0.788, 1.576)]
        for name in ("zk16", "zk64"):
            q99 = float(np.median(np.quantile(np.abs(pooled[name][has]), 0.99, axis=1)))
            arms += [(name, Q99_T15 / q99), (name, 2 * Q99_T15 / q99)]
        for c in ("A", "B", "C"):
            cpm = basal[c].to_numpy(dtype=float)
            x = 0.05 * cpm
            mu = cpm * UMI / 1e6
            sd = np.where(mu > 0, 1.0 / np.sqrt(N_CELLS * np.maximum(mu, 1e-12)), 0.0)
            live = keep & (cpm > 0)
            Tl = (np.log1p(x * np.exp(np.clip(T, -20, 20))) - np.log1p(x))[:, live]
            for name, amp in arms:
                E = pooled[name][has] * amp
                vals = []
                for seed in SEEDS:
                    eps = np.random.default_rng(seed).standard_normal(E.shape) * sd
                    D = (np.log1p(x * np.exp(np.clip(E + eps, -20, 20))) - np.log1p(x))[:, live]
                    vals.append(float(rank_pds(D, Tl).mean()))
                q99 = float(np.median(np.quantile(np.abs(E), 0.99, axis=1)))
                rows.append({"held_out": held, "context": c, "variant": name, "amplitude": round(amp, 4),
                             "median_q99_abs": q99, "pds_proxy_noisy": float(np.mean(vals)),
                             "pds_proxy_noisy_sd_seeds": float(np.std(vals)), "targets": len(targets)})
            print(held, c, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / "noise_sim.csv", index=False)
    summary = (df.groupby(["held_out", "variant", "amplitude"])[["median_q99_abs", "pds_proxy_noisy"]]
                 .mean().round(4).reset_index())
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/noise_sim.py", "claim_type":
                   "model of generated pseudobulk noise on an effect-space proxy; not VCC scores",
                   "n_cells": N_CELLS, "umi": UMI, "seeds": SEEDS, "q99_t15": Q99_T15,
                   "summary": summary.to_dict("records")}, f, indent=1)
    print(summary.to_string())


if __name__ == "__main__":
    main()
