"""Write one contract-compliant cell shard (R-LAB P2), and check it before calling it done.

The core takes a block of raw counts (cells x native features), the per-cell metadata already
mapped to the contract's names, the feature table and the provenance, and writes a new .h5ad that
`contracts.validate_shard` accepts; it refuses an existing path, records the sum of counts before
and after writing, and re-reads the file to verify it. Adapters map one source schema to the core.

Adapter here: `h5ad` (a published AnnData with counts in X, dense or CSR), used for the HepG2
pilot. The CSV genes x cells (HIPSCI) and MTX with hashing (Jurkat) adapters come with J02 and J03.

    python shard_writer.py h5ad --path <file> --study hepg2_nadig --cells 0:1000 \
        --axis <data_root>/raw/controls/gene_names.csv --out <new dir>/shard_00000.h5ad \
        --map target=gene guides=guide_id library=batch --published-depth UMI_count \
        --control-label non-targeting --context HepG2 --chemistry "10x 3'" --modality CRISPRi
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from contracts import CONTRACT_VERSION, OBS_REQUIRED, validate_shard  # noqa: E402

MISSING = "MISSING"


def sha256_head(path: Path, nbytes: int = 1 << 26) -> str:
    """Hash of the first 64 MiB: an identity check of a large source, declared as partial."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read(nbytes))
    return h.hexdigest()


def official_index(symbols: list[str], axis_csv: str | None) -> tuple[np.ndarray, np.ndarray]:
    if not axis_csv:
        return np.full(len(symbols), -1), np.array(["none"] * len(symbols))
    axis = [line.strip().split(",")[0] for line in open(axis_csv, encoding="utf-8") if line.strip()]
    if axis and axis[0].lower() in ("gene", "gene_name", "genes", "x"):
        axis = axis[1:]
    where: dict[str, list[int]] = {}
    for i, g in enumerate(axis):
        where.setdefault(g, []).append(i)
    idx = np.array([where[s][0] if len(where.get(s, [])) == 1 else -1 for s in symbols])
    kind = np.array(["unique" if len(where.get(s, [])) == 1 else ("ambiguous" if s in where else "none")
                     for s in symbols])
    return idx, kind


def write_shard(x, obs, var, uns: dict, out: Path) -> list[str]:
    """The core: x is CSR integer counts (cells x native features); obs and var are DataFrames."""
    import anndata as ad
    import scipy.sparse as sp
    if out.exists():
        sys.exit(f"refusing: {out} exists")
    x = sp.csr_matrix(x)
    if x.data.size and not np.all(np.equal(np.mod(x.data, 1), 0)):
        sys.exit("refusing: X is not integer counts; corrected counts belong in a layer")
    x = x.astype(np.int32)
    missing = sorted(set(OBS_REQUIRED) - set(obs.columns))
    if missing:
        sys.exit(f"refusing: obs lacks {missing}")
    before = int(x.sum())
    uns = {**uns, "contract_version": CONTRACT_VERSION,
           "parity": {**uns.get("parity", {}), "sum_before": before, "cells": int(x.shape[0])}}
    a = ad.AnnData(X=x, obs=obs, var=var, uns=uns)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial.h5ad")
    a.write_h5ad(tmp, compression="gzip")
    b = ad.read_h5ad(tmp)
    after = int(b.X.sum())
    b.uns["parity"]["sum_after"] = after
    b.write_h5ad(tmp, compression="gzip")
    problems = validate_shard(tmp)
    if not problems:
        tmp.rename(out)
    return problems


def adapter_h5ad(args) -> None:
    import anndata as ad
    import pandas as pd
    import scipy.sparse as sp
    src = Path(args.path)
    a = ad.read_h5ad(src, backed="r")
    start, stop = (int(v) for v in args.cells.split(":"))
    block = a[start:stop]
    x = block.X[:] if not sp.issparse(block.X) else block.X
    x = sp.csr_matrix(np.asarray(x) if not sp.issparse(x) else x)
    mapping = dict(kv.split("=", 1) for kv in args.map)
    o = block.obs
    col = lambda name: o[mapping[name]].astype(str).to_numpy() if name in mapping else np.array([MISSING] * block.n_obs)
    target = col("target")
    control = np.where(target == args.control_label, "NTC", "none")
    depth = np.asarray(x.sum(axis=1)).ravel()
    obs = pd.DataFrame({
        "cell_key": [f"{args.study}|{lib}|{bc}" for lib, bc in zip(col("library"), block.obs_names)],
        "study": args.study, "library": col("library"), "barcode": list(block.obs_names),
        "target": np.where(control == "NTC", "NTC", target), "guides": col("guides"),
        "guide_confidence": col("guide_confidence"), "modality": args.modality, "control_kind": control,
        "context": args.context, "donor_or_clone": col("donor_or_clone"), "batch": col("library"),
        "chemistry": args.chemistry, "condition": "none",
        "depth_native": o[args.published_depth].to_numpy(dtype=float) if args.published_depth else depth.astype(float),
        "depth_published": o[args.published_depth].to_numpy(dtype=float) if args.published_depth else depth.astype(float),
        "depth_on_file_axis": depth.astype(float), "n_genes_detected": np.diff(x.indptr),
    }, index=[f"c{start + i}" for i in range(block.n_obs)])
    symbols = list(a.var_names)
    idx, kind = official_index(symbols, args.axis)
    var = pd.DataFrame({"feature_id": a.var["gene_id"].astype(str).to_numpy() if "gene_id" in a.var else symbols,
                        "symbol": symbols, "feature_type": "Gene Expression", "measured": True,
                        "official_index": idx, "mapping": kind}, index=symbols)
    commit = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    uns = {"source": {"id": args.study, "locator": str(src), "bytes": src.stat().st_size,
                      "sha256_first_64MiB": sha256_head(src)},
           "read": {"how": "anndata backed, row slice", "rows": args.cells},
           "rows": {"range": args.cells, "of": int(a.n_obs)},
           "qc_version": "none", "writer": {"script": "shard_writer.py", "commit": commit},
           "notes": "depth_native is the published total before the gene filter; depth_on_file_axis sums the file's axis"}
    a.file.close()
    problems = write_shard(x, obs, var, uns, Path(args.out))
    print(args.out, "ok" if not problems else problems)
    sys.exit(1 if problems else 0)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kind", required=True)
    h = sub.add_parser("h5ad")
    for flag in ("--path", "--study", "--cells", "--out"):
        h.add_argument(flag, required=True)
    h.add_argument("--axis"); h.add_argument("--map", nargs="*", default=[])
    h.add_argument("--published-depth"); h.add_argument("--control-label", default="non-targeting")
    h.add_argument("--context", required=True); h.add_argument("--chemistry", required=True)
    h.add_argument("--modality", required=True)
    h.set_defaults(fn=adapter_h5ad)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
