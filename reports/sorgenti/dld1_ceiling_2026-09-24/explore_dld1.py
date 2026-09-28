"""First look at the DLD-1 (GSE337988) Low1 effect matrices against the team's targets and K562.

Exploratory, not a stage: prints facts and writes one JSON to --out (refuses to overwrite).
Usage: python explore_dld1.py <dld1_dir> <data_root> <out.json> [--log-base 2|e]
"""
import gzip
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

dld1, root, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
log_base = sys.argv[5] if len(sys.argv) > 5 and sys.argv[4] == "--log-base" else "2"
if out.exists():
    sys.exit(f"refusing to overwrite {out}")

lfc_path = dld1 / "GSE337988_sublib2_de_matrices_lfc_matrix_Low1.csv.gz"
se_path = dld1 / "GSE337988_sublib2_de_matrices_se_matrix_Low1.csv.gz"
with gzip.open(lfc_path, "rt") as f:
    header = f.readline().rstrip("\n").split(",")
    first_rows = [f.readline().rstrip("\n").split(",")[:4] for _ in range(3)]
print("columns:", len(header), "first:", header[:6], "last:", header[-3:])
print("first rows (4 fields):", first_rows)

lfc = pd.read_csv(lfc_path, index_col=0, dtype={c: np.float32 for c in header[1:]})
print("lfc shape (rows x cols):", lfc.shape)
row_labels, col_labels = list(lfc.index[:5]), list(lfc.columns[:5])
print("row labels:", row_labels, "col labels:", col_labels)

genes_axis = pd.read_csv(root / "raw/controls/gene_names.csv")["gene_name"].tolist()
targets300 = pd.read_csv(root / "raw/controls/pert_counts.csv")["target_gene"].tolist()
axis = set(genes_axis)
# Decide orientation: the side whose labels overlap the gene axis most is the measured-gene side.
rows_in_axis = sum(1 for g in lfc.index if g in axis)
cols_in_axis = sum(1 for g in lfc.columns if g in axis)
genes_as_rows = rows_in_axis >= cols_in_axis
mat = lfc if genes_as_rows else lfc.T
print("measured genes on", "rows" if genes_as_rows else "columns",
      "| in official axis:", max(rows_in_axis, cols_in_axis), "of", mat.shape[0])

pert_labels = list(mat.columns)
def target_of(label):
    return str(label).split("_")[0]
pert_targets = pd.Series([target_of(p) for p in pert_labels], index=pert_labels)
dld_targets = set(pert_targets)
nt_like = [p for p in pert_labels if "non" in str(p).lower() or "ntc" in str(p).lower() or "safe" in str(p).lower()]
print("perturbation columns:", len(pert_labels), "| distinct targets:", len(dld_targets),
      "| control-like labels:", len(nt_like), nt_like[:3])
overlap300 = sorted(t for t in targets300 if t in dld_targets)
print("official targets covered:", len(overlap300), "of", len(targets300))

# Per-target DLD-1 effect: mean over the target's perturbation columns (promoters/guides).
by_target = mat.T.groupby(pert_targets.values).mean().T  # genes x targets
k = np.load(root / "processed/multisource_2026-09-23_r5/k562.npz", allow_pickle=True)
k_targets = list(k["targets"])
k_raw = pd.DataFrame(k["raw"], index=k_targets, columns=genes_axis).T  # genes x targets, ln fold change
scale = np.log(2.0) if log_base == "2" else 1.0  # DLD-1 fold changes to natural log
shared_t = [t for t in overlap300 if t in k_targets]
shared_g = [g for g in by_target.index if g in axis]
d = by_target.loc[shared_g, shared_t].astype(np.float64) * scale
kk = k_raw.loc[shared_g, shared_t].astype(np.float64)

def corr(a, b):
    a, b = np.asarray(a), np.asarray(b)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 20:
        return np.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])

rng = np.random.default_rng(20260924)
same, shuffled, sign_agree = [], [], []
for i, t in enumerate(shared_t):
    same.append(corr(d[t], kk[t]))
    j = shared_t[(i + 1 + rng.integers(len(shared_t) - 1)) % len(shared_t)] if len(shared_t) > 1 else t
    shuffled.append(corr(d[t], kk[j]))
    big = (np.abs(kk[t]) >= np.nanquantile(np.abs(kk[t]), 0.99)) & np.isfinite(d[t])
    if big.sum() >= 5:
        sign_agree.append(float((np.sign(d[t][big]) == np.sign(kk[t][big])).mean()))

result = {
    "dld1_file": lfc_path.name, "log_base_assumed": log_base,
    "matrix_shape_rows_cols": list(lfc.shape), "genes_on": "rows" if genes_as_rows else "columns",
    "measured_genes": int(mat.shape[0]), "measured_genes_in_official_axis": int(len(shared_g)),
    "perturbation_columns": len(pert_labels), "distinct_targets": len(dld_targets),
    "official_targets_covered": len(overlap300), "shared_with_k562_cache": len(shared_t),
    "per_target_corr_dld1_vs_k562": {"median": float(np.nanmedian(same)) if same else None,
                                      "n": int(np.isfinite(same).sum()) if same else 0},
    "per_target_corr_shuffled_null": {"median": float(np.nanmedian(shuffled)) if shuffled else None},
    "sign_agreement_top1pct_k562_genes": {"median": float(np.median(sign_agree)) if sign_agree else None,
                                          "n": len(sign_agree)},
    "claim_type": "exploratory measurement in effect space; not a VCC score",
}
print(json.dumps(result, indent=2))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
