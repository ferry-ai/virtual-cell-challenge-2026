"""adapters.h5csc_shards (gene-major h5ad, the scPerturb CSC files and KOLF) gives, cell for cell, the shards that
adapters.h5rows gives for the same data stored by rows: several passes, small column chunks, and a remote read.

    python -m unittest test_csc -v          (from this folder)
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
from test_range_reader import FakeRange  # noqa: E402

LABELS = dict(target_col="gene", control_values=["non-targeting"], library_col="batch")


def write(path, x):
    import anndata as ad
    import pandas as pd
    n = x.shape[0]
    obs = pd.DataFrame({"gene": pd.Categorical(np.where(np.arange(n) % 5 == 0, "non-targeting",
                                                        [f"G{i % 7}" for i in range(n)])),
                        "batch": pd.Categorical([f"b{i % 3}" for i in range(n)])}, index=[f"cell{i}" for i in range(n)])
    ad.AnnData(X=x, obs=obs, var=pd.DataFrame(index=[f"gene{j}" for j in range(x.shape[1])])).write_h5ad(path)


class Csc(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(3)
        x = sp.random(2300, 90, density=0.15, format="csr", random_state=rng, dtype=np.float32)
        x.data = np.ceil(x.data * 30).astype(np.float32)
        self.x = x
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        write(self.d / "rows.h5ad", x.tocsr())
        write(self.d / "cols.h5ad", x.tocsc())

    def tearDown(self):
        self.tmp.cleanup()

    def compare(self, csc_blocks):
        rows = list(adapters.h5rows(str(self.d / "rows.h5ad"), "s", "K", "10x", "CRISPRi", None, block=500, **LABELS))
        self.assertEqual([b[0] for b in rows], [b[0] for b in csc_blocks])
        for (_, x1, o1, v1, u1), (_, x2, o2, v2, u2) in zip(rows, csc_blocks):
            self.assertEqual(abs(x1 - x2).sum(), 0)
            for c in ("target", "control_kind", "library", "cell_key", "depth_native", "n_genes_detected"):
                self.assertEqual(o1[c].tolist(), o2[c].tolist(), c)
            self.assertEqual(u1["rows"], u2["rows"])
        got = sp.vstack([b[1] for b in csc_blocks]).tocsr()
        self.assertEqual(abs(got - self.x).sum(), 0)

    def test_local_file_in_several_passes_and_chunks(self):
        blocks = list(adapters.h5csc_shards(str(self.d / "cols.h5ad"), "s", "K", "10x", "CRISPRi", None,
                                            self.d / "work", block=500, cells_per_pass=1000, column_chunk=700,
                                            min_free_bytes=1 << 20, **LABELS))
        self.assertEqual(sorted({b[4]["read"]["pass"] for b in blocks}), [0, 1, 2])
        self.compare(blocks)
        self.assertFalse((self.d / "work").exists())                     # buckets removed after use

    def test_remote_file(self):
        FakeRange.blobs = {"https://fake.invalid/cols.h5ad": (self.d / "cols.h5ad").read_bytes()}
        original = inspect_remote.RangeFile
        inspect_remote.RangeFile = lambda url, block: FakeRange(url, block=4096, max_bytes=8 * 4096)
        try:
            blocks = list(adapters.h5csc_shards("https://fake.invalid/cols.h5ad", "s", "K", "10x", "CRISPRi", None,
                                                self.d / "work2", block=500, cells_per_pass=2300, column_chunk=5000,
                                                min_free_bytes=1 << 20, **LABELS))
        finally:
            inspect_remote.RangeFile = original
        self.compare(blocks)


if __name__ == "__main__":
    unittest.main()
