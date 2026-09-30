import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import anndata as ad
import numpy as np

import stack_pilot as pilot
import stack_profiles_to_cells as cells


class ProfileCellsTest(unittest.TestCase):
    def fixture(self, root):
        path = root / "A"; path.mkdir()
        genes, targets = ["X", "Y", "Z"], ["T1", "T2"]
        libs = np.array([70., 100., 200.])
        np.savez(path / "axis.npz", genes=genes, targets=targets, shared=[True, True, False], library_sizes=libs)
        rows = []
        for i, target in enumerate(targets):
            q0 = np.array([.2, .3, .5]); q1 = q0.copy() if i else np.array([.4, .1, .5])
            name = f"profile_{i:03d}.npz"
            np.savez(path / name, target=target, transfer=q0, stack=q1)
            rows.append({"file": name, "sha256": pilot.sha(path / name), "target": target, "fallback": bool(i)})
        pilot.write_json(path / "complete.json", {"status": "profiles_only_no_cells_no_scores", "baseline": "t25_unscaled",
            "context": "A", "model_seed": pilot.SEED, "axis_sha256": pilot.sha(path / "axis.npz"), "profiles": rows})
        return path, genes, targets, libs

    def test_draw_is_bit_identical_to_frozen_pilot_and_streamed_axis(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(pilot, "N_OUTPUT", 3):
            root = Path(tmp); path, genes, targets, libs = self.fixture(root)
            q = np.array([.4, .1, .5])
            rng = pilot.rng_for("output:T1")
            expected = pilot.sample_counts(q, rng.choice(libs, 3, replace=True), rng,
                max_stored_per_cell=12000, max_counts_per_cell=1000000)
            self.assertEqual((cells.draw(q, libs, "T1") != expected).nnz, 0)
            result = cells.generate({"A": path}, genes, targets, root / "out")
            self.assertEqual(result["n_cells"], 6)
            actual = ad.read_h5ad(root / "out" / "prediction.h5ad")
            self.assertEqual(list(actual.var_names), genes)
            self.assertEqual(list(actual.obs.target_gene.astype(str)), ["T1"] * 3 + ["T2"] * 3)
            self.assertEqual(set(actual.obs.context.astype(str)), {"A"})
            self.assertEqual((actual.X[:3] != expected).nnz, 0)
            self.assertEqual(result["prediction_sha256"], pilot.sha(root / "out" / "prediction.h5ad"))
            self.assertFalse((root / "out" / "prediction.partial.h5ad").exists())

    def test_invalid_hash_or_axis_refuses_before_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, genes, targets, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "context"):
                cells.generate({"B": path}, genes, targets, root / "out")
            self.assertFalse((root / "out").exists())
            with self.assertRaisesRegex(ValueError, "axes"):
                cells.generate({"A": path}, list(reversed(genes)), targets, root / "out")
            self.assertFalse((root / "out").exists())
            with (path / "profile_000.npz").open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(ValueError, "hash/path"):
                cells.generate({"A": path}, genes, targets, root / "out")
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
