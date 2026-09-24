"""Within-context ceiling (DLD-1 Low1 vs Low2) against cross-context transfer, with bootstrap CIs.

Exploratory, not a stage. Low1 and Low2 are the two lane-split halves of the low-MOI data
(bioRxiv 10.64898/2026.07.10.737863), so Low1 vs Low2 measures how reproducible a target's
effect is inside DLD-1. Everything is computed per target on the same genes (DLD-1 response
genes on the official axis), then summarised by the median, with a bootstrap over targets.
Usage: python ceiling_dld1.py <dld1_dir> <data_root> <cache_dir> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

dld1, root, cache, out = map(Path, sys.argv[1:5])
if out.exists():
    sys.exit(f"refusing to overwrite {out}")
rng = np.random.default_rng(20260924)
B = 2000

def per_target(path):
    m = pd.read_csv(path, index_col=0).astype(np.float32)
    cols = [c for c in m.columns if not str(c).upper().startswith("NTC")]
    t = pd.Series([str(c).split("_")[0] for c in cols], index=cols)
    return m[cols].T.groupby(t.values).mean().T  # genes x targets

low1 = per_target(dld1 / "GSE337988_sublib2_de_matrices_lfc_matrix_Low1.csv.gz")
low2 = per_target(dld1 / "GSE337988_sublib2_de_matrices_lfc_matrix_Low2.csv.gz")
genes_axis = pd.read_csv(root / "raw/controls/gene_names.csv")["gene_name"].tolist()
targets300 = pd.read_csv(root / "raw/controls/pert_counts.csv")["target_gene"].tolist()
axis = set(genes_axis)
genes = [g for g in low1.index if g in axis and g in low2.index]
tg = [t for t in low1.columns if t in low2.columns]
L1 = low1.loc[genes, tg].to_numpy(np.float64)
L2 = low2.loc[genes, tg].to_numpy(np.float64)

def col_corr(A, Bm):
    A = A - np.nanmean(A, axis=0); Bm = Bm - np.nanmean(Bm, axis=0)
    num = np.nansum(A * Bm, axis=0)
    den = np.sqrt(np.nansum(A * A, axis=0) * np.nansum(Bm * Bm, axis=0))
    return num / den

def boot_median(x):
    x = np.asarray(x)[np.isfinite(x)]
    if len(x) < 5:
        return None
    meds = np.median(rng.choice(x, size=(B, len(x)), replace=True), axis=1)
    return {"median": float(np.median(x)), "ci95": [float(np.quantile(meds, 0.025)), float(np.quantile(meds, 0.975))], "n": int(len(x))}

within = col_corr(L1, L2)
perm = rng.permutation(len(tg))
within_null = col_corr(L1, L2[:, perm])
strength = np.sqrt(np.nanmean(L1 ** 2, axis=0))
strong = strength >= np.quantile(strength, 0.9)
result = {
    "genes_used": len(genes), "targets_in_both_halves": len(tg),
    "within_dld1_all_targets": boot_median(within),
    "within_dld1_null_shuffled": boot_median(within_null),
    "within_dld1_top10pct_by_effect_size": boot_median(within[strong]),
    "claim_type": "exploratory measurement in effect space; not a VCC score",
    "sources": {},
}
idx = {t: i for i, t in enumerate(tg)}
per_source = {}
for npz in sorted(cache.glob("*.npz")):
    z = np.load(npz, allow_pickle=True)
    src_t = [str(t) for t in z["targets"]]
    raw = pd.DataFrame(z["raw"], index=src_t, columns=genes_axis).T
    shared = [t for t in targets300 if t in idx and t in set(src_t)]
    if len(shared) < 5:
        continue
    D = L1[:, [idx[t] for t in shared]]
    S = raw.loc[genes, shared].to_numpy(np.float64)
    cross = col_corr(D, S)
    null = col_corr(D, S[:, rng.permutation(len(shared))])
    w = within[[idx[t] for t in shared]]
    per_source[npz.stem] = dict(zip(shared, cross))
    result["sources"][npz.stem] = {
        "shared_targets": len(shared),
        "cross_corr": boot_median(cross), "cross_null": boot_median(null),
        "within_dld1_same_targets": boot_median(w),
    }

def paired_diff(a, b):
    common = [t for t in per_source.get(a, {}) if t in per_source.get(b, {})]
    d = np.array([per_source[a][t] - per_source[b][t] for t in common])
    d = d[np.isfinite(d)]
    if len(d) < 5:
        return None
    meds = np.median(rng.choice(d, size=(B, len(d)), replace=True), axis=1)
    return {"median_diff": float(np.median(d)), "ci95": [float(np.quantile(meds, 0.025)), float(np.quantile(meds, 0.975))], "n": int(len(d))}

result["paired_orion_hct116_minus_k562"] = paired_diff("orion_hct116", "k562")
result["paired_orion_hct116_minus_orion_hek293t"] = paired_diff("orion_hct116", "orion_hek293t")
result["paired_orion_hct116_minus_cd4_Rest"] = paired_diff("orion_hct116", "cd4_Rest")
print(json.dumps(result, indent=2))
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
