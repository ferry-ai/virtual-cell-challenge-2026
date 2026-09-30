"""Small-memory zero-effect audit; see PROTOCOLLO_NULLO.md before running."""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np

from audit_profile import control_summary
from vcc2026.de_tools import ReferencePool, bh
from vcc2026.inference import read_csr_rows
from vcc2026.sampling import fit_gene_dispersion, resample_library_sizes, sample_counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--contexts", default="ABC")
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit("Output exists")
    args.out.mkdir(parents=True)
    for c in args.contexts:
        path = args.data / "raw/controls" / f"context_{c}.h5ad"
        raw, pc, zero, libs, genes = control_summary(path)
        rng = np.random.default_rng(20260929)
        perm = rng.permutation(libs.size)
        reference = read_csr_rows(path, perm[:1500], genes.size)
        pool = ReferencePool(reference, genes)
        del reference
        gc.collect()
        phi = fit_gene_dispersion(raw, libs, zero, n_cells=1000, seed=20260929, block=512)
        phi_pc = fit_gene_dispersion(pc, libs, zero, n_cells=1000, seed=20260929, block=512)
        rows = []
        for rep in range(3):
            for arm, multiplier in [("real", None), ("poisson", 0), ("phi_025", .25), ("phi_05", .5), ("phi_1", 1), ("phi_1_percell", 1)]:
                draw = np.random.default_rng(20260929 + rep)
                if arm == "real":
                    pick = draw.choice(perm[1500:], size=400, replace=False)
                    cells = read_csr_rows(path, pick, genes.size)
                else:
                    is_pc = arm == "phi_1_percell"
                    cells = sample_counts(pc if is_pc else raw,
                                          resample_library_sizes(libs, 400, draw), draw,
                                          max_stored_per_cell=13200, max_counts_per_cell=1000000,
                                          overdispersion=multiplier * (phi_pc if is_pc else phi) if multiplier else None)
                pval, lfc = pool.test(cells)
                called = bh(pval) < .05
                col = np.asarray(cells.sum(axis=0), dtype=float).ravel()
                pred = np.log1p(5e4 * col / col.sum())
                real = np.log1p(5e4 * raw / raw.sum())
                row = {"context": c, "replicate": rep, "arm": arm, "n_pred": int(called.sum()),
                       "frac_up": float((lfc[called] > 0).mean()) if called.any() else None,
                       "nnz_per_cell": float(cells.nnz / 400), "bulk_energy_realized_vs_pooled": float(np.sum((pred - real)**2)),
                       "lfc_bias_all_median": float(np.median(lfc))}
                rows.append(row)
                print(json.dumps(row), flush=True)
                del cells
        payload = {"claim_type": "control-only exploratory calibration; not official score",
                   "reference_cells": 1500, "cells_per_replicate": 400,
                   "genes_tested": int(pool.kept.size), "rows": rows}
        with (args.out / f"context_{c}.json").open("x", encoding="utf8") as fh:
            json.dump(payload, fh, indent=2)
        del pool
        gc.collect()


if __name__ == "__main__":
    main()
