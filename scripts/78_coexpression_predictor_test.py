"""Stage 78: does control-cell co-expression predict where a knockdown moves genes?

The only zero-shot signal that reads the TARGET context is the natural covariation
of genes across that context's control cells. If knocking X down moved the genes
that covary with X, a model could learn it from the 18,400 controls of A, B and C.
This tests the premise where it can be tested: HepG2 (Nadig 2024), which has both
control cells and knockdowns.

For 300 seeded HepG2 targets with >= 50 cells, and 2,000 seeded NTC cells:
  effect_X[g] = log2 ratio of mean fractions, X's cells vs NTC cells;
  coexp_X[g]  = correlation of X with g across NTC cells, raw and after removing the
                top 20 principal components (cell state);
  score       = Pearson(coexp_X, effect_X) over expressed genes, excluding X and
                genes within 50 kb of X (the cis effect is measured separately, stage 77).

A measurement on essential-screen targets, in one context. Not a score.

    python scripts/78_coexpression_predictor_test.py --out reports/coexpression_2026-09-17
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vcc2026 import config  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--out", type=Path, required=True)
ARGS = ap.parse_args()
if (ARGS.out / "summary.json").exists():
    raise SystemExit(f"{ARGS.out} already holds a summary")
ARGS.out.mkdir(parents=True, exist_ok=True)


path = config.paths().raw / "nadig_hepg2" / "NadigOConner2024_hepg2.h5ad"
coords = load_coordinates(config.paths().external / "annotation" / "gene_coordinates_gencode_v50.tsv")
with h5py.File(path, "r") as f:
    obs = read_frame(f["obs"])
    genes = read_frame(f["var"]).index.astype(str).to_numpy()
sym = obs["gene"].astype(str).to_numpy()
ntc_all = sym == "non-targeting"
ntc = np.zeros_like(ntc_all)
ntc[np.random.default_rng(1).choice(np.flatnonzero(ntc_all), 2000, replace=False)] = True
counts = pd.Series(sym[~ntc_all]).value_counts()
gpos = {g: i for i, g in enumerate(genes)}
targets = [t for t in counts.index if counts[t] >= 50 and t in gpos]
rng = np.random.default_rng(0)
targets = sorted(rng.choice(targets, size=min(300, len(targets)), replace=False).tolist())
tidx = {t: i for i, t in enumerate(targets)}
code = np.array([tidx.get(s, -1) for s in sym])

acc = np.zeros((len(targets), genes.size))
n_t = np.zeros(len(targets))
ntc_rows = np.flatnonzero(ntc)
rows = np.flatnonzero((code >= 0) | ntc)
ntc_log = []
ctrl_sum = np.zeros(genes.size)
with h5py.File(path, "r") as f:
    x = f["X"]
    for i in range(0, rows.size, 1000):
        r = rows[i:i + 1000]
        blk = x[r].astype(np.float64)
        frac = blk / blk.sum(axis=1, keepdims=True)
        m = code[r] >= 0
        np.add.at(acc, code[r][m], frac[m])
        np.add.at(n_t, code[r][m], 1)
        nm = ntc[r]
        ctrl_sum += frac[nm].sum(axis=0)
        ntc_log.append(np.log1p(1e4 * frac[nm]).astype(np.float32))
        print(f"read {i + r.size}/{rows.size}", flush=True) if (i // 1000) % 20 == 0 else None
ctrl = ctrl_sum / ntc.sum()
L = np.vstack(ntc_log)
expressed = ctrl > 2e-5
Lz = L - L.mean(axis=0)
sd = Lz.std(axis=0)
ok = expressed & (sd > 0)
Lz = Lz[:, ok] / sd[ok]
g_ok = genes[ok]
# residualize on top PCs (cell state)
u, s, vt = np.linalg.svd(Lz[:, np.argsort(-Lz.var(axis=0))[:2000]], full_matrices=False)
pcs = u[:, :20]
R = Lz - pcs @ (pcs.T @ Lz)
R /= R.std(axis=0) + 1e-9
n = Lz.shape[0]
okpos = {g: i for i, g in enumerate(g_ok)}
res = []
for t in targets:
    if t not in okpos:
        continue
    j = okpos[t]
    eff = np.log2((acc[tidx[t]] / n_t[tidx[t]] + 1e-7) / (ctrl + 1e-7))[ok]
    mask = np.ones(g_ok.size, dtype=bool)
    mask[j] = False
    if t in coords.index:
        c, tss = coords.at[t, "chrom"], coords.at[t, "tss"]
        near = coords[(coords.chrom == c) & ((coords.tss - tss).abs() < 50000)].index
        mask &= ~np.isin(g_ok, near)
    raw = (Lz[:, j] @ Lz) / n
    par = (R[:, j] @ R) / n
    kd = eff[j]
    res.append((t, kd, n_t[tidx[t]], np.corrcoef(raw[mask], eff[mask])[0, 1], np.corrcoef(par[mask], eff[mask])[0, 1],
                np.abs(eff[mask]).mean()))
d = pd.DataFrame(res, columns=["target", "kd_log2", "cells", "r_raw", "r_partial", "mean_abs_eff"])
print(d.describe().round(3).to_string())
strong_kd = d[d.kd_log2 < -1]
print("targets with KD < -1 log2:", len(strong_kd), "median r_raw", strong_kd.r_raw.median().round(3),
      "median r_partial", strong_kd.r_partial.median().round(3))
top = d.sort_values("mean_abs_eff", ascending=False).head(200)
print("top-200 strongest-effect targets: median r_raw", top.r_raw.median().round(3), "median r_partial",
      top.r_partial.median().round(3), "frac r_partial > 0:", (top.r_partial > 0).mean().round(3))
d.to_csv(ARGS.out / "coexp_scores.csv", index=False)
summary = {
    "stage": "78_coexpression_predictor_test",
    "written_utc": datetime.now(timezone.utc).isoformat(),
    "n_targets": int(len(d)), "n_ntc_cells": int(ntc.sum()),
    "median_r_raw": float(d.r_raw.median()), "median_r_partial": float(d.r_partial.median()),
    "mean_r_partial": float(d.r_partial.mean()),
    "strong_kd_targets": {"n": int(len(strong_kd)), "median_r_raw": float(strong_kd.r_raw.median()),
                          "median_r_partial": float(strong_kd.r_partial.median())},
    "top200_by_effect": {"median_r_raw": float(top.r_raw.median()), "median_r_partial": float(top.r_partial.median()),
                         "frac_r_partial_positive": float((top.r_partial > 0).mean())},
    "claim_type": "measurement on HepG2 essential-screen targets; one context",
}
(ARGS.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
