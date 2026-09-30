"""First QC measurements on the cell-level sources already on disk (R-LAB, first delivery).

Per cell: total counts, genes detected, fraction on mitochondrial genes (MT- symbols of the file's
own axis). Reported as quantiles per source, never used to drop a cell: this is the measure the QC
policy will be fixed on, not the policy. Every reader streams, so it runs in well under 1 GB of RAM:

- h5ad (CSR or dense): blocks of rows through h5py/anndata backed mode;
- HIPSCI genes x cells CSV.gz: one pass over the file, keeping only the first --cells columns;
- 10x MatrixMarket .mtx.gz of one channel: per-barcode totals over every barcode, empty droplets
  included, which is what an ambient-RNA estimate needs.

    python qc_sample.py h5ad  --path <file> --name <id> --out qc_r1/<id>.json [--published-depth UMI_count]
    python qc_sample.py hipsci --path <csv.gz> --name <id> --cells 3000 --out qc_r1/<id>.json
    python qc_sample.py mtx    --channel <dir>/<prefix> --name <id> --out qc_r1/<id>.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np

QUANTILES = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]


def summary(values: np.ndarray) -> dict:
    if values.size == 0:
        return {}
    q = np.quantile(values, QUANTILES)
    return {"n": int(values.size), "min": float(values.min()), "max": float(values.max()),
            **{f"q{int(p * 100):02d}": float(v) for p, v in zip(QUANTILES, q)}}


def write(out: Path, data: dict) -> None:
    if out.exists():
        sys.exit(f"refusing: {out} exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(out, json.dumps({k: data[k] for k in ("name", "cells") if k in data}))


def from_h5ad(args) -> None:
    import anndata as ad
    import scipy.sparse as sp
    a = ad.read_h5ad(args.path, backed="r")
    mito = np.array([n.startswith("MT-") for n in a.var_names])
    totals, genes, mt = [], [], []
    for start in range(0, a.n_obs, args.block):
        x = a.X[start:start + args.block]
        x = x.tocsr() if sp.issparse(x) else sp.csr_matrix(np.asarray(x))
        t = np.asarray(x.sum(axis=1)).ravel()
        totals.append(t)
        genes.append(np.diff(x.indptr))
        mt.append(np.asarray(x[:, mito].sum(axis=1)).ravel() / np.maximum(t, 1))
    t, g, m = np.concatenate(totals), np.concatenate(genes), np.concatenate(mt)
    out = {"name": args.name, "path": args.path, "cells": int(a.n_obs), "genes_on_axis": int(a.n_vars),
           "mito_genes_on_axis": int(mito.sum()), "total_counts": summary(t), "genes_detected": summary(g),
           "mito_fraction": summary(m), "zero_depth_cells": int((t == 0).sum())}
    if args.published_depth and args.published_depth in a.obs:
        pub = a.obs[args.published_depth].to_numpy(dtype=float)
        out["published_depth"] = summary(pub)
        out["fraction_of_published_depth_on_axis"] = summary(t / np.maximum(pub, 1))
    if args.group and args.group in a.obs:
        out["groups"] = int(a.obs[args.group].nunique())
    a.file.close()
    write(Path(args.out), out)


def from_hipsci(args) -> None:
    n = args.cells
    totals = np.zeros(n); detected = np.zeros(n, dtype=np.int64); mito = np.zeros(n)
    genes = 0
    with gzip.open(args.path, "rt", encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split(",", n + 1)[1:n + 1]
        for line in fh:
            genes += 1
            fields = line.split(",", n + 1)
            values = np.array(fields[1:n + 1], dtype=np.float64)
            totals += values
            detected += values > 0
            if fields[0].split(":")[1].startswith("MT-"):
                mito += values
    out = {"name": args.name, "path": args.path, "cells": n, "sampled": "the first columns of the file",
           "first_cell": header[0], "genes_on_axis": genes, "total_counts": summary(totals),
           "genes_detected": summary(detected.astype(float)), "mito_fraction": summary(mito / np.maximum(totals, 1)),
           "zero_depth_cells": int((totals == 0).sum())}
    write(Path(args.out), out)


def from_mtx(args) -> None:
    import pandas as pd
    prefix = args.channel
    feats = pd.read_csv(prefix + "_transcriptome_features.tsv.gz", sep="\t", header=None)
    mito_rows = set((np.flatnonzero(feats[1].astype(str).str.startswith("MT-")) + 1).tolist())
    with gzip.open(prefix + "_transcriptome_matrix.mtx.gz", "rt") as fh:
        skip = 0
        line = fh.readline()
        while line.startswith("%"):
            skip += 1; line = fh.readline()
        n_genes, n_bc, nnz = (int(v) for v in line.split())
    totals = np.zeros(n_bc + 1); mito = np.zeros(n_bc + 1); detected = np.zeros(n_bc + 1, dtype=np.int64)
    reader = pd.read_csv(prefix + "_transcriptome_matrix.mtx.gz", sep=" ", header=None, skiprows=skip + 1,
                         names=["g", "b", "v"], dtype={"g": np.int32, "b": np.int32, "v": np.float64},
                         chunksize=5_000_000)
    for chunk in reader:
        b, v = chunk["b"].to_numpy(), chunk["v"].to_numpy()
        totals += np.bincount(b, weights=v, minlength=n_bc + 1)
        detected += np.bincount(b, minlength=n_bc + 1)
        is_mt = chunk["g"].isin(mito_rows).to_numpy()
        mito += np.bincount(b[is_mt], weights=v[is_mt], minlength=n_bc + 1)
    totals, mito, detected = totals[1:], mito[1:], detected[1:]
    cells = totals >= args.cell_umi
    out = {"name": args.name, "channel": prefix, "barcodes": n_bc, "genes_on_axis": n_genes, "nnz": nnz,
           "barcodes_by_umi": {str(k): int((totals >= k).sum()) for k in (1, 10, 100, 500, 1000, 5000)},
           "cell_umi_threshold_for_summary": args.cell_umi, "cells": int(cells.sum()),
           "total_counts": summary(totals[cells]), "genes_detected": summary(detected[cells].astype(float)),
           "mito_fraction": summary(mito[cells] / np.maximum(totals[cells], 1)),
           "ambient_pool_umi": float(totals[(totals > 0) & (totals < 100)].sum()),
           "ambient_pool_barcodes": int(((totals > 0) & (totals < 100)).sum())}
    write(Path(args.out), out)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kind", required=True)
    h = sub.add_parser("h5ad"); h.add_argument("--path", required=True); h.add_argument("--name", required=True)
    h.add_argument("--out", required=True); h.add_argument("--block", type=int, default=2000)
    h.add_argument("--published-depth"); h.add_argument("--group"); h.set_defaults(fn=from_h5ad)
    c = sub.add_parser("hipsci"); c.add_argument("--path", required=True); c.add_argument("--name", required=True)
    c.add_argument("--out", required=True); c.add_argument("--cells", type=int, default=3000); c.set_defaults(fn=from_hipsci)
    m = sub.add_parser("mtx"); m.add_argument("--channel", required=True); m.add_argument("--name", required=True)
    m.add_argument("--out", required=True); m.add_argument("--cell-umi", type=float, default=500); m.set_defaults(fn=from_mtx)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
