"""The compact twins (fastshard.py): every encoding path decodes to the source exactly.

Cases with known answers: empty rows and an empty block, counts above 65,535 (uint32 path), more than 65,535 features
(uint32 indices), rows stored unsorted in the source (sorted in the twin, same matrix), repeated or negative values
refused, read_rows in any order with repeats, and cellnet.read_csr / read_csr_rows giving the same model-gene matrix
from a shard and from its twin.

    python -m unittest test_fastshard -v          (from this folder, with the project venv; seconds)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402
import fastshard as FS  # noqa: E402
from fixtures import GENES, counts, write_shard  # noqa: E402


def decode(table, payloads, meta, tmp: Path, name="x.fcsr.npz"):
    import json
    np.savez(tmp / name, meta=np.array(json.dumps(meta)), blocks=table, **payloads)
    return FS.FastShard(tmp / name)


def random_csr(rng, n, f, density, top=50):
    x = sp.random(n, f, density=density, random_state=np.random.RandomState(int(rng.integers(1 << 31))), format="csr")
    x.data = np.ceil(x.data * top).astype(np.int64)
    return x


class Encoding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def roundtrip(self, x, block_rows=7, name="x.fcsr.npz"):
        table, payloads, facts = FS.encode_arrays(x.data, x.indices, x.indptr, x.shape[1], block_rows=block_rows)
        meta = {"format": FS.FORMAT, "version": FS.FORMAT_VERSION, "level": FS.LEVEL, "block_rows": block_rows,
                "shape": list(x.shape), **facts}
        t = decode(table, payloads, meta, self.d, name)
        d, i, p = t.read_all()
        y = sp.csr_matrix((d, i, p), shape=x.shape)
        self.assertEqual((y != x).nnz, 0)
        return t, facts

    def test_widths_and_empty_rows(self):
        rng = np.random.default_rng(0)
        x = random_csr(rng, 40, 30, 0.2).tolil()
        x[5, :] = 0
        x[14:21, :] = 0                         # an empty block (rows 14-20 with block_rows 7)
        x[3, 2] = 70000                         # a count above 65,535
        t, facts = self.roundtrip(x.tocsr())
        self.assertEqual(facts["max_count"], 70000)
        self.assertEqual(int(t.blocks[2, 2]), 0)
        wide = random_csr(rng, 10, 70000, 0.0005)                        # indices above 65,535
        self.roundtrip(wide, name="wide.fcsr.npz")

    def test_unsorted_rows_are_sorted(self):
        x = sp.csr_matrix(np.array([[0, 3, 0, 5], [7, 0, 1, 0]]))
        data, idx, ptr = np.array([5, 3, 1, 7]), np.array([3, 1, 2, 0]), np.array([0, 2, 4])
        table, payloads, facts = FS.encode_arrays(data, idx, ptr, 4, block_rows=8)
        self.assertFalse(facts["sorted_within_rows_in_source"])
        meta = {"format": FS.FORMAT, "version": FS.FORMAT_VERSION, "level": FS.LEVEL, "block_rows": 8,
                "shape": [2, 4], **facts}
        d, i, p = decode(table, payloads, meta, self.d).read_all()
        self.assertEqual((sp.csr_matrix((d, i, p), shape=(2, 4)) != x).nnz, 0)
        self.assertTrue(all(np.all(np.diff(i[p[r]:p[r + 1]]) > 0) for r in range(2)))

    def test_bad_values_refused(self):
        with self.assertRaises(ValueError):
            FS.encode_arrays(np.array([1.5]), np.array([0]), np.array([0, 1]), 3)
        with self.assertRaises(ValueError):
            FS.encode_arrays(np.array([-1]), np.array([0]), np.array([0, 1]), 3)
        with self.assertRaises(ValueError):
            FS.encode_arrays(np.array([1, 1]), np.array([2, 2]), np.array([0, 2]), 3)

    def test_read_rows(self):
        x = random_csr(np.random.default_rng(1), 50, 20, 0.3)
        t, _ = self.roundtrip(x, block_rows=8)
        rows = np.array([49, 0, 7, 8, 8, 23])
        d, i, p = t.read_rows(rows)
        self.assertEqual((sp.csr_matrix((d, i, p), shape=(rows.size, 20)) != x[rows]).nnz, 0)

    def test_shard_and_twin_read_alike(self):
        rng = np.random.default_rng(2)
        p = rng.dirichlet(np.ones(len(GENES)))
        x = counts(rng, p, 90)
        write_shard(self.d / "s.h5ad", x, "s", "K", "L1", ["NTC"] * 90, [f"b{i}-1" for i in range(90)], "file://s")
        rec = FS.encode(self.d / "s.h5ad", self.d / FS.twin_name("s.h5ad"), block_rows=16)
        self.assertTrue(rec["verified"])
        self.assertEqual(FS.check(self.d / "s.h5ad", self.d / FS.twin_name("s.h5ad"))["equal"], True)
        info = CN.index_shard(self.d / "s.h5ad")
        gene_of_axis = np.arange(len(GENES))
        gene_of_axis[3] = -1                                   # a feature off the model, dropped by both paths
        a, ma = CN.read_csr(self.d / "s.h5ad", info.official_index, info.measured, gene_of_axis, len(GENES))
        b, mb = CN.read_csr(self.d / FS.twin_name("s.h5ad"), info.official_index, info.measured, gene_of_axis, len(GENES))
        self.assertEqual((a != b).nnz, 0)
        np.testing.assert_array_equal(ma, mb)
        rows = np.array([5, 80, 5, 33])
        a, _ = CN.read_csr_rows(self.d / "s.h5ad", rows, info.official_index, info.measured, gene_of_axis, len(GENES))
        b, _ = CN.read_csr_rows(self.d / FS.twin_name("s.h5ad"), rows, info.official_index, info.measured,
                                gene_of_axis, len(GENES))
        self.assertEqual((a != b).nnz, 0)
        with self.assertRaises(FileExistsError):
            FS.encode(self.d / "s.h5ad", self.d / FS.twin_name("s.h5ad"))


if __name__ == "__main__":
    unittest.main()
