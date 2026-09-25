"""Sixth pass: which amplitude rule makes shrunk effects safe through the real generator step?

`noise_sim.py` matched the median q99 |ln fc| of t15. For shrunk effects that needs a factor of
about 9.6 (t15 sources, k 64), which pushes a few strong genes to the generator's clip
(|log2 fc| 6) and makes `inference.compositional_shift` lower every other observed gene. This
pass adds both steps of `vcc2026.inference.predicted_profile` to the model:

    d = clip(a * e / ln 2, -6, 6) on observed genes; c = log2(sum b / sum b * 2^d);
    profile = b * 2^(d + c); then Poisson noise of a 400-cell mean and log1p at 5e4.

Amplitude rules compared, for zk16 and zk64 (raw effects at 0.394 = t15 as reference):
* ``t15amp``: the t15 amplitude 0.394 on the shrunk effects (no gene exceeds its t15 value
  once shrunk: |zk * 0.394| <= |raw * 0.394|);
* ``q99``: the median q99 |ln fc| of t15 (0.229), as in noise_sim.py;
* ``l2``: the median per-target L2 norm of the t15 effects;
* ``q99cap2``: q99 rule, then |ln fc| capped at 2.

Reported per arm: the PDS proxy, the median |compositional shift| in log2 and the median
number of genes whose realised |ln fc| exceeds 0.1 (a crude stand-in for how many genes the
generator would move enough to call). Three noise seeds, contexts A/B/C.

    scripts/py.cmd reports/banco_varianti_2026-09-25/noise_sim2.py --out reports/banco_varianti_2026-09-25/r6
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
from noise_sim import N_CELLS, UMI, rank_pds  # noqa: E402
from shrink_sweep import table  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402

SEEDS = (1, 2, 3)
LN2 = np.log(2.0)


def realise(E, basal_cpm, observed, rng):
    """ln fold change realised by the generator's profile step, plus pseudobulk noise."""
    d = np.clip(E / LN2, -6.0, 6.0)
    b = basal_cpm[None, :] * observed
    moved = (b * np.exp2(d)).sum(axis=1)
    flat = b.sum(axis=1)
    c = np.log2(np.divide(flat, moved, out=np.ones_like(flat), where=moved > 0))
    real_ln = np.where(observed, (d + c[:, None]) * LN2, 0.0)
    mu = basal_cpm * UMI / 1e6 * np.exp(real_ln)
    sd = np.where(mu > 0, 1.0 / np.sqrt(N_CELLS * np.maximum(mu, 1e-12)), 0.0)
    noisy = real_ln + rng.standard_normal(E.shape) * sd
    return noisy, c, real_ln


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
        pooled, weight = {}, None
        for name, k in (("raw", None), ("zk16", 16.0), ("zk64", 64.0)):
            tabs = [table(args.cache, s, k) for s in preds]
            P, den = mix(tabs, base_targets, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
            P[den == 0] = 0.0
            pooled[name] = P
            weight = den
        has = np.abs(pooled["raw"]).sum(axis=1) > 0
        targets = [t for t, h in zip(base_targets, has) if h]
        observed = weight[has] > 0
        T = np.nan_to_num(truth.raw[np.array([tidx[t] for t in targets])].astype(np.float64))
        ref = pooled["raw"][has] * 0.394
        ref_q99 = float(np.median(np.quantile(np.abs(ref), 0.99, axis=1)))
        ref_l2 = float(np.median(np.linalg.norm(ref, axis=1)))
        arms = [("raw", "t15amp", ref)]
        for name in ("zk16", "zk64"):
            E = pooled[name][has]
            q99 = float(np.median(np.quantile(np.abs(E), 0.99, axis=1)))
            l2 = float(np.median(np.linalg.norm(E, axis=1)))
            arms += [(name, "t15amp", E * 0.394), (name, "q99", E * ref_q99 / q99), (name, "l2", E * ref_l2 / l2),
                     (name, "q99cap2", np.clip(E * ref_q99 / q99, -2.0, 2.0))]
        for c in ("A", "B", "C"):
            cpm = basal[c].to_numpy(dtype=float)
            x = 0.05 * cpm
            live = keep & (cpm > 0)
            Tl = (np.log1p(x * np.exp(np.clip(T, -20, 20))) - np.log1p(x))[:, live]
            for name, rule, E in arms:
                vals, shifts, moved = [], [], []
                for seed in SEEDS:
                    noisy, cshift, real_ln = realise(E, cpm, observed, np.random.default_rng(seed))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, live]
                    vals.append(float(rank_pds(D, Tl).mean()))
                    shifts.append(float(np.median(np.abs(cshift))))
                    moved.append(float(np.median((np.abs(real_ln) > 0.1).sum(axis=1))))
                rows.append({"held_out": held, "context": c, "variant": name, "rule": rule,
                             "pds_proxy_generator": float(np.mean(vals)),
                             "median_abs_comp_shift_log2": float(np.mean(shifts)),
                             "median_genes_moved_gt_0.1ln": float(np.mean(moved)),
                             "max_abs_ln_fc": float(np.abs(E).max())})
            print(held, c, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / "noise_sim2.csv", index=False)
    summary = (df.groupby(["held_out", "variant", "rule"])[["pds_proxy_generator", "median_abs_comp_shift_log2",
                                                            "median_genes_moved_gt_0.1ln", "max_abs_ln_fc"]]
                 .mean().round(4).reset_index())
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/noise_sim2.py", "claim_type":
                   "model of the trial-01 profile step (clip, compositional shift) and pseudobulk noise "
                   "on an effect-space proxy; not VCC scores", "seeds": SEEDS,
                   "summary": summary.to_dict("records")}, f, indent=1)
    print(summary.to_string())


if __name__ == "__main__":
    main()
