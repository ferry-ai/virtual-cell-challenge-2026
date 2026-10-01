"""Where the batch loader of train_cellnet.py spends its time, measured on a Kaggle CPU runtime (no GPU quota).

1/10/2026, after rlab-cellnet-r1: the GPU waited for data 87% of the time (about 630 cells/s per arm, two arms in
parallel, each with two loader processes, on 4 CPUs) and the evaluation read its 146 shards in 1,621 s. This kernel
measures, on the training shards of the prepass state rlab-prepass-r3, each measurement on shards no earlier one read
(the page cache would otherwise hide the reads):
1. the raw read of shard files (MB/s), one at a time and four at once;
2. read_csr in parts: h5py's read of X (I/O and gzip decompression; then again from the page cache), the conversion as
   it is (feature columns, COO to CSR, sort) and a direct filter of the CSR arrays, which must give the same matrix;
3. the batch stream played in this process, read_csr as it is and with the direct filter (cells/s, time in reads);
4. the stream through a DataLoader with 2 and 3 loader processes and a consumer that does nothing, direct filter.
Writes /kaggle/working/profile.json after each measurement. Run as the code file of a CPU kernel that attaches
rlab-cellnet-code, the six datasets of the first training and the output of rlab-prepass-r3.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py
import numpy as np

INPUT, OUT, OWNER = Path("/kaggle/input"), Path("/kaggle/working"), "davidmaisterx"
WINDOW = float(os.environ.get("PROFILE_WINDOW_SECONDS", 150))


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / OWNER / slug, INPUT / "notebooks" / OWNER / slug,
              INPUT / "kernels" / OWNER / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts below {INPUT}")
    return hits[0]


CODE = mount("rlab-cellnet-code")
sys.path.insert(0, str(CODE))
import cell_data as CD  # noqa: E402
import cellnet as CN  # noqa: E402
import train_cellnet as TC  # noqa: E402
import torch  # noqa: E402

res = {"started_utc": TC.now(), "cpus": os.cpu_count(), "window_seconds": WINDOW}


def save():
    (OUT / "profile.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


def rss_children_mb():
    try:
        import psutil
        me = psutil.Process()
        return round(sum(c.memory_info().rss for c in me.children(recursive=True)) / 2**20, 1)
    except Exception:  # noqa: BLE001 - a report only
        return None


def read_csr_fast(path, official_index, measured, gene_of_axis, n_model_genes):
    """The candidate: the same matrix as CN.read_csr without COO, sum or sort. Columns are remapped and filtered in
    place; the row pointer comes from a cumulative count of the kept entries."""
    import scipy.sparse as sp
    with h5py.File(path, "r") as f:
        g = f["X"]
        shape = tuple(int(v) for v in g.attrs["shape"])
        data, indices, indptr = g["data"][:], g["indices"][:], g["indptr"][:].astype(np.int64)
    col, mask, _ = CD.feature_columns(official_index, measured, gene_of_axis, n_model_genes)
    new_col = col[indices]
    ok = new_col >= 0
    kept = np.concatenate([[0], np.cumsum(ok, dtype=np.int64)])
    m = sp.csr_matrix((data[ok].astype(np.float32, copy=False), new_col[ok].astype(np.int32), kept[indptr]),
                      shape=(shape[0], n_model_genes))
    return m, mask


READ = {"seconds": 0.0, "n": 0}


def timed(fn):
    def wrapped(*args, **kw):
        t = time.time()
        out = fn(*args, **kw)
        READ["seconds"] += time.time() - t
        READ["n"] += 1
        return out
    return wrapped


ORIGINAL = CN.read_csr

# ---------------------------------------------------------------------------------------------- state
t = time.time()
prepass = mount("rlab-prepass-r3") / "prepass"
with open(prepass / TC.STATE, "rb") as fh:
    st = pickle.load(fh)
shards = st["shards"]
for s, p in zip(shards, TC.resolve_shards(shards, [INPUT])):
    s["path"] = p
stix = {s: i for i, s in enumerate(st["studies"])}
for s in shards:
    s["stu"] = stix[s["study"]]
G = st["G"]
lib_rows = {}
for k in range(len(st["key_names"])):
    valid = np.flatnonzero(st["pool_sid"][k] >= 0)
    if valid.size:
        lc = st["pool_libc"][k][valid]
        lib_rows[k] = {int(l): valid[lc == l] for l in np.unique(lc)}
train_ids = sorted((i for i, s in enumerate(shards) if len(s["train_rows"])), key=lambda i: -shards[i]["bytes"])
res["state"] = {"seconds": round(time.time() - t, 1), "shards": len(shards), "training_shards": len(train_ids),
                "training_cells": int(sum(len(shards[i]["train_rows"]) for i in train_ids)),
                "training_bytes": int(sum(shards[i]["bytes"] for i in train_ids))}
save()
print("state", res["state"], flush=True)

# shards dealt round-robin by size into disjoint groups, so each group has the same mix
pool = list(train_ids)
take = lambda n: [pool.pop(0) for _ in range(min(n, len(pool)))]  # noqa: E731
GROUPS = {"raw_one": take(2), "raw_four": take(4), "convert": take(3)}
rest = pool[:]
n_groups = 4
dealt = [rest[g::n_groups] for g in range(n_groups)]
GROUPS.update({"stream_as_is": dealt[0], "stream_direct": dealt[1], "loader_2": dealt[2], "loader_3": dealt[3]})
res["groups"] = {k: {"shards": len(v), "bytes": int(sum(shards[i]["bytes"] for i in v)),
                     "training_cells": int(sum(len(shards[i]["train_rows"]) for i in v))} for k, v in GROUPS.items()}
save()


def raw_read(path):
    n = 0
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            n += len(b)
    return n


# ---------------------------------------------------------------------------------------------- 1. raw reads
t = time.time()
nbytes = sum(raw_read(shards[i]["path"]) for i in GROUPS["raw_one"])
dt = time.time() - t
res["raw_one_at_a_time"] = {"bytes": nbytes, "seconds": round(dt, 2), "mb_per_s": round(nbytes / 2**20 / dt, 1)}
t = time.time()
with ThreadPoolExecutor(4) as ex:
    nbytes = sum(ex.map(raw_read, [shards[i]["path"] for i in GROUPS["raw_four"]]))
dt = time.time() - t
res["raw_four_at_once"] = {"bytes": nbytes, "seconds": round(dt, 2), "mb_per_s": round(nbytes / 2**20 / dt, 1)}
save()
print("raw", res["raw_one_at_a_time"], res["raw_four_at_once"], flush=True)

# ---------------------------------------------------------------------------------------------- 2. read_csr in parts
rows = []
for i in GROUPS["convert"]:
    s = shards[i]
    r = {"shard": s["name"], "bytes": s["bytes"], "cells": int(s["n"]), "training_rows": len(s["train_rows"])}
    t = time.time()
    with h5py.File(s["path"], "r") as f:
        g = f["X"]
        r["compression"] = g["data"].compression
        r["chunks"] = list(g["data"].chunks) if g["data"].chunks else None
        data, indices, indptr = g["data"][:], g["indices"][:], g["indptr"][:]
    r["h5_read_cold_s"] = round(time.time() - t, 2)
    r["nnz"] = int(data.size)
    r["dtypes"] = [str(data.dtype), str(indices.dtype), str(indptr.dtype)]
    t = time.time()
    with h5py.File(s["path"], "r") as f:
        g = f["X"]
        _ = g["data"][:], g["indices"][:], g["indptr"][:]
    r["h5_read_cached_s"] = round(time.time() - t, 2)
    t = time.time()
    m_old, mask_old = ORIGINAL(s["path"], s["official_index"], s["measured"], st["gene_of_axis"], G)
    r["read_csr_as_is_cached_s"] = round(time.time() - t, 2)
    t = time.time()
    m_new, mask_new = read_csr_fast(s["path"], s["official_index"], s["measured"], st["gene_of_axis"], G)
    r["read_csr_direct_cached_s"] = round(time.time() - t, 2)
    m_chk = m_new.copy()
    m_chk.sort_indices()
    r["same_matrix"] = bool(m_old.shape == m_chk.shape and np.array_equal(m_old.indptr, m_chk.indptr)
                            and np.array_equal(m_old.indices, m_chk.indices) and np.array_equal(m_old.data, m_chk.data)
                            and np.array_equal(mask_old, mask_new))
    keep = np.asarray(s["train_rows"])
    t = time.time()
    _ = m_new[keep]
    r["row_select_s"] = round(time.time() - t, 2)
    rows.append(r)
    res["convert"] = rows
    save()
    print("convert", r, flush=True)
    del data, indices, indptr, m_old, m_new, m_chk


# ---------------------------------------------------------------------------------------------- 3-4. streams
def only(ids):
    """The prepass shards with training rows kept only in `ids` (the others are not read)."""
    keep = set(ids)
    return [s if k in keep else {**s, "train_rows": np.zeros(0, np.int64)} for k, s in enumerate(shards)]


def stream_rate(name, ids, workers, reader):
    CN.read_csr = timed(reader)
    READ["seconds"], READ["n"] = 0.0, 0
    sub = only(ids)
    W = max(1, workers)
    stream = TC.BatchStream(sub, st["gene_of_axis"], G, lib_rows, len(st["symbols"]), 256, 4, 64, 0, W, 0)
    loader = torch.utils.data.DataLoader(stream, batch_size=None, num_workers=workers,
                                         prefetch_factor=8 if workers else None)
    it = iter(loader)
    t0 = time.time()
    stamps, cells = [], 0
    first = None
    while time.time() - t0 < WINDOW:
        b = next(it)
        cells += int(b["sid"].shape[0])
        now = time.time()
        if first is None:
            first = now - t0
        stamps.append((now - t0, cells))
    rss = rss_children_mb()
    del it, loader
    half = [x for x in stamps if x[0] >= stamps[-1][0] / 2]
    late = (half[-1][1] - half[0][1]) / max(half[-1][0] - half[0][0], 1e-9) if len(half) > 1 else None
    out = {"workers": workers, "batches": len(stamps), "cells": cells, "seconds": round(stamps[-1][0], 1),
           "first_batch_s": round(first, 1),
           "cells_per_s_after_first": round((cells - stamps[0][1]) / max(stamps[-1][0] - first, 1e-9), 1),
           "cells_per_s_second_half": round(late, 1) if late else None,
           "children_rss_mb": rss}
    if workers == 0:
        out["shard_reads"] = READ["n"]
        out["read_seconds"] = round(READ["seconds"], 1)
        out["read_fraction"] = round(READ["seconds"] / stamps[-1][0], 3)
    CN.read_csr = ORIGINAL
    res[name] = out
    save()
    print(name, out, flush=True)


stream_rate("stream_as_is", GROUPS["stream_as_is"], 0, ORIGINAL)
stream_rate("stream_direct", GROUPS["stream_direct"], 0, read_csr_fast)
stream_rate("loader_2", GROUPS["loader_2"], 2, read_csr_fast)
stream_rate("loader_3", GROUPS["loader_3"], 3, read_csr_fast)
res["finished_utc"] = TC.now()
save()
print("done", flush=True)
