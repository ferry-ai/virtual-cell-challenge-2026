"""Compare DLD-1 (GSE337988 Low1) per-target effects with each source of a stage-98 cache.

Exploratory, not a stage. For each cached source: per-target correlation with DLD-1 on the shared
measured genes, the same with a shuffled target (the null), and sign agreement on the source's
top 1% genes per target. Writes one JSON (refuses to overwrite).
Usage: python compare_sources.py <dld1_lfc.csv.gz> <data_root> <cache_dir> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

lfc_path, root, cache, out = map(Path, sys.argv[1:5])
if out.exists():
    sys.exit(f"refusing to overwrite {out}")

lfc = pd.read_csv(lfc_path, index_col=0, dtype=np.float32 if False else None)
lfc = lfc.astype(np.float32)
genes_axis = pd.read_csv(root / "raw/controls/gene_names.csv")["gene_name"].tolist()
targets300 = pd.read_csv(root / "raw/controls/pert_counts.csv")["target_gene"].tolist()
axis = set(genes_axis)

cols = list(lfc.columns)
ntc_cols = [c for c in cols if str(c).upper().startswith("NTC")]
pert_cols = [c for c in cols if c not in set(ntc_cols)]
targets = pd.Series([str(c).split("_")[0] for c in pert_cols], index=pert_cols)
by_target = lfc[pert_cols].T.groupby(targets.values).mean().T * np.log(2.0)  # genes x targets
shared_g = [g for g in by_target.index if g in axis]

rng = np.random.default_rng(20260924)
def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() >= 20 else np.nan

report = {"dld1_file": lfc_path.name, "ntc_columns": len(ntc_cols),
          "perturbation_columns": len(pert_cols), "dld1_targets": int(targets.nunique()),
          "measured_genes_in_axis": len(shared_g),
          "official_targets_in_dld1": int(sum(t in set(targets) for t in targets300)),
          "sources": {},
          "claim_type": "exploratory measurement in effect space (ln fold change, DLD-1 assumed log2); not a VCC score"}
for npz in sorted(cache.glob("*.npz")):
    z = np.load(npz, allow_pickle=True)
    src_t = list(z["targets"])
    raw = pd.DataFrame(z["raw"], index=src_t, columns=genes_axis).T
    shared_t = [t for t in targets300 if t in set(targets) and t in set(src_t)]
    if len(shared_t) < 5:
        report["sources"][npz.stem] = {"shared_targets": len(shared_t)}
        continue
    d = by_target.loc[shared_g, shared_t].to_numpy(np.float64)
    s = raw.loc[shared_g, shared_t].to_numpy(np.float64)
    same, null, sign = [], [], []
    for i in range(len(shared_t)):
        same.append(corr(d[:, i], s[:, i]))
        j = (i + 1 + rng.integers(len(shared_t) - 1)) % len(shared_t)
        null.append(corr(d[:, i], s[:, j]))
        col = s[:, i]
        thr = np.nanquantile(np.abs(col), 0.99)
        big = (np.abs(col) >= thr) & np.isfinite(d[:, i])
        if big.sum() >= 5:
            sign.append(float((np.sign(d[big, i]) == np.sign(col[big])).mean()))
    same, null = np.array(same), np.array(null)
    report["sources"][npz.stem] = {
        "shared_targets": len(shared_t),
        "corr_median": float(np.nanmedian(same)), "corr_mean": float(np.nanmean(same)),
        "null_corr_median": float(np.nanmedian(null)),
        "frac_targets_corr_gt_null_p95": float(np.mean(same > np.nanquantile(null, 0.95))),
        "sign_agreement_top1pct_median": float(np.median(sign)) if sign else None,
    }
print(json.dumps(report, indent=2))
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
