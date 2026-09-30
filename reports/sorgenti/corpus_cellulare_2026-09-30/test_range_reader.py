"""The HTTP range reader keeps a bounded cache and returns the same cells as a local read (30/09, after jobs 100/105).

A fake RangeFile serves the bytes of a small h5ad written here; `adapters.h5rows` reads it as if it were remote. Each
case checks that the blocks yielded equal the local file's rows exactly and that the cache never holds more than its
limit, while the whole matrix passes through it.

    python -m unittest test_range_reader -v          (from this folder, with the project venv)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adapters  # noqa: E402
import inspect_remote  # noqa: E402

URL = "https://fake.invalid/cells.h5ad"


class FakeRange(inspect_remote.RangeFile):
    blobs: dict = {}
    peak = 0

    def _resolve(self):
        self.final_url, self.size, self.etag = self.url, len(self.blobs[self.url]), "v1"

    def _get(self, lo, hi):
        return self.blobs[self.url][lo:hi + 1], "v1"

    def _blk(self, i):
        data = super()._blk(i)
        FakeRange.peak = max(FakeRange.peak, len(self.cache))
        return data


def write_h5ad(path, x, dense):
    import anndata as ad
    import pandas as pd
    n, g = x.shape
    labels = np.where(np.arange(n) % 7 == 0, "non-targeting", np.array([f"G{i % 13}" for i in range(n)]))
    obs = pd.DataFrame({"gene": pd.Categorical(labels), "batch": pd.Categorical([f"b{i % 3}" for i in range(n)])},
                       index=[f"cell{i}" for i in range(n)])
    var = pd.DataFrame(index=[f"gene{j}" for j in range(g)])
    ad.AnnData(X=x.toarray() if dense else x, obs=obs, var=var).write_h5ad(path)


class RangeReader(unittest.TestCase):
    def run_case(self, dense):
        rng = np.random.default_rng(1 if dense else 2)
        x = sp.random(3000, 200, density=0.2, format="csr", random_state=rng, dtype=np.float32)
        x.data = np.ceil(x.data * 20).astype(np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cells.h5ad"
            write_h5ad(path, x, dense)
            FakeRange.blobs = {URL: path.read_bytes()}
            FakeRange.peak = 0
            original = inspect_remote.RangeFile
            inspect_remote.RangeFile = lambda url, block: FakeRange(url, block=4096, max_bytes=4 * 4096)
            try:
                blocks = list(adapters.h5rows(URL, "s", "ctx", "chem", "CRISPRi", None, block=400,
                                              target_col="gene", control_values=["non-targeting"],
                                              library_col="batch"))
            finally:
                inspect_remote.RangeFile = original
        got = sp.vstack([b[1] for b in blocks]).tocsr()
        self.assertEqual(got.shape, x.shape)
        self.assertEqual(abs(got - x).sum(), 0)
        self.assertLessEqual(FakeRange.peak, 4)
        self.assertGreater(len(FakeRange.blobs[URL]), 4 * 4096 * 4)      # the file is much larger than the cache
        obs = blocks[0][2]
        self.assertEqual(obs["target"].iloc[0], "NTC")
        self.assertEqual(obs["library"].iloc[1], "b1")

    def test_csr_matrix_streams_through_a_bounded_cache(self):
        self.run_case(dense=False)

    def test_dense_matrix_streams_through_a_bounded_cache(self):
        self.run_case(dense=True)


if __name__ == "__main__":
    unittest.main()
