"""P1 of R-LAB, completed: read the layout of remote h5ad files over HTTP byte ranges, never the matrices.

For each URL: file size; X (dense or CSR, shape, dtype, compression, stored values); layers; obs columns with their
number of distinct values and the most frequent ones (targets, controls, batches, conditions); var index and columns.
That is what an adapter needs (which column holds the target, which value marks the controls, which the batch), and
it measures the cells a source can bring, instead of taking them from a paper. A read touches a few MB per file:
h5py opens a file-like object whose reads are HTTP Range requests with a block cache.

Writes one JSON per file into a NEW --out folder, plus index.json; a file that fails is recorded with its error.

    python inspect_remote.py --urls urls.json --out p1_r4/remote
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path

import numpy as np


class RangeFile(io.RawIOBase):
    """A read-only, seekable file over HTTP Range requests, cached by blocks.

    The cache keeps the most recently used blocks up to `max_bytes`: an adapter streams whole matrices through this
    reader, and an unbounded cache held every byte read (jobs 100 and 105 were killed for memory after about 5 GB of
    H1, 30/09). Evicted blocks are fetched again when needed."""

    def __init__(self, url: str, block: int = 1 << 20, max_bytes: int = 256 << 20):
        self.url, self.block, self.pos, self.cache, self.fetched = url, block, 0, OrderedDict(), 0
        self.max_blocks = max(4, max_bytes // block)
        self.etag = None
        self._resolve()

    def _resolve(self):
        """The final URL and the size, from a GET of one byte: hosts that redirect to signed storage URLs (Figshare
        to S3) sign them for the method used, and a URL resolved by HEAD refuses ranged GETs. Called again when a
        signed URL expires: Figshare's expire 10 seconds after signing (X-Amz-Expires=10, read on 1/10), so the
        caller uses the new URL at once. A failed resolution is retried with a pause."""
        req = urllib.request.Request(self.url, headers={"Range": "bytes=0-0", "User-Agent": "vcc2026-rlab/1"})
        for attempt in range(1, 6):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    total = r.headers.get("Content-Range", "").rsplit("/", 1)[-1]
                    size = int(total) if total.isdigit() else int(r.headers["Content-Length"])
                    etag = r.headers.get("ETag")
                    self.final_url = r.geturl()
                break
            except OSError:
                if attempt == 5:
                    raise
                time.sleep(5 * attempt)
        if getattr(self, "size", None) not in (None, size):
            raise OSError(f"the file changed while it was read: {size} bytes after {self.size}")
        self.size = size
        if self.etag and etag and etag != self.etag:
            raise OSError(f"the file changed while it was read: ETag {etag} after {self.etag}")
        self.etag = self.etag or etag      # every range must come from this same version of the file

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def _fetch(self, url, lo, hi):
        req = urllib.request.Request(url, headers={"Range": f"bytes={lo}-{hi}", "User-Agent": "vcc2026-rlab/1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read(), r.headers.get("ETag")

    def _get(self, lo, hi, max_resolves=20, max_failures=5):
        """Bytes lo..hi (inclusive) and the ETag they came with. A 400 or 403 is an expired signed URL: it is resolved
        again and the range requested at once, with no pause that would let the new signature expire too (job 109
        stopped after five 403 in a row, 1/10); other failures are retried after a growing pause."""
        resolves = failures = 0
        while True:
            try:
                return self._fetch(self.final_url, lo, hi)
            except urllib.error.HTTPError as err:
                if err.code in (400, 403) and resolves < max_resolves:
                    resolves += 1
                    self._resolve()
                    continue
                failures += 1
                if failures >= max_failures:
                    raise
                time.sleep(5 * failures)
            except OSError:
                failures += 1
                if failures >= max_failures:
                    raise
                time.sleep(5 * failures)

    def _blk(self, i):
        if i in self.cache:
            self.cache.move_to_end(i)
            return self.cache[i]
        lo, hi = i * self.block, min(self.size, (i + 1) * self.block) - 1
        data, etag = self._get(lo, hi)
        if self.etag and etag and etag != self.etag:
            raise OSError(f"the file changed while it was read: ETag {etag} after {self.etag}")
        if len(data) != hi - lo + 1:
            raise OSError(f"range {lo}-{hi} returned {len(data)} bytes: the server ignores Range")
        self.cache[i] = data
        self.fetched += len(data)
        while len(self.cache) > self.max_blocks:
            self.cache.popitem(last=False)
        return data

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        out, p = bytearray(), self.pos
        while len(out) < n:
            i = p // self.block
            data = self._blk(i)
            start = p - i * self.block
            take = data[start:start + (n - len(out))]
            out += take
            p += len(take)
        b[:n] = out
        self.pos += n
        return n


def text(values) -> list[str]:
    return [v.decode() if isinstance(v, bytes) else str(v) for v in values]


def describe_column(node, n_top: int = 12) -> dict:
    import h5py
    if isinstance(node, h5py.Group) and "categories" in node:
        cats = text(node["categories"][:])
        codes = node["codes"][:]
        vals, cnt = np.unique(codes, return_counts=True)
        order = np.argsort(-cnt)
        top = {(cats[vals[i]] if vals[i] >= 0 else "<NA>"): int(cnt[i]) for i in order[:n_top]}
        return {"kind": "categorical", "n": int(codes.size), "distinct": len(cats), "top": top}
    if isinstance(node, h5py.Dataset):
        if node.dtype.kind in "SOU" and node.shape and node.shape[0] <= 3_000_000:
            vals, cnt = np.unique(np.asarray(text(node[:])), return_counts=True)
            order = np.argsort(-cnt)
            return {"kind": "strings", "n": int(node.shape[0]), "distinct": int(vals.size),
                    "top": {str(vals[i]): int(cnt[i]) for i in order[:n_top]}}
        if node.dtype.kind in "iufb" and node.shape:
            head = node[: min(node.shape[0], 200_000)]
            return {"kind": "numeric", "dtype": str(node.dtype), "n": int(node.shape[0]),
                    "sample_min": float(np.nanmin(head)) if head.size else None,
                    "sample_max": float(np.nanmax(head)) if head.size else None}
        return {"kind": str(node.dtype), "shape": list(node.shape)}
    if isinstance(node, h5py.Group):
        return {"kind": "group", "keys": list(node.keys())[:20],
                "encoding": text([node.attrs.get("encoding-type", b"")])[0]}
    return {"kind": type(node).__name__}


def describe_matrix(node) -> dict:
    import h5py
    if isinstance(node, h5py.Dataset):
        info = {"format": "dense", "shape": list(node.shape), "dtype": str(node.dtype),
                "compression": node.compression, "chunks": list(node.chunks) if node.chunks else None}
        rows = node[:min(node.shape[0], 50)]
        info["first_rows_integer"] = bool(np.all(np.equal(np.mod(rows, 1), 0)))
        info["first_rows_max"] = float(rows.max()) if rows.size else None
        return info
    enc = text([node.attrs.get("encoding-type", b"")])[0]
    shape = [int(v) for v in node.attrs.get("shape", [])]
    data = node["data"]
    head = data[:min(data.shape[0], 200_000)]
    return {"format": enc or "group", "shape": shape, "dtype": str(data.dtype), "stored": int(data.shape[0]),
            "compression": data.compression, "chunks": list(data.chunks) if data.chunks else None,
            "sample_integer": bool(np.all(np.equal(np.mod(head, 1), 0))) if head.size else None,
            "sample_max": float(head.max()) if head.size else None}


def inspect(url: str) -> dict:
    import h5py
    t0 = time.time()
    fh = RangeFile(url)
    out = {"url": url, "bytes": fh.size}
    with h5py.File(io.BufferedReader(fh, buffer_size=1 << 20), "r") as f:
        out["top"] = list(f.keys())
        if "X" in f:
            out["X"] = describe_matrix(f["X"])
        if "layers" in f:
            out["layers"] = {k: describe_matrix(f["layers"][k]) for k in f["layers"].keys()}
        for frame in ("obs", "var"):
            if frame not in f:
                continue
            g = f[frame]
            if isinstance(g, h5py.Dataset):          # legacy anndata: one structured array
                names = list(g.dtype.names or [])
                out[frame] = {"legacy_structured": True, "rows": int(g.shape[0]), "columns": names}
                if frame == "obs" and g.shape[0] <= 3_000_000:
                    arr = g[:]
                    out[frame]["describe"] = {}
                    for c in names:
                        col = arr[c]
                        if col.dtype.kind in "SOU":
                            vals, cnt = np.unique(np.asarray(text(col)), return_counts=True)
                            order = np.argsort(-cnt)
                            out[frame]["describe"][c] = {"distinct": int(vals.size),
                                                         "top": {str(vals[i]): int(cnt[i]) for i in order[:12]}}
                continue
            index = text([g.attrs.get("_index", b"_index")])[0]
            cols = [k for k in g.keys() if k != "__categories"]
            entry = {"index": index, "columns": cols}
            if frame == "obs":
                entry["describe"] = {}
                for c in cols:
                    try:
                        entry["describe"][c] = describe_column(g[c])
                    except Exception as err:          # noqa: BLE001 - an inventory records what it cannot read
                        entry["describe"][c] = {"error": f"{type(err).__name__}: {err}"}
            else:
                try:
                    entry["rows"] = int(g[index].shape[0])
                    entry["first"] = text(g[index][:5])
                except Exception as err:              # noqa: BLE001
                    entry["error"] = f"{type(err).__name__}: {err}"
            out[frame] = entry
    out["seconds"] = round(time.time() - t0, 1)
    out["fetched_bytes"] = fh.fetched
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--urls", required=True, type=Path, help="JSON list of {id, url}")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    index = []
    for item in json.loads(a.urls.read_text(encoding="utf-8")):
        try:
            info = inspect(item["url"])
            status = "ok"
        except Exception as err:                      # noqa: BLE001
            info, status = {"url": item["url"], "error": f"{type(err).__name__}: {err}"}, "error"
        info["id"] = item["id"]
        (a.out / f"{item['id']}.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
        shape = (info.get("X") or {}).get("shape")
        index.append({"id": item["id"], "status": status, "bytes": info.get("bytes"), "X_shape": shape,
                      "X_format": (info.get("X") or {}).get("format"), "seconds": info.get("seconds"),
                      "error": info.get("error")})
        print(item["id"], status, shape, info.get("seconds"), info.get("error", ""), flush=True)
    (a.out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
