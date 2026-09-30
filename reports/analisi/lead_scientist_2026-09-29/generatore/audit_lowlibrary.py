"""Streaming control-only attribution of per-cell CPM outliers to low-depth cells."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit("Output exists")
    thresholds = [100, 500, 1000, 2000]
    watched = ["RNF151", "CCM2L", "SOCS1", "MAFB", "HIST1H3G", "CSKMT", "DEPP1", "HIST1H3H", "MXD1", "NRARP"]
    results = []
    for context in "ABC":
        with h5py.File(args.data / "raw/controls" / f"context_{context}.h5ad", "r") as f:
            n, g = map(int, f["X"].attrs["shape"])
            ptr = f["X/indptr"][:]
            index = f["var"][f["var"].attrs["_index"]]
            genes = index["values"].asstr()[:] if isinstance(index, h5py.Group) else index.asstr()[:]
            raw, cpm = np.zeros(g), np.zeros(g)
            low_raw = {t: np.zeros(g) for t in thresholds}
            low_cpm = {t: np.zeros(g) for t in thresholds}
            low_n = {t: 0 for t in thresholds}
            libs_all = np.zeros(n)
            for start in range(0, n, 400):
                end = min(n, start + 400)
                local = ptr[start:end+1] - ptr[start]
                val = f["X/data"][ptr[start]:ptr[end]].astype(float)
                ix = f["X/indices"][ptr[start]:ptr[end]]
                libs = np.array([val[a:b].sum() for a,b in zip(local[:-1], local[1:])])
                libs_all[start:end] = libs
                lengths = np.diff(local)
                inv = np.repeat(1 / np.maximum(libs, 1), lengths)
                raw += np.bincount(ix, weights=val, minlength=g)
                cpm += np.bincount(ix, weights=val * inv, minlength=g)
                for threshold in thresholds:
                    selected = libs < threshold
                    low_n[threshold] += int(selected.sum())
                    entries = np.repeat(selected, lengths)
                    low_raw[threshold] += np.bincount(ix[entries], weights=val[entries], minlength=g)
                    low_cpm[threshold] += np.bincount(ix[entries], weights=(val*inv)[entries], minlength=g)
            row = {"context": context, "library_quantiles_min_p001_p01_p05_p50": np.quantile(libs_all, [0,.001,.01,.05,.5]).tolist(),
                   "thresholds": [], "outlier_attribution": []}
            for t in thresholds:
                row["thresholds"].append({"library_lt": t, "n_cells": low_n[t], "fraction_cells": low_n[t]/n,
                                          "fraction_all_counts": float(low_raw[t].sum()/raw.sum())})
            for gene in watched:
                positions = np.flatnonzero(genes == gene)
                if not positions.size:
                    continue
                j = positions[0]
                row["outlier_attribution"].append({"gene": gene, "mean_cell_cpm": float(1e6*cpm[j]/n),
                    "fraction_gene_per_cell_cpm_from_lowlibrary": {str(t): float(low_cpm[t][j]/cpm[j]) if cpm[j] else None for t in thresholds},
                    "fraction_gene_counts_from_lowlibrary": {str(t): float(low_raw[t][j]/raw[j]) if raw[j] else None for t in thresholds}})
            results.append(row)
            print(json.dumps(row), flush=True)
    with args.out.open("x", encoding="utf8") as fh:
        json.dump({"claim_type": "measured control-only attribution; no cell removal or model change", "results": results}, fh, indent=2)


if __name__ == "__main__":
    main()
