"""Basal expression of every source context on the official axis, from its own control rows.

The learned transfer model needs, for each gene, how expressed it is in the context a source
was measured in and in the context being predicted. For A/B/C that is
interim/basal_cpm_by_context.csv; for the sources it is computed here from their controls:

* k562: the non-targeting rows of the K562 genome-wide per-cell-mean pseudobulk, averaged
  (weighted by cells) and scaled to CPM;
* cd4_Rest, cd4_Stim8hr, cd4_Stim48hr: summed counts of the non-targeting pseudobulk rows of
  stage 97 per condition, to CPM; cd4_mix is the mean of the three, as its effects are;
* orion_hct116, orion_hek293t: summed counts of the non-targeting pool rows of stage 102, to CPM.

Genes a source did not measure are NaN. Output: one CSV, genes x contexts, with A, B, C appended.

    scripts/py.cmd reports/trasferimento_appreso_2026-09-26/basal_profiles.py \
        --out C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-26.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402

DATA = config.paths().data_root


def to_axis(values: np.ndarray, genes, axis) -> np.ndarray:
    s = pd.Series(np.asarray(values, dtype=np.float64), index=pd.Index(np.asarray(genes).astype(str)))
    s = s[~s.index.duplicated()]
    return s.reindex(axis).to_numpy()


def cpm(counts: np.ndarray) -> np.ndarray:
    return counts / counts.sum() * 1e6


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k562-bulk", type=Path, default=DATA / "external/K562_gwps_raw_bulk_01.h5ad")
    ap.add_argument("--cd4", type=Path, default=DATA / "external/cd4/panel_rows_2026-09-22.h5ad")
    ap.add_argument("--hct116", type=Path, default=DATA / "external/orion/hct116_panel_pools_2026-09-23.h5ad")
    ap.add_argument("--hek293t", type=Path, default=DATA / "external/orion/hek293t_panel_pools_2026-09-23.h5ad")
    ap.add_argument("--abc", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    axis = np.asarray(official_axis().symbols)
    out, info = {}, {}

    with h5py.File(args.k562_bulk, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        ntc = np.flatnonzero(np.array(["non-targeting" in lab for lab in labels]))
        means = f["X"][ntc]
        cells = np.nan_to_num(f["obs/num_cells_filtered"][:][ntc])   # NaN cells count as 0, as in stage 98
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    prof = (means * cells[:, None]).sum(axis=0) / cells.sum()
    out["k562"] = to_axis(cpm(prof), names, axis)
    info["k562"] = {"control_rows": int(ntc.size), "cells": float(cells.sum())}

    a = ad.read_h5ad(args.cd4, backed="r")
    obs = a.obs
    for cond in ("Rest", "Stim8hr", "Stim48hr"):
        rows = np.flatnonzero((obs["guide_type"] == "non-targeting").to_numpy() & (obs["condition"] == cond).to_numpy())
        x = a.X[np.sort(rows)]
        x = np.asarray(x.sum(axis=0)).ravel() if hasattr(x, "sum") else x.sum(axis=0)
        out[f"cd4_{cond}"] = to_axis(cpm(x), a.var_names, axis)
        info[f"cd4_{cond}"] = {"control_rows": int(rows.size)}
    a.file.close()
    out["cd4_mix"] = np.nanmean(np.vstack([out[f"cd4_{c}"] for c in ("Rest", "Stim8hr", "Stim48hr")]), axis=0)

    for name, path in (("orion_hct116", args.hct116), ("orion_hek293t", args.hek293t)):
        a = ad.read_h5ad(path, backed="r")
        tgt = a.obs["target"].astype(str).str.lower()
        rows = np.flatnonzero(tgt.str.contains("non-targeting|non_targeting|ntc|control").to_numpy())
        if rows.size == 0:
            raise SystemExit(f"{name}: no control rows among {sorted(set(tgt))[:5]}")
        x = a.X[np.sort(rows)]
        x = np.asarray(x.sum(axis=0)).ravel() if hasattr(x, "sum") else x.sum(axis=0)
        out[name] = to_axis(cpm(x), a.var_names, axis)
        info[name] = {"control_rows": int(rows.size)}
        a.file.close()

    abc = pd.read_csv(args.abc).set_index("gene_name").reindex(axis)[["A", "B", "C"]]
    df = pd.DataFrame(out, index=pd.Index(axis, name="gene_name"))
    df = pd.concat([df, abc], axis=1)
    df.to_csv(args.out)
    info["genes_measured"] = {c: int(np.isfinite(df[c]).sum()) for c in df.columns}
    with open(args.out.with_suffix(".json"), "x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_appreso_2026-09-26/basal_profiles.py", "info": info}, fh, indent=1)
    print(json.dumps(info, indent=1))
    print(df.corr(method="spearman").round(3).to_string())


if __name__ == "__main__":
    main()
