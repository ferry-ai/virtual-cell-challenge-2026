"""Read-only streaming audit of pooled versus per-cell control profiles.

Run with scripts/py.cmd; writes only a new JSON in the report's own output path.
No reference outcome is read and no production artifact is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def control_summary(path: Path):
    with h5py.File(path, "r") as f:
        n, g = map(int, f["X"].attrs["shape"])
        ip = f["X/indptr"][:]
        raw, norm, detected = np.zeros(g), np.zeros(g), np.zeros(g)
        libraries = np.zeros(n)
        for st in range(0, n, 400):
            en = min(n, st + 400)
            ptr = ip[st:en + 1]
            values = f["X/data"][ptr[0]:ptr[-1]].astype(float)
            ix = f["X/indices"][ptr[0]:ptr[-1]]
            local = ptr - ptr[0]
            libs = np.array([values[a:b].sum() for a, b in zip(local[:-1], local[1:])])
            raw += np.bincount(ix, weights=values, minlength=g)
            norm += np.bincount(ix, weights=values / np.repeat(np.maximum(libs, 1), np.diff(local)), minlength=g)
            detected += np.bincount(ix, minlength=g)
            libraries[st:en] = libs
        index = f["var"][f["var"].attrs["_index"]]
        if isinstance(index, h5py.Group):
            if "categories" in index:
                genes = index["categories"].asstr()[:][index["codes"][:]]
            else:
                genes = index["values"].asstr()[:]
                if "mask" in index and index["mask"][:].any():
                    raise ValueError("Missing control gene labels")
        else:
            genes = index.asstr()[:]
    return raw, norm / n, 1 - detected / n, libraries, genes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit("Output already exists; choose a new path")
    rows = []
    for c in "ABC":
        path = args.data / "raw/controls" / f"context_{c}.h5ad"
        raw, pc, pzero, libs, genes = control_summary(path)
        pp = raw / raw.sum()
        keep = pc > 5e-6
        logbias = np.log2(np.maximum(pp, 1e-30) / np.maximum(pc, 1e-30))
        dz = np.log1p(5e4 * pc) - np.log1p(5e4 * pp)
        order = np.argsort(np.abs(logbias) * keep)[-10:][::-1]
        row = {
            "context": c, "n_cells": int(libs.size), "n_genes": int(genes.size),
            "library_mean": float(libs.mean()), "library_cv": float(libs.std() / libs.mean()),
            "de_genes_reference_mean_cpm_gt_5": int(keep.sum()),
            "pooled_over_per_cell_log2_bias_q01_q10_q50_q90_q99": np.quantile(logbias[keep], [.01, .1, .5, .9, .99]).tolist(),
            "de_genes_abs_log2_bias_gt_0p1": int(np.sum((np.abs(logbias) > .1) & keep)),
            "bulk_space_energy_per_cell_vs_pooled_per_target_all_genes": float(dz @ dz),
            "bulk_space_energy_per_cell_vs_pooled_panel_300": float(300 * (dz @ dz)),
            "mse_ratio_proxy_added_energy_over_4786": float(300 * (dz @ dz) / 4786),
            "top_bias": [{"gene": str(genes[j]), "log2_bias": float(logbias[j]), "mean_cell_cpm": float(pc[j] * 1e6)} for j in order],
            "input_path": str(path), "input_bytes": path.stat().st_size,
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    payload = {"claim_type": "measured controls only; energy ratio is a proxy, not official MSE", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as fh:
        json.dump(payload, fh, indent=2)


if __name__ == "__main__":
    main()
