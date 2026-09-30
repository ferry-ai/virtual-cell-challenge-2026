"""Control-only, streaming expected-profile audit; no synthetic cells or scorer run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np

from audit_profile import control_summary
from depth_bins import DepthBins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit("Output exists")
    definitions = {"uniform8": np.linspace(0, 1, 9),
                   "tail8": np.array([0, .01, .025, .05, .1, .25, .5, .75, 1])}
    results = []
    for context in "ABC":
        path = args.data / "raw/controls" / f"context_{context}.h5ad"
        raw, pc, _, libs, genes = control_summary(path)
        bins, sums, edges = {}, {}, {}
        for name, quantiles in definitions.items():
            edges[name] = np.unique(np.quantile(libs, quantiles[1:-1]))
            assignments = np.searchsorted(edges[name], libs, side="right")
            bins[name] = np.searchsorted(np.unique(assignments), assignments)
            sums[name] = np.zeros((bins[name].max() + 1, genes.size))
        # The h5ad has no library-size metadata: one first pass obtains those
        # and the exact per-cell reference; this second bounded pass gets sums.
        with h5py.File(path, "r") as f:
            ip = f["X/indptr"][:]
            for start in range(0, libs.size, 200):
                end = min(libs.size, start + 200)
                values = f["X/data"][ip[start]:ip[end]].astype(float)
                indices = f["X/indices"][ip[start]:ip[end]]
                lengths = np.diff(ip[start:end+1])
                for name in definitions:
                    rowbins = np.repeat(bins[name][start:end], lengths)
                    sums[name] += np.bincount(rowbins * genes.size + indices, weights=values,
                                              minlength=sums[name].size).reshape(sums[name].shape)
        keep = pc > 5e-6
        pp = raw / raw.sum()
        baseline_rmse = float(np.sqrt(np.mean((1e6*(pp[keep]-pc[keep]))**2)))
        for name in definitions:
            for smoothing in [0, .01]:
                model = DepthBins.from_sums(sums[name], libs, bins[name], support_smoothing=smoothing)
                estimate_pc = model.cell_weights @ model.profiles
                estimate_pp = model.depth_weights @ model.profiles
                logbias = np.log2(estimate_pc[keep] / pc[keep])
                rmse = float(np.sqrt(np.mean((1e6*(estimate_pc[keep]-pc[keep]))**2)))
                row = {"context": context, "bins": name, "support_smoothing": smoothing,
                       "edges": edges[name].tolist(), "cells_per_bin": np.bincount(bins[name]).tolist(),
                       "cpm_rmse_on_expressed": rmse, "pooled_cpm_rmse_on_expressed": baseline_rmse,
                       "cpm_rmse_fraction_of_pooled": rmse / baseline_rmse,
                       "log2_bias_rms_on_expressed": float(np.sqrt(np.mean(logbias**2))),
                       "genes_abs_log2_bias_gt_0p1": int(np.sum(np.abs(logbias)>.1)),
                       "max_abs_global_pooled_error": float(np.max(np.abs(estimate_pp-pp))),
                       "watched": []}
                for gene in ["RNF151", "CCM2L", "SOCS1", "MAFB", "PLK1", "UBE2C", "CDK1", "TOP2A"]:
                    j = np.flatnonzero(genes == gene)[0]
                    row["watched"].append({"gene": gene,"true_mean_cell_cpm": float(1e6*pc[j]),
                                            "bin_mean_cell_cpm": float(1e6*estimate_pc[j]),
                                            "null_log2_bias": float(np.log2(estimate_pc[j]/pc[j]))})
                results.append(row)
                print(json.dumps({k:v for k,v in row.items() if k not in ["watched","edges"]}),flush=True)
    with args.out.open("x", encoding="utf8") as fh:
        json.dump({"claim_type": "measured expected control profile; no generated cells or official score", "results": results}, fh, indent=2)


if __name__ == "__main__":
    main()
