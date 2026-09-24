"""Stage 97: the CD4 pseudobulk rows of a target panel, read remotely by exact byte ranges.

The GWCD4i pseudobulk (Zhu/Dann/Marson, GSE314342) is one 44.6 GB h5ad on public S3: one
row per guide x donor x culture condition, raw summed counts over 18,129 genes. D-031
deferred CD4 on the 1.7 TB of its single-cell files; the pseudobulk is what transfer
needs, and its chunks are uncompressed, so a panel's rows cost about a gigabyte.

Selected rows:
* every targeting row whose ``perturbed_gene_name`` is a panel target (exact symbol, as
  in stage 26), with all guides kept -- the ``keep_*`` author flags travel as columns
  and are NOT applied here, because filtering on observed guide efficacy selects on the
  outcome;
* up to ``--ntc-per-group`` non-targeting rows per donor x condition, seeded.

Integrity: every fetched row must sum to the row's own ``total_counts`` and hold
non-negative integers, or the stage stops. The output h5ad goes under the data root
(D-001); the manifest goes to ``--report-dir``. Neither is overwritten.

    python scripts/97_extract_cd4_rows.py --out <data_root>/external/cd4/panel_rows.h5ad \
        --report-dir reports/cd4_rows_2026-09-22
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.remote_csr import chunk_map, http_fetcher, read_rows  # noqa: E402
from vcc2026.remote_ranges import HTTPRangeReader  # noqa: E402

URL = ("https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/marson2025_data/"
       "GWCD4i.pseudobulk_merged.h5ad")
DATA_ROOT = config.paths().data_root  # VCC2026_DATA_ROOT, else configs/config.yaml


def categorical(obs, key):
    node = obs[key]
    cats = node["categories"].asstr()[:]
    codes = node["codes"][:]
    return np.where(codes >= 0, cats[np.clip(codes, 0, None)], ""), cats


def head(url: str) -> dict:
    import httpx
    r = httpx.head(url, timeout=60, follow_redirects=True)
    r.raise_for_status()
    return {"size": int(r.headers["Content-Length"]), "etag": r.headers.get("ETag"),
            "last_modified": r.headers.get("Last-Modified")}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default=URL)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv",
                   help="CSV whose first column lists the panel targets")
    p.add_argument("--ntc-per-group", type=int, default=200)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--threads", type=int, default=16)
    p.add_argument("--max-gib", type=float, default=4.0, help="refuse a row selection above this")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report-dir", type=Path, required=True)
    args = p.parse_args()
    manifest_path = args.report_dir / "manifest.json"
    for path in (args.out, manifest_path):
        if path.exists():
            raise FileExistsError(f"{path} exists; new runs go to a new destination")
    started = time.monotonic()
    remote = head(args.url)
    log(f"remote {remote['size'] / 1e9:.2f} GB, etag {remote['etag']}")
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()

    reader = HTTPRangeReader(args.url, max_bytes=512 * 2**20, block_size=2**20)
    with h5py.File(reader, "r") as f:
        obs = f["obs"]
        target, _ = categorical(obs, "perturbed_gene_name")
        target_id, _ = categorical(obs, "perturbed_gene_id")
        gtype, _ = categorical(obs, "guide_type")
        guide, _ = categorical(obs, "guide_id")
        donor, _ = categorical(obs, "donor_id")
        cond, _ = categorical(obs, "culture_condition")
        run, _ = categorical(obs, "10xrun_id")
        num = {k: obs[k][:] for k in ("n_cells", "total_counts")}
        flags = {k: obs[k][:] for k in obs.keys() if k.startswith("keep_")}
        genes = f["var/gene_name"].asstr()[:]
        gene_ids = f["var/gene_ids"].asstr()[:]
        indptr = f["X/indptr"][:]
    log(f"obs {len(target):,} rows, {len(genes):,} genes; reading chunk maps")
    # The chunk index is a B-tree whose few-KB nodes are scattered through the 44.6 GB file:
    # 1 MiB blocks would move ~1 GB for them, so the index is walked with small blocks.
    index_reader = HTTPRangeReader(args.url, max_bytes=256 * 2**20, block_size=16 * 2**10)
    with h5py.File(index_reader, "r") as f:
        dmap, imap = chunk_map(f["X/data"]), chunk_map(f["X/indices"])
    meta_bytes = reader.transferred + index_reader.transferred
    log(f"metadata read: {meta_bytes / 2**20:.1f} MiB; chunks {len(dmap.offsets):,} x2")

    in_panel = (gtype == "targeting") & np.isin(target, panel)
    rng = np.random.default_rng(args.seed)
    ntc_rows = []
    for (d, c), grp in pd.DataFrame({"row": np.flatnonzero(gtype == "non-targeting"),
                                     "d": donor[gtype == "non-targeting"],
                                     "c": cond[gtype == "non-targeting"]}).groupby(["d", "c"]):
        rows = grp.row.to_numpy()
        ntc_rows.extend(rng.choice(rows, size=min(args.ntc_per_group, len(rows)), replace=False).tolist())
    rows = np.sort(np.concatenate([np.flatnonzero(in_panel), np.array(ntc_rows, dtype=np.int64)]))
    need = int(sum(indptr[r + 1] - indptr[r] for r in rows)) * (dmap.itemsize + imap.itemsize)
    log(f"selected {len(rows):,} rows ({in_panel.sum():,} panel, {len(ntc_rows):,} NTC); "
        f"{need / 2**30:.2f} GiB of row bytes")
    if need > args.max_gib * 2**30:
        raise RuntimeError(f"selection needs {need / 2**30:.2f} GiB > --max-gib {args.max_gib}")

    last = [0.0]

    def progress(done, total):
        now = time.monotonic()
        if now - last[0] > 20 or done == total:
            last[0] = now
            log(f"  requests {done:,}/{total:,}")

    fetch = http_fetcher(args.url, expected_size=remote["size"])
    data, idx, ptr, fetched = read_rows(indptr, rows, dmap, imap, fetch, threads=args.threads,
                                        progress=progress)
    log(f"fetched {fetched / 2**30:.2f} GiB in {time.monotonic() - started:.0f}s")

    # Integrity: exact non-negative integers, in-range columns, and each row's own total.
    if not np.isfinite(data).all() or (data < 0).any() or (data != np.rint(data)).any():
        raise ValueError("non-count values in fetched rows")
    if idx.size and (idx.min() < 0 or idx.max() >= len(genes)):
        raise ValueError("column index out of range: byte arithmetic is wrong")
    sums = np.bincount(np.repeat(np.arange(len(rows)), np.diff(ptr)), weights=data,
                       minlength=len(rows))
    bad = ~np.isclose(sums, num["total_counts"][rows], rtol=0, atol=0.5)
    if bad.any():
        raise ValueError(f"{bad.sum()} rows do not sum to their total_counts (first row {rows[bad][0]})")
    exact32 = data.max(initial=0) < 2**24
    X = sp.csr_matrix((data.astype(np.float32 if exact32 else np.float64), idx.astype(np.int32), ptr),
                      shape=(len(rows), len(genes)))
    X.sum_duplicates()
    obs_df = pd.DataFrame({
        "source_row": rows, "target": np.where(gtype[rows] == "non-targeting", "non-targeting", target[rows]),
        "target_id": target_id[rows], "guide_id": guide[rows], "guide_type": gtype[rows],
        "donor": donor[rows], "condition": cond[rows], "run": run[rows],
        "n_cells": num["n_cells"][rows], "total_counts": num["total_counts"][rows],
        **{k: v[rows] for k, v in flags.items()},
    }, index=[f"cd4pb:{r}" for r in rows])
    out = ad.AnnData(X=X, obs=obs_df, var=pd.DataFrame({"gene_ids": gene_ids}, index=genes))
    out.var_names_make_unique()
    out.uns["provenance"] = {"url": args.url, "etag": remote["etag"], "stage": "97_extract_cd4_rows",
                             "normalization": "none; raw summed counts per pseudobulk row"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.write_h5ad(args.out, compression="gzip")
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()

    panel_rows = obs_df[obs_df.guide_type == "targeting"]
    per_target = panel_rows.groupby("target").agg(
        rows=("source_row", "size"), guides=("guide_id", "nunique"), donors=("donor", "nunique"),
        conditions=("condition", "nunique"), cells=("n_cells", "sum"))
    covered = sorted(per_target.index)
    manifest = {
        "stage": "97_extract_cd4_rows",
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "claim_type": "measurement: rows copied from the public file, verified against their own totals",
        "remote": {"url": args.url, **remote},
        "bytes": {"metadata": int(meta_bytes), "rows": int(fetched)},
        "seconds": round(time.monotonic() - started, 1),
        "selection": {"panel_targets": len(panel), "panel_targets_found": len(covered),
                      "panel_targets_missing": sorted(set(panel) - set(covered)),
                      "panel_rows": int(len(panel_rows)), "ntc_rows": int(len(rows) - len(panel_rows)),
                      "ntc_per_group": args.ntc_per_group, "seed": args.seed,
                      "author_flags_applied": False},
        "per_target_cells": {"median": float(per_target.cells.median()),
                             "q10": float(per_target.cells.quantile(0.1)),
                             "min": float(per_target.cells.min()),
                             "targets_ge_100_cells": int((per_target.cells >= 100).sum())},
        "integrity": {"rows_sum_to_total_counts": True, "integer_counts": True,
                      "stored_dtype": str(X.dtype)},
        "output": {"path": str(args.out), "bytes": args.out.stat().st_size, "sha256": digest,
                   "shape": list(X.shape), "nnz": int(X.nnz)},
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    per_target.to_csv(args.report_dir / "per_target.csv")
    with open(manifest_path, "x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"done: {len(covered)}/{len(panel)} targets; median cells/target "
        f"{manifest['per_target_cells']['median']:.0f}; output {args.out}")


if __name__ == "__main__":
    main()
