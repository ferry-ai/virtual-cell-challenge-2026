"""Tests for `vcc2026.remote_csr`: exact rows from byte ranges of a chunked CSR file.

Each test pins a way a range reader could return plausible wrong numbers:

* a row that straddles a chunk boundary, read from the wrong chunk offset;
* merged requests that drop or shift a piece;
* a compressed dataset read as raw bytes;
* a short read accepted silently.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.remote_csr import (  # noqa: E402
    chunk_map, local_fetcher, plan_requests, read_rows,
)


def _write_csr(path: Path, rng, n_rows=40, n_cols=50, chunk=7, compression=None):
    dense = rng.poisson(0.4, size=(n_rows, n_cols)).astype(np.float64)
    dense[rng.random(dense.shape) < 0.5] = 0.0
    indptr = [0]
    data, idx = [], []
    for row in dense:
        nz = np.flatnonzero(row)
        data.extend(row[nz]); idx.extend(nz)
        indptr.append(len(data))
    with h5py.File(path, "w") as f:
        g = f.create_group("X")
        # a filler dataset first, so chunk offsets are not simply sequential from zero
        f.create_dataset("filler", data=np.arange(1000, dtype=np.int64))
        g.create_dataset("data", data=np.array(data), chunks=(chunk,), compression=compression)
        g.create_dataset("indices", data=np.array(idx, dtype=np.int64), chunks=(chunk,),
                         compression=compression)
        g.create_dataset("indptr", data=np.array(indptr, dtype=np.int64))
    return dense


class RemoteCsrTests(unittest.TestCase):
    def test_selected_rows_match_h5py_including_chunk_straddles(self):
        rng = np.random.default_rng(0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.h5"
            dense = _write_csr(path, rng)
            with h5py.File(path, "r") as f:
                dmap, imap = chunk_map(f["X/data"]), chunk_map(f["X/indices"])
                indptr = f["X/indptr"][:]
            rows = [39, 0, 5, 6, 17, 18, 22]          # unsorted, adjacent, and repeated order
            for gap in (0, 30, 10_000):               # no merge, some merge, one request
                data, idx, ptr, fetched = read_rows(indptr, rows, dmap, imap, local_fetcher(path),
                                                    threads=3, max_gap=gap)
                for i, r in enumerate(rows):
                    got = np.zeros(dense.shape[1])
                    got[idx[ptr[i]:ptr[i + 1]]] = data[ptr[i]:ptr[i + 1]]
                    np.testing.assert_array_equal(got, dense[r])
                self.assertGreater(fetched, 0)

    def test_contiguous_dataset_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("pad", data=np.zeros(13))
                f.create_dataset("v", data=np.arange(100, dtype=np.float64))
            with h5py.File(path, "r") as f:
                cmap = chunk_map(f["v"])
            fetch = local_fetcher(path)
            (a, b, lo, hi), = cmap.file_span(10, 20)
            np.testing.assert_array_equal(np.frombuffer(fetch(a, b), dtype=np.float64),
                                          np.arange(10, 20, dtype=np.float64))

    def test_compressed_dataset_is_refused(self):
        rng = np.random.default_rng(1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "z.h5"
            _write_csr(path, rng, compression="gzip")
            with h5py.File(path, "r") as f, self.assertRaises(ValueError):
                chunk_map(f["X/data"])

    def test_short_read_raises(self):
        rng = np.random.default_rng(2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.h5"
            _write_csr(path, rng)
            with h5py.File(path, "r") as f:
                dmap, imap = chunk_map(f["X/data"]), chunk_map(f["X/indices"])
                indptr = f["X/indptr"][:]
            good = local_fetcher(path)
            with self.assertRaises(RuntimeError):
                read_rows(indptr, [3], dmap, imap, lambda a, b: good(a, b)[:-1], threads=1)

    def test_plan_requests_covers_every_piece_once(self):
        pieces = [(0, 10), (10, 20), (25, 30), (100, 120), (119, 125)]
        plan = plan_requests(pieces, max_gap=5, max_request=1000)
        self.assertEqual(plan, [(0, 30), (100, 125)])
        plan = plan_requests(pieces, max_gap=5, max_request=15)
        for a, b in pieces:
            self.assertEqual(sum(1 for s, e in plan if s <= a and b <= e), 1)


if __name__ == "__main__":
    unittest.main()
