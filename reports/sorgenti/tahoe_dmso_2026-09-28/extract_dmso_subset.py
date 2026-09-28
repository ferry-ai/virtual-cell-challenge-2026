"""Tahoe-100M vehicle (DMSO_TF) cells from a systematic subset of the shards, summed per cell line x plate.

The complete extraction (extract_dmso.py, on Kaggle) plans all 3,388 shards before reading any count; on 28/09 its
planner covered about 400 shards an hour, reading one shard at a time. This script reads every --step-th shard
(0, step, 2*step, ...), which covers every plate in proportion because the shards are in plate order, with parallel
HTTP range requests: per shard the footer, the `drug` column of every row group, then the five needed columns of the
row groups that hold vehicle cells only (measured on shard 1031: the 1,364 vehicle cells sit in 3 consecutive row
groups of 29). Counts are summed in float64 per (cell_line_id, plate) over Tahoe's whole gene table (token order),
the negative first element of a cell dropped as in the official tutorial. Output in the format of extract_dmso.py's
`pseudobulk.npz` (`sums`, `n_cells`, `library`, `cell_line`, `plate`, `token_id`, `gene_symbol`, `ensembl_id`), with
`metadata/` (the small tables) and `manifest.json` (the shards read, cells and bytes), so corpus_tahoe.py reads it.

    scripts/py.cmd reports/sorgenti/tahoe_dmso_2026-09-28/extract_dmso_subset.py --out <new dir> --step 5
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

REPO = "tahoebio/Tahoe-100M"
N_SHARDS = 3388
VEHICLE = "DMSO_TF"
COLUMNS = ["genes", "expressions", "drug", "cell_line_id", "plate"]
META = Path("C:/Users/ferra/vcc2026-data/external/tahoe100m/metadata")


class RangeFile(io.RawIOBase):
    """A read-only, seekable view of a remote file through HTTP Range requests (counts the bytes received)."""

    def __init__(self, url: str, session: requests.Session, counter: list):
        self.session, self.counter = session, counter
        r = session.head(url, allow_redirects=True, timeout=60)
        r.raise_for_status()
        self.url, self.size, self.pos = r.url, int(r.headers["Content-Length"]), 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        self.pos = {io.SEEK_SET: offset, io.SEEK_CUR: self.pos + offset, io.SEEK_END: self.size + offset}[whence]
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        for attempt in range(5):
            try:
                r = self.session.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=120)
                if r.status_code != 206:
                    raise IOError(f"HTTP {r.status_code} for a range request (the server must honour Range)")
                data = r.content
                break
            except (requests.RequestException, IOError):
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
        b[:len(data)] = data
        self.pos += len(data)
        self.counter[0] += len(data)
        return len(data)


def shard_url(i: int, revision: str) -> str:
    return f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/data/train-{i:05d}-of-{N_SHARDS:05d}.parquet"


def read_shard(i: int, revision: str, tokens: np.ndarray, lines: dict, plates: dict) -> dict:
    counter = [0]
    with requests.Session() as s:
        f = RangeFile(shard_url(i, revision), s, counter)
        pf = pq.ParquetFile(pa.PythonFile(f, mode="r"))
        md = pf.metadata
        vehicle_groups = []
        for g in range(md.num_row_groups):
            drug = pf.read_row_group(g, columns=["drug"])["drug"]
            n = pc.sum(pc.cast(pc.equal(drug, VEHICLE), pa.int64())).as_py() or 0
            if n:
                vehicle_groups.append(g)
        out = {"shard": i, "row_groups": md.num_row_groups, "vehicle_row_groups": vehicle_groups, "groups": {}}
        V = tokens.size
        for g in vehicle_groups:
            t = pf.read_row_group(g, columns=COLUMNS)
            keep = pc.equal(t["drug"], VEHICLE)
            t = t.filter(keep)
            genes = t["genes"].combine_chunks()
            expr = t["expressions"].combine_chunks()
            if not np.array_equal(np.asarray(genes.offsets), np.asarray(expr.offsets)):
                raise ValueError(f"shard {i} rg {g}: genes and expressions misaligned")
            off = np.asarray(genes.offsets, dtype=np.int64)
            tok = np.asarray(genes.values, dtype=np.int64)
            val = np.asarray(expr.values, dtype=np.float64)
            drop = np.zeros(tok.size, dtype=bool)
            first = off[:-1][off[:-1] < off[1:]]
            drop[first[val[first] < 0]] = True            # the CLS marker, as in the official tutorial
            if (val[~drop] < 0).any():
                raise ValueError(f"shard {i} rg {g}: negative counts beyond the marker")
            pos = np.searchsorted(tokens, tok)
            pos = np.clip(pos, 0, V - 1)
            if (tokens[pos[~drop]] != tok[~drop]).any():
                raise ValueError(f"shard {i} rg {g}: tokens outside the gene table")
            cl = np.asarray(t["cell_line_id"].to_numpy(zero_copy_only=False)).astype(str)
            pl = np.asarray(t["plate"].to_numpy(zero_copy_only=False)).astype(str)
            cell = np.repeat(np.arange(cl.size), np.diff(off))
            keys = sorted(set(zip(cl.tolist(), pl.tolist())))
            kidx = {k: j for j, k in enumerate(keys)}
            code = np.array([kidx[k] for k in zip(cl.tolist(), pl.tolist())], dtype=np.int64)
            m = ~drop
            flat = code[cell[m]] * V + pos[m]
            block = np.bincount(flat, weights=val[m], minlength=len(keys) * V).reshape(len(keys), V)
            lib = np.bincount(cell[m], weights=val[m], minlength=cl.size)
            for j, key in enumerate(keys):
                acc = out["groups"].setdefault(key, [np.zeros(V), 0, 0.0])
                acc[0] += block[j]
                acc[1] += int((code == j).sum())
                acc[2] += float(lib[code == j].sum())
        f.close()
    out["bytes"] = counter[0]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--revision", default="main")
    ap.add_argument("--max-shards", type=int, default=0, help="stop after this many shards (0: all of the subset)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "metadata").mkdir()
    for name in ("gene", "cell_line", "drug", "sample"):
        shutil.copy2(META / f"{name}_metadata.parquet", args.out / "metadata" / f"{name}_metadata.parquet")
    gm = pq.read_table(META / "gene_metadata.parquet").to_pandas().sort_values("token_id")
    tokens = gm["token_id"].to_numpy(dtype=np.int64)
    if np.unique(tokens).size != tokens.size:
        raise ValueError("duplicate token ids in gene_metadata")
    shards = list(range(args.offset, N_SHARDS, args.step))
    if args.max_shards:
        shards = shards[:args.max_shards]
    sums, ncell, libs, per_shard = {}, {}, {}, []
    lock, t0, done_bytes = threading.Lock(), time.time(), 0
    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(read_shard, i, args.revision, tokens, {}, {}): i for i in shards}
        for k, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            with lock:
                for key, (vec, n, lib) in r["groups"].items():
                    if key not in sums:
                        sums[key], ncell[key], libs[key] = np.zeros(tokens.size), 0, 0.0
                    sums[key] += vec
                    ncell[key] += n
                    libs[key] += lib
                done_bytes += r["bytes"]
                per_shard.append({"shard": r["shard"], "row_groups": r["row_groups"],
                                  "vehicle_row_groups": r["vehicle_row_groups"], "bytes": r["bytes"],
                                  "vehicle_cells": int(sum(v[1] for v in r["groups"].values()))})
            if k % 20 == 0 or k == len(shards):
                print(f"{k}/{len(shards)} shards, {sum(ncell.values())} vehicle cells, {done_bytes / 1e9:.2f} GB, "
                      f"{time.time() - t0:.0f} s", flush=True)
    keys = sorted(sums)
    np.savez_compressed(args.out / "pseudobulk.npz", sums=np.vstack([sums[k] for k in keys]),
                        n_cells=np.array([ncell[k] for k in keys], dtype=np.int64),
                        library=np.array([libs[k] for k in keys]),
                        cell_line=np.array([k[0] for k in keys]), plate=np.array([k[1] for k in keys]),
                        token_id=tokens, gene_symbol=np.asarray(gm["gene_symbol"].fillna("").tolist(), dtype=str),
                        ensembl_id=np.asarray(gm["ensembl_id"].fillna("").tolist(), dtype=str))
    per_shard.sort(key=lambda x: x["shard"])
    manifest = {"stage": "tahoe_dmso_2026-09-28/extract_dmso_subset.py", "repo": REPO, "revision": args.revision,
                "complete": True, "subset": {"step": args.step, "offset": args.offset, "shards": len(shards)},
                "vehicle_cells": int(sum(ncell.values())), "groups": len(keys),
                "lines": len({k[0] for k in keys}), "plates": sorted({k[1] for k in keys}),
                "bytes_read": done_bytes, "seconds": round(time.time() - t0, 1), "per_shard": per_shard,
                "claim_type": "data extraction; no model result"}
    with (args.out / "manifest.json").open("x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps({k: manifest[k] for k in ("vehicle_cells", "groups", "lines", "bytes_read", "seconds")}))


if __name__ == "__main__":
    main()
