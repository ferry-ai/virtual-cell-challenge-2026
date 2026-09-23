"""Stage 102: X-Atlas/Orion panel pseudobulk, one batch file at a time.

Orion (Xaira; HCT116 and HEK293T, genome-wide CRISPRi, cells fixed before 10x Chromium,
aligned to GRCh38 2024-A) is published as 332 parquet files, one per GEM batch. Each file is
ONE row group holding ~13,000 targets, so there is nothing to skip: every file is read
whole. This stage downloads a file with parallel range requests, keeps only the cells of the
panel targets and of the non-targeting guides that pass the dual-guide filter, sums their
counts per (batch, target), writes that partial to ``--work``, and deletes the download.
A partial that already exists is skipped, so the stage resumes after an interruption.

``--finalize`` merges the partials into one h5ad of pseudobulk rows with the columns stage
98 reads (``target``, ``donor`` = a pool of GEM batches, ``condition`` = the line, ``n_cells``), so
Orion goes through `effects_from_pseudobulk` exactly like CD4: each batch's knockdown
against the controls of the same batches (``--pools``, default 8).

Licence: CC-BY-NC-SA-4.0. Using Orion in a submission needs the owner's decision (D-004 d);
measuring it does not.

    python scripts/102_extract_orion_panel.py --line HCT116 --work <data_root>/interim/orion_hct116
    python scripts/102_extract_orion_panel.py --line HCT116 --work <...> --finalize --out <h5ad> \
        --report-dir reports/orion_2026-09-22
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.remote_csr import http_fetcher  # noqa: E402

REPO = "Xaira-Therapeutics/X-Atlas-Orion"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main/"
DATA_ROOT = Path("C:/Users/ferra/vcc2026-data")
NTC = "Non-Targeting"


def list_files(line: str) -> list[tuple[str, int]]:
    import httpx
    r = httpx.get(f"https://huggingface.co/api/datasets/{REPO}/tree/main/data", timeout=60)
    r.raise_for_status()
    out = [(i["path"], int(i["size"])) for i in r.json()
           if i.get("type") == "file" and i["path"].startswith(f"data/{line}_")]
    return sorted(out)


def download(path: str, size: int, dest: Path, threads: int = 8, chunk: int = 16 * 2**20) -> None:
    fetch = http_fetcher(BASE + path, expected_size=size)
    spans = [(a, min(a + chunk, size)) for a in range(0, size, chunk)]
    with open(dest, "wb") as fh:
        fh.truncate(size)
    def run(span):
        a, b = span
        buf = fetch(a, b)
        with open(dest, "r+b") as fh:
            fh.seek(a)
            fh.write(buf)
    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(run, spans))


def gene_tokens(work: Path) -> pd.DataFrame:
    local = work / "gene_metadata.parquet"
    if not local.exists():
        import httpx
        r = httpx.get(BASE + "metadata/gene_metadata.parquet", timeout=120, follow_redirects=True)
        r.raise_for_status()
        local.write_bytes(r.content)
    return pd.read_parquet(local)


def process_file(parquet: Path, panel_index: dict[str, int], n_tokens: int, batch_rows: int = 2048):
    """Summed counts, cells and UMIs per selected target in one batch file."""
    import pyarrow.parquet as pq

    n_groups = len(panel_index)
    sums = np.zeros((n_groups, n_tokens), dtype=np.float64)
    cells = np.zeros(n_groups, dtype=np.int64)
    umis = np.zeros(n_groups, dtype=np.float64)
    pf = pq.ParquetFile(parquet)
    samples = set()
    for batch in pf.iter_batches(batch_size=batch_rows,
                                 columns=["gene_token_id", "gene_expression", "gene_target",
                                          "pass_guide_filter", "total_counts", "sample"]):
        tgt = batch.column("gene_target").to_numpy(zero_copy_only=False).astype(str)
        ok = batch.column("pass_guide_filter").to_numpy(zero_copy_only=False) == 1
        grp = np.array([panel_index.get(t, -1) for t in tgt])
        keep = ok & (grp >= 0)
        samples.update(batch.column("sample").to_numpy(zero_copy_only=False).astype(str).tolist())
        if not keep.any():
            continue
        tok_col, expr_col = batch.column("gene_token_id"), batch.column("gene_expression")
        offsets = tok_col.offsets.to_numpy()
        tok = tok_col.values.to_numpy()
        expr = expr_col.values.to_numpy()
        rows = np.flatnonzero(keep)
        lens = offsets[rows + 1] - offsets[rows]
        idx = np.concatenate([np.arange(offsets[r], offsets[r + 1]) for r in rows]) if rows.size else np.zeros(0, int)
        g = np.repeat(grp[rows], lens)
        flat = g * n_tokens + tok[idx]
        sums += np.bincount(flat, weights=expr[idx], minlength=n_groups * n_tokens).reshape(n_groups, n_tokens)
        cells += np.bincount(grp[rows], minlength=n_groups)
        umis += np.bincount(grp[rows], weights=batch.column("total_counts").to_numpy(zero_copy_only=False)[rows],
                            minlength=n_groups)
    return sums, cells, umis, sorted(samples)


def finalize(args, groups: list[str], tokens: pd.DataFrame) -> None:
    import anndata as ad
    import scipy.sparse as sp

    parts = sorted(args.work.glob("part_*.npz"))
    # Batches are summed into `--pools` pools, each with its OWN non-targeting cells, so every
    # knockdown is still compared with controls from the same GEM batches. One row per batch
    # would hold ~2 cells per target and ~1 GB of rows for a line.
    n_pools = max(1, min(args.pools, len(parts)))
    sums = None
    cells = np.zeros((n_pools, len(groups)))
    umis = np.zeros((n_pools, len(groups)))
    members = [[] for _ in range(n_pools)]
    for i, part in enumerate(parts):
        z = np.load(part, allow_pickle=False)
        k = i % n_pools
        if sums is None:
            sums = np.zeros((n_pools,) + z["sums"].shape, dtype=np.float32)
        sums[k] += z["sums"]
        cells[k] += z["cells"]
        umis[k] += z["umis"]
        members[k].append(str(z["batch"]))
    rows, obs = [], []
    for k in range(n_pools):
        for gi, name in enumerate(groups):
            if cells[k, gi] > 0:
                rows.append(sp.csr_matrix(sums[k, gi:gi + 1]))
                obs.append({"target": "non-targeting" if name == NTC else name, "donor": f"pool{k}",
                            "condition": args.line, "n_cells": float(cells[k, gi]),
                            "total_counts": float(umis[k, gi])})
    del sums
    X = sp.vstack(rows, format="csr").astype(np.float32)
    names = tokens.set_index("gene_token_id").reindex(range(X.shape[1]))["gene_name"].fillna("").astype(str)
    var = pd.DataFrame({"token": np.arange(X.shape[1])}, index=names.to_numpy())
    keep = var.index != ""
    X, var = X[:, np.flatnonzero(keep)], var[keep]
    out = ad.AnnData(X=X, obs=pd.DataFrame(obs, index=[f"orion:{i}" for i in range(len(obs))]), var=var)
    out.var_names_make_unique()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise FileExistsError(args.out)
    out.write_h5ad(args.out, compression="gzip")
    per_target = out.obs[out.obs.target != "non-targeting"].groupby("target").n_cells.sum()
    manifest = {"stage": "102_extract_orion_panel", "written_utc": datetime.now(timezone.utc).isoformat(),
                "line": args.line, "files": len(parts), "rows": int(out.n_obs), "genes": int(out.n_vars),
                "panel_targets_found": int(per_target.size),
                "cells_per_target": {"median": float(per_target.median()), "q10": float(per_target.quantile(0.1)),
                                     "min": float(per_target.min())},
                "ntc_cells": float(out.obs.loc[out.obs.target == "non-targeting", "n_cells"].sum()),
                "filter": "pass_guide_filter == 1", "licence": "CC-BY-NC-SA-4.0",
                "pools": {f"pool{k}": m for k, m in enumerate(members)},
                "output": {"path": str(args.out), "sha256": hashlib.sha256(args.out.read_bytes()).hexdigest()}}
    args.report_dir.mkdir(parents=True, exist_ok=True)
    with open(args.report_dir / f"manifest_{args.line}.json", "x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"finalized {args.line}: {manifest['panel_targets_found']} targets, median cells "
        f"{manifest['cells_per_target']['median']:.0f}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", choices=["HCT116", "HEK293T"], required=True)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--max-files", type=int, default=None, help="pilot: stop after N files")
    p.add_argument("--finalize", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--report-dir", type=Path, default=None)
    p.add_argument("--pools", type=int, default=8, help="--finalize: batch pools, each with its own controls")
    args = p.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()
    groups = panel + [NTC]
    panel_index = {t: i for i, t in enumerate(groups)}
    tokens = gene_tokens(args.work)
    n_tokens = int(tokens["gene_token_id"].max()) + 1
    if args.finalize:
        if args.out is None or args.report_dir is None:
            raise SystemExit("--finalize needs --out and --report-dir")
        finalize(args, groups, tokens)
        return
    files = list_files(args.line)
    log(f"{args.line}: {len(files)} files, {sum(s for _, s in files) / 1e9:.1f} GB; {n_tokens} gene tokens")
    done = 0
    t0 = time.monotonic()
    for path, size in files[: args.max_files]:
        name = Path(path).stem
        part = args.work / f"part_{name}.npz"
        if part.exists():
            continue
        tmp = args.work / f"{name}.parquet.download"
        t1 = time.monotonic()
        download(path, size, tmp, threads=args.threads)
        sums, cells, umis, samples = process_file(tmp, panel_index, n_tokens)
        tmp_part = part.with_suffix(".tmp.npz")
        np.savez_compressed(tmp_part, sums=sums.astype(np.float32), cells=cells, umis=umis,
                            batch=name, samples=np.array(samples), source_bytes=size)
        tmp_part.replace(part)
        tmp.unlink()
        done += 1
        log(f"  {name}: {size / 2**20:.0f} MiB in {time.monotonic() - t1:.0f}s; panel cells {cells[:-1].sum()}, "
            f"NTC {cells[-1]} ({done} done, {time.monotonic() - t0:.0f}s)")


if __name__ == "__main__":
    main()
