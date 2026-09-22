"""Selected rows of a remote CSR matrix, read as exact byte ranges in parallel.

h5py over an HTTP file object (`remote_ranges.HTTPRangeReader`) serves one block at a
time, so thousands of scattered rows cost thousands of sequential round trips. Here the
chunk map of ``X/data`` and ``X/indices`` is read once through h5py, each selected row is
turned into the byte ranges it occupies inside those chunks, ranges that sit close
together in the file are merged, and the merged ranges are fetched concurrently.

An uncompressed, unfiltered chunk is byte-addressable, which is what makes a partial-chunk
read exact. A compressed or filtered dataset is refused rather than read wrongly.

The fetch function is injected, so the byte arithmetic is tested against a local file
(`local_fetcher`) and the network is touched only by `http_fetcher`.
"""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

__all__ = [
    "ChunkMap", "chunk_map", "row_pieces", "plan_requests", "read_rows",
    "http_fetcher", "local_fetcher",
]

Fetch = Callable[[int, int], bytes]          # (file_start, file_stop) -> bytes


@dataclass(frozen=True)
class ChunkMap:
    """Where each chunk of a 1-D dataset starts in the file."""

    offsets: np.ndarray        # byte offset of chunk k, in chunk order
    chunk_len: int             # elements per chunk (the whole length if contiguous)
    itemsize: int
    n: int                     # total elements
    dtype: np.dtype

    def file_span(self, lo: int, hi: int) -> list[tuple[int, int, int, int]]:
        """Element range [lo, hi) as (file_start, file_stop, elem_lo, elem_hi) pieces."""
        if not 0 <= lo <= hi <= self.n:
            raise ValueError(f"element range [{lo}, {hi}) outside [0, {self.n}]")
        out = []
        pos = lo
        while pos < hi:
            k = pos // self.chunk_len
            stop = min(hi, (k + 1) * self.chunk_len)
            start_b = int(self.offsets[k]) + (pos - k * self.chunk_len) * self.itemsize
            out.append((start_b, start_b + (stop - pos) * self.itemsize, pos, stop))
            pos = stop
        return out


def chunk_map(ds) -> ChunkMap:
    """Chunk offsets of a 1-D h5py dataset; refuses filters, which break byte addressing."""
    if ds.ndim != 1:
        raise ValueError("only 1-D datasets are supported")
    plist = ds.id.get_create_plist()
    if plist.get_nfilters():
        raise ValueError(f"{ds.name}: filtered/compressed storage is not byte-addressable")
    dtype = ds.dtype
    n = int(ds.shape[0])
    if ds.chunks is None:
        off = ds.id.get_offset()
        if off is None:
            raise ValueError(f"{ds.name}: contiguous dataset without allocated storage")
        return ChunkMap(np.array([off], dtype=np.int64), max(n, 1), dtype.itemsize, n, dtype)
    chunk_len = int(ds.chunks[0])
    n_chunks = -(-n // chunk_len)
    offsets = np.full(n_chunks, -1, dtype=np.int64)

    def visit(info):
        k = info.chunk_offset[0] // chunk_len
        if info.filter_mask:
            raise ValueError(f"{ds.name}: chunk {k} carries a filter mask")
        offsets[k] = info.byte_offset

    ds.id.chunk_iter(visit)
    if (offsets < 0).any():
        raise ValueError(f"{ds.name}: {(offsets < 0).sum()} unallocated chunks")
    return ChunkMap(offsets, chunk_len, dtype.itemsize, n, dtype)


def row_pieces(indptr: np.ndarray, rows: Sequence[int], cmap: ChunkMap):
    """Per selected row, the (file_start, file_stop, elem_lo, elem_hi) pieces it needs."""
    return [cmap.file_span(int(indptr[r]), int(indptr[r + 1])) for r in rows]


def plan_requests(pieces: Sequence[tuple[int, int]], max_gap: int, max_request: int):
    """Merge sorted byte ranges whose gap is <= max_gap into requests <= max_request bytes.

    Returns a list of (start, stop) requests; every input range lies inside exactly one.
    """
    spans = sorted(set((int(a), int(b)) for a, b in pieces if b > a))
    out: list[list[int]] = []
    for a, b in spans:
        if out and a - out[-1][1] <= max_gap and max(b, out[-1][1]) - out[-1][0] <= max_request:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def read_rows(indptr, rows, data_map: ChunkMap, index_map: ChunkMap, fetch: Fetch, *,
              threads: int = 16, max_gap: int = 64 * 1024, max_request: int = 8 * 2**20,
              progress: Callable[[int, int], None] | None = None):
    """Values and column indices of the selected rows, in the order given.

    Returns ``(data, indices, row_ptr, bytes_fetched)``: ``data[row_ptr[i]:row_ptr[i+1]]``
    belongs to ``rows[i]``. Values keep the source dtype; the caller narrows them.
    """
    rows = [int(r) for r in rows]
    lengths = np.array([int(indptr[r + 1]) - int(indptr[r]) for r in rows], dtype=np.int64)
    row_ptr = np.concatenate([[0], np.cumsum(lengths)])
    total = int(row_ptr[-1])
    data = np.empty(total, dtype=data_map.dtype)
    indices = np.empty(total, dtype=index_map.dtype)
    work = []            # (target array, out_lo, out_hi, file_start, file_stop)
    for i, r in enumerate(rows):
        lo = int(indptr[r])
        for arr, cmap in ((data, data_map), (indices, index_map)):
            for fs, fe, el, eh in cmap.file_span(lo, int(indptr[r + 1])):
                o = int(row_ptr[i]) + (el - lo)
                work.append((arr, o, o + (eh - el), fs, fe))
    requests = plan_requests([(w[3], w[4]) for w in work], max_gap, max_request)
    starts = np.array([a for a, _ in requests], dtype=np.int64)
    by_request: list[list[tuple]] = [[] for _ in requests]
    for w in work:
        k = int(np.searchsorted(starts, w[3], side="right")) - 1
        if not (requests[k][0] <= w[3] and w[4] <= requests[k][1]):
            raise AssertionError("piece outside its planned request")
        by_request[k].append(w)
    fetched = 0
    done = 0
    lock = threading.Lock()

    def run(k: int):
        nonlocal fetched, done
        a, b = requests[k]
        buf = fetch(a, b)
        if len(buf) != b - a:
            raise RuntimeError(f"short read: {len(buf)} of {b - a} bytes at {a}")
        for arr, o0, o1, fs, fe in by_request[k]:
            arr[o0:o1] = np.frombuffer(buf, dtype=arr.dtype, count=o1 - o0, offset=fs - a)
        with lock:
            fetched += b - a
            done += 1
            if progress is not None:
                progress(done, len(requests))

    with ThreadPoolExecutor(max_workers=threads) as ex:
        for f in [ex.submit(run, k) for k in range(len(requests))]:
            f.result()
    return data, indices, row_ptr, fetched


def local_fetcher(path) -> Fetch:
    """Byte ranges from a local file: the test double for `http_fetcher`."""
    def fetch(a: int, b: int) -> bytes:
        with open(path, "rb") as fh:
            fh.seek(a)
            return fh.read(b - a)
    return fetch


def http_fetcher(url: str, *, expected_size: int | None = None, retries: int = 5,
                 timeout: float = 120.0) -> Fetch:
    """Byte ranges over HTTP. Refuses anything but an exact 206 of the requested span."""
    import httpx

    local = threading.local()

    def client():
        c = getattr(local, "client", None)
        if c is None:
            c = local.client = httpx.Client(timeout=timeout, follow_redirects=True,
                                            headers={"Accept-Encoding": "identity"})
        return c

    def fetch(a: int, b: int) -> bytes:
        last = None
        for attempt in range(retries):
            try:
                r = client().get(url, headers={"Range": f"bytes={a}-{b - 1}"})
                if r.status_code != 206:
                    raise RuntimeError(f"HTTP {r.status_code}: server did not honour Range")
                m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", r.headers.get("Content-Range", ""))
                if not m or int(m[1]) != a or int(m[2]) != b - 1:
                    raise RuntimeError(f"unexpected Content-Range {r.headers.get('Content-Range')!r}")
                if expected_size is not None and int(m[3]) != expected_size:
                    raise RuntimeError("remote size changed during the read")
                if len(r.content) != b - a:
                    raise RuntimeError("incomplete range body")
                return r.content
            except Exception as exc:  # network errors are retried, then raised
                last = exc
                time.sleep(min(30.0, 2.0 ** attempt))
        raise RuntimeError(f"range {a}-{b} failed after {retries} attempts: {last}")

    return fetch
