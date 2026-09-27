"""Synthetic CSC integration tests; every count read uses local_fetcher."""

import importlib.util
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

import h5py
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from vcc2026.remote_csr import local_fetcher

SPEC = importlib.util.spec_from_file_location(
    "kolf_sums", REPO / "reports/universo_kolf_2026-09-27/kolf_sums.py")
kolf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kolf)


class KolfSumsTests(unittest.TestCase):
    def setUp(self):
        output = redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        # All temporary data stays inside this working copy.
        self.tmp = tempfile.TemporaryDirectory(dir=REPO)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "counts.h5ad"
        self.url = "https://synthetic.invalid/immutable.h5ad"
        self.axis = ["D", "absent", "A", "C", "B", "zero"]
        self.genes = ["A", "B", "C", "D", "extra", "zero"]
        rng = np.random.default_rng(27)
        self.dense = rng.poisson(1.2, (24, 6)).astype(np.float32)
        self.dense[:, -1] = 0
        self.targets = np.array([0, 1, 2, 0, 1, 2] * 4, dtype=np.int8)
        self.channels = np.array([0, 8, 1, 9, 1, 8] * 4, dtype=np.int8)
        self.totals = self.dense.sum(axis=1)
        with h5py.File(self.path, "w") as f:
            obs = f.create_group("obs")
            for name, cats, codes in (
                ("gene_target", ["NTC", "T1", "T2"], self.targets),
                ("channel", [f"channel-{i}" for i in range(10)], self.channels),
                ("batch", ["b0", "b1", "b2"], np.arange(24) % 3),
                ("perturbed", np.array([False, True]), (self.targets != 0).astype(int)),
            ):
                group = obs.create_group(name)
                if isinstance(cats, list):
                    group.create_dataset("categories", data=cats, dtype=h5py.string_dtype())
                else:
                    group.create_dataset("categories", data=cats)
                group.create_dataset("codes", data=codes)
            obs.create_dataset("total_counts", data=self.totals)
            f.create_dataset("var/_index", data=self.genes, dtype=h5py.string_dtype())
            g = f.create_group("layers/counts")
            g.attrs["encoding-type"] = "csc_matrix"
            g.attrs["shape"] = self.dense.shape
            data, indices, ptr = [], [], [0]
            for column in self.dense.T:
                nz = np.flatnonzero(column)
                data.extend(column[nz])
                indices.extend(nz)
                ptr.append(len(data))
            g.create_dataset("data", data=np.array(data, dtype=np.float32), chunks=(7,))
            g.create_dataset("indices", data=np.array(indices, dtype=np.int64), chunks=(5,))
            g.create_dataset("indptr", data=np.array(ptr, dtype=np.int64))
            # Accessing X would give a very different result.
            f.create_dataset("X", data=self.dense * 123)
        self.fetch = local_fetcher(self.path)
        self.network = patch.object(kolf, "http_fetcher", side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.remote = patch.object(kolf, "HTTPRangeReader", side_effect=AssertionError("network forbidden"))
        self.remote.start()
        self.addCleanup(self.remote.stop)

    def obs(self, name):
        directory = self.root / name
        kolf.prepare_obs(self.url, directory, self.axis, local_path=self.path)
        return directory

    def reference(self, directory):
        with np.load(directory / "groups.npz") as z:
            self.assertEqual(z["group_of_cell"].dtype, np.dtype("int32"))
            self.assertEqual(z["total_counts"].dtype, np.dtype("float64"))
            np.testing.assert_array_equal(z["missing_genes"], ["absent"])
            result = np.full((len(z["target"]), len(self.axis)), np.nan, dtype=np.float32)
            for i, (target, pool) in enumerate(zip(z["target"], z["pool"])):
                target_code = ["NTC", "T1", "T2"].index(target)
                mask = (self.targets == target_code) & (self.channels % 8 == pool)
                self.assertEqual(z["n_cells"][i], mask.sum())
                self.assertEqual(z["total_counts"][i], self.totals[mask].sum(dtype=np.float64))
                np.testing.assert_array_equal(z["group_of_cell"][mask], i)
                for j, symbol in enumerate(self.axis):
                    if symbol in self.genes:
                        result[i, j] = self.dense[mask, self.genes.index(symbol)].sum()
            return result

    def build(self, name, blocks, max_nnz=kolf.MAX_NNZ):
        directory = self.obs(name)
        for i in range(blocks):
            self.assertTrue(kolf.run_block(self.url, directory / "groups.npz", i, blocks,
                                           directory, fetch=self.fetch, max_nnz=max_nnz))
        dest = directory / "sums.npz"
        kolf.merge(directory, dest)
        with np.load(dest) as z:
            self.assertEqual(z["sums"].dtype, np.dtype("float32"))
            np.testing.assert_array_equal(z["genes"], self.axis)
            result = z["sums"]
        np.testing.assert_array_equal(result, self.reference(directory))
        return result

    def test_dense_reference_and_two_block_splits(self):
        np.testing.assert_array_equal(self.build("one", 1), self.build("three", 3))

    def test_bounded_batches_and_split_single_column(self):
        self.build("tiny_batches", 3, max_nnz=4)

    def test_empty_blocks_are_valid(self):
        self.build("empty_blocks", 7)

    def test_missing_block_fails(self):
        directory = self.obs("missing")
        kolf.run_block(self.url, directory / "groups.npz", 0, 3, directory, fetch=self.fetch)
        with self.assertRaisesRegex(ValueError, "missing"):
            kolf.merge(directory, directory / "sums.npz")
        self.assertFalse((directory / "sums.npz").exists())

    def test_resume_skips_without_fetch(self):
        directory = self.obs("resume")
        kolf.run_block(self.url, directory / "groups.npz", 0, 1, directory, fetch=self.fetch)
        path = directory / "block_0_of_1.npz"
        before = path.read_bytes(), path.stat().st_mtime_ns
        def forbidden(a, b):
            self.fail("resumed block must not fetch")
        self.assertFalse(kolf.run_block(self.url, directory / "groups.npz", 0, 1,
                                        directory, fetch=forbidden))
        self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))

    def test_failed_fetch_does_not_publish(self):
        directory = self.obs("failed")
        def broken(a, b):
            raise RuntimeError("injected interruption")
        with self.assertRaisesRegex(RuntimeError, "interruption"):
            kolf.run_block(self.url, directory / "groups.npz", 0, 1, directory, fetch=broken)
        self.assertFalse((directory / "block_0_of_1.npz").exists())
        self.assertTrue(kolf.run_block(self.url, directory / "groups.npz", 0, 1,
                                       directory, fetch=self.fetch))

    def test_mixed_splits_and_wrong_group_identity_fail(self):
        directory = self.obs("mixed")
        for blocks in (1, 2):
            kolf.run_block(self.url, directory / "groups.npz", 0, blocks, directory, fetch=self.fetch)
        with self.assertRaises(ValueError):
            kolf.merge(directory, directory / "sums.npz")
        # A different groups archive must not silently reuse a completed block.
        groups = kolf._load(directory / "groups.npz")
        groups["total_counts"] += 1
        other = directory / "other.npz"
        np.savez(other, **groups)
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            kolf.run_block(self.url, other, 0, 1, directory, fetch=self.fetch)


if __name__ == "__main__":
    unittest.main()
