"""Compact twins of the contract shards, read fast by the training (version 4).

Why: in the two v3 trainings the GPU computed a step in about 66 ms and waited for its batches 81-84% of the time
(diagnosi_r1/DIAGNOSI.md). The contract shards are h5ad files whose counts are gzip-4 compressed in chunks of about
8,000 values; decompressing them is CPU work that the four cores of a Kaggle GPU machine cannot do at the GPU's pace.

A twin keeps the same rows, in the same order, with the same counts on the same native features: only the encoding
changes. Rows are cut into blocks; each block stores three streams, each as little-endian unsigned integers of the
narrowest width that holds it (uint16 when it can, uint32 otherwise), byte-shuffled and compressed with zstd through
pyarrow (present on Kaggle and Colab images):
- n: the nonzeros of each row;
- d: the feature indices, delta-coded within each row (the first index of a row is absolute), rows sorted by index;
- v: the counts (integers >= 0; anything else is refused).
The file is an uncompressed .npz holding the payloads (uint8 arrays), a block table and a JSON `meta` with the source's
name, bytes and sha256, so a training can resolve a twin against its prepass state without mounting the h5ad.

`encode` writes a twin and proves it: every block is decoded again and compared exactly with the source arrays.

    python fastshard.py encode <shard.h5ad> <out.fcsr.npz>      (prints the receipt as JSON)
    python fastshard.py check <shard.h5ad> <twin.fcsr.npz>      (decodes the twin and compares it with the shard)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

FORMAT = "vcc2026-fcsr"
FORMAT_VERSION = 1
SUFFIX = ".fcsr.npz"
BLOCK_ROWS = 4096
LEVEL = 3
_WIDTHS = {2: np.dtype("<u2"), 4: np.dtype("<u4")}


def twin_name(shard_name: str) -> str:
    """The file name of the twin of a shard: <shard name>.fcsr.npz (the shard's own name kept whole)."""
    return f"{shard_name}{SUFFIX}"


def is_twin(path) -> bool:
    return str(path).endswith(SUFFIX)


def _codec(level=LEVEL):
    import pyarrow as pa
    return pa.Codec("zstd", compression_level=level)


def _width(values: np.ndarray) -> int:
    top = int(values.max()) if values.size else 0
    if top < 0:
        raise ValueError("negative values cannot be stored")
    return 2 if top <= 0xFFFF else 4


def _pack(values: np.ndarray, codec) -> tuple[np.ndarray, int, int]:
    """values (non-negative integers) -> (compressed payload, width in bytes, raw bytes)."""
    w = _width(values)
    raw = np.ascontiguousarray(values.astype(_WIDTHS[w], copy=False))
    shuffled = np.ascontiguousarray(raw.view(np.uint8).reshape(-1, w).T)
    comp = codec.compress(shuffled.tobytes(), asbytes=True)
    return np.frombuffer(comp, np.uint8), w, raw.nbytes


def _unpack(payload: np.ndarray, width: int, raw_bytes: int, codec) -> np.ndarray:
    if raw_bytes == 0:
        return np.zeros(0, _WIDTHS[width])
    buf = codec.decompress(payload.tobytes(), decompressed_size=raw_bytes, asbytes=True)
    shuffled = np.frombuffer(buf, np.uint8).reshape(width, -1)
    return np.ascontiguousarray(shuffled.T).view(_WIDTHS[width]).ravel()


def sort_within_rows(indices: np.ndarray, data: np.ndarray, indptr: np.ndarray):
    """Indices and data with each row sorted by feature index (stable), and whether anything moved."""
    n = indptr.size - 1
    row = np.repeat(np.arange(n, dtype=np.int64), np.diff(indptr))
    order = np.lexsort((indices, row))
    moved = bool((order != np.arange(order.size)).any())
    return indices[order], data[order], moved


def encode_arrays(data, indices, indptr, n_features: int, block_rows=BLOCK_ROWS, level=LEVEL):
    """Blocks of a CSR (data, indices, indptr) as (block table, payloads, facts). Refuses non-integer or negative counts,
    and repeated feature indices within a row."""
    data = np.asarray(data)
    indices = np.asarray(indices, np.int64)
    indptr = np.asarray(indptr, np.int64)
    if data.size and (np.any(data < 0) or np.any(data != np.round(data))):
        raise ValueError("counts must be integers >= 0")
    counts = np.round(data).astype(np.int64) if data.dtype.kind == "f" else data.astype(np.int64)
    indices, counts, moved = sort_within_rows(indices, counts, indptr)
    n = indptr.size - 1
    row = np.repeat(np.arange(n, dtype=np.int64), np.diff(indptr))
    delta = np.empty_like(indices)
    if indices.size:
        delta[1:] = indices[1:] - indices[:-1]
        first = indptr[:-1][np.diff(indptr) > 0]
        delta[first] = indices[first]
        is_first = np.zeros(delta.size, bool)
        is_first[first] = True
        if np.any(delta[~is_first] <= 0):
            raise ValueError("a row repeats a feature index")
    if indices.size and (indices.max() >= n_features or indices.min() < 0):
        raise ValueError("feature index outside the shard's features")
    codec = _codec(level)
    table, payloads = [], {}
    for b, r0 in enumerate(range(0, n, block_rows)):
        r1 = min(n, r0 + block_rows)
        lo, hi = int(indptr[r0]), int(indptr[r1])
        nnz = np.diff(indptr[r0:r1 + 1])
        pn, wn, rn = _pack(nnz, codec)
        pd_, wd, rd = _pack(delta[lo:hi], codec)
        pv, wv, rv = _pack(counts[lo:hi], codec)
        payloads[f"b{b}_n"], payloads[f"b{b}_d"], payloads[f"b{b}_v"] = pn, pd_, pv
        table.append([r0, r1 - r0, hi - lo, wn, rn, wd, rd, wv, rv])
    facts = {"n_rows": int(n), "nnz": int(indices.size), "counts_sum": int(counts.sum()),
             "n_features": int(n_features), "sorted_within_rows_in_source": not moved,
             "max_count": int(counts.max()) if counts.size else 0}
    return np.asarray(table, np.int64).reshape(-1, 9), payloads, facts


def sha256_file(path, chunk=16 << 20) -> tuple[str, float]:
    """sha256 of a file and the seconds the read took (the raw read speed of the storage)."""
    h, t0 = hashlib.sha256(), time.time()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest(), time.time() - t0


def read_h5ad_x(path):
    """The stored CSR of a contract shard (data, indices, indptr, shape), as the training reads it."""
    import h5py
    with h5py.File(path, "r") as f:
        g = f["X"]
        shape = tuple(int(v) for v in g.attrs["shape"])
        return g["data"][:], g["indices"][:], g["indptr"][:].astype(np.int64), shape


def encode(src, dst, block_rows=BLOCK_ROWS, level=LEVEL) -> dict:
    """Write the twin of contract shard `src` at `dst` (refusing to replace a file) and verify it block by block
    against the source arrays. Returns the receipt: source and twin bytes and sha256, facts and timings."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise FileExistsError(dst)
    source_sha, t_raw = sha256_file(src)
    t0 = time.time()
    data, indices, indptr, shape = read_h5ad_x(src)
    t_h5 = time.time() - t0
    t0 = time.time()
    table, payloads, facts = encode_arrays(data, indices, indptr, shape[1], block_rows, level)
    t_enc = time.time() - t0
    meta = {"format": FORMAT, "version": FORMAT_VERSION, "codec": "zstd", "level": level, "block_rows": block_rows,
            "byte_shuffle": True, "delta_within_rows": True, "source_name": src.name, "source_bytes": src.stat().st_size,
            "source_sha256": source_sha, "shape": list(shape), **facts}
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".partial.npz")
    np.savez(tmp, meta=np.array(json.dumps(meta)), blocks=table, **payloads)
    tmp.replace(dst)
    t0 = time.time()
    twin = FastShard(dst)
    d2, i2, p2 = twin.read_all()
    t_dec = time.time() - t0
    s_idx, s_dat, _ = sort_within_rows(np.asarray(indices, np.int64), np.asarray(data), np.asarray(indptr, np.int64))
    same = (np.array_equal(p2, indptr) and np.array_equal(i2, s_idx)
            and np.array_equal(d2.astype(np.int64), np.asarray(s_dat).astype(np.int64)))
    if not same:
        dst.unlink()
        raise AssertionError(f"{src.name}: the twin does not decode to the source arrays")
    twin_sha, _ = sha256_file(dst)
    return {"name": src.name, "twin": dst.name, "source_bytes": meta["source_bytes"], "source_sha256": source_sha,
            "twin_bytes": dst.stat().st_size, "twin_sha256": twin_sha, "verified": True, **facts,
            "seconds": {"raw_read_and_sha256": round(t_raw, 3), "h5py_read_decompress": round(t_h5, 3),
                        "encode": round(t_enc, 3), "decode_and_compare": round(t_dec, 3)}}


class FastShard:
    """A twin opened for reading. read_all() and read_rows(rows) return (data, indices, indptr) on native features, with
    the rows sorted by feature index; data as int32 (uint32 counts above 2**31 are refused)."""

    def __init__(self, path):
        self.path = Path(path)
        self.z = np.load(self.path, allow_pickle=False)
        self.meta = json.loads(str(self.z["meta"]))
        if self.meta.get("format") != FORMAT or self.meta.get("version") != FORMAT_VERSION:
            raise ValueError(f"{self.path}: not a {FORMAT} v{FORMAT_VERSION} file")
        self.blocks = np.asarray(self.z["blocks"], np.int64).reshape(-1, 9)
        self.n_rows = int(self.meta["n_rows"])
        self.shape = tuple(self.meta["shape"])
        self._codec = _codec(self.meta.get("level", LEVEL))

    def close(self):
        self.z.close()

    def _block(self, b):
        r0, nr, nnz, wn, rn, wd, rd, wv, rv = (int(v) for v in self.blocks[b])
        n = _unpack(self.z[f"b{b}_n"], wn, rn, self._codec).astype(np.int64)
        d = _unpack(self.z[f"b{b}_d"], wd, rd, self._codec).astype(np.int64)
        v = _unpack(self.z[f"b{b}_v"], wv, rv, self._codec)
        if n.size != nr or d.size != nnz or v.size != nnz or int(n.sum()) != nnz:
            raise ValueError(f"{self.path.name}: block {b} is inconsistent")
        ptr = np.concatenate([[0], np.cumsum(n)])
        if nnz == 0:
            return r0, ptr, np.zeros(0, np.int32), np.zeros(0, np.int32)
        cs = np.cumsum(d)
        starts = ptr[:-1]
        # the first index of a row is stored whole: subtract the running sum up to the row's start
        base_row = np.zeros(nr, np.int64)
        has = starts > 0
        base_row[has] = cs[starts[has] - 1]
        idx = cs - np.repeat(base_row, n)
        if v.dtype == np.uint32 and v.size and int(v.max()) > np.iinfo(np.int32).max:
            raise ValueError("a count above 2**31")
        return r0, ptr, idx.astype(np.int32), v.astype(np.int32)

    def read_all(self):
        datas, idxs, ptrs, off = [], [], [np.zeros(1, np.int64)], 0
        for b in range(len(self.blocks)):
            _, ptr, idx, v = self._block(b)
            datas.append(v)
            idxs.append(idx)
            ptrs.append(ptr[1:] + off)
            off += int(ptr[-1])
        data = np.concatenate(datas) if datas else np.zeros(0, np.int32)
        indices = np.concatenate(idxs) if idxs else np.zeros(0, np.int32)
        return data, indices, np.concatenate(ptrs)

    def read_rows(self, rows):
        """The given rows (any order, repeats allowed) as a CSR (data, indices, indptr); only their blocks are decoded."""
        rows = np.asarray(rows, np.int64)
        if rows.size and (rows.min() < 0 or rows.max() >= self.n_rows):
            raise IndexError("row outside the shard")
        br = int(self.meta["block_rows"])
        need = np.unique(rows // br)
        cache = {int(b): self._block(int(b)) for b in need}
        lens = np.zeros(rows.size, np.int64)
        for j, r in enumerate(rows):
            _, ptr, _, _ = cache[int(r // br)]
            loc = int(r % br)
            lens[j] = ptr[loc + 1] - ptr[loc]
        indptr = np.concatenate([[0], np.cumsum(lens)])
        data = np.empty(int(indptr[-1]), np.int32)
        indices = np.empty(int(indptr[-1]), np.int32)
        for j, r in enumerate(rows):
            _, ptr, idx, v = cache[int(r // br)]
            loc = int(r % br)
            a, b = ptr[loc], ptr[loc + 1]
            data[indptr[j]:indptr[j + 1]] = v[a:b]
            indices[indptr[j]:indptr[j + 1]] = idx[a:b]
        return data, indices, indptr


def check(src, twin) -> dict:
    data, indices, indptr, shape = read_h5ad_x(src)
    t = FastShard(twin)
    d2, i2, p2 = t.read_all()
    s_idx, s_dat, _ = sort_within_rows(np.asarray(indices, np.int64), np.asarray(data), indptr)
    ok = (tuple(t.shape) == tuple(shape) and np.array_equal(p2, indptr) and np.array_equal(i2, s_idx)
          and np.array_equal(d2.astype(np.int64), np.asarray(s_dat).astype(np.int64)))
    return {"source": str(src), "twin": str(twin), "equal": bool(ok), "rows": int(shape[0]), "nnz": int(indices.size)}


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "encode":
        print(json.dumps(encode(*args)))
    elif cmd == "check":
        print(json.dumps(check(*args)))
    else:
        raise SystemExit(__doc__)
