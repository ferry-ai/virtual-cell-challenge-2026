"""Small contract tests; no torch/Stack checkpoint, external data or network."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

import stack_pilot as pilot


class FakeStack:
    def __init__(self):
        self.calls = []

    def get_incontext_generation(self, **kw):
        self.calls.append(kw)
        src, dest = kw["base_adata_or_path"], kw["test_adata_or_path"]
        result = sp.csr_matrix(dest.X).copy()
        # Deliberately mutate passed objects, matching the API risk.
        dest.X = sp.csr_matrix(np.full(dest.shape, 777, dtype=np.float32))
        src.X = sp.csr_matrix(np.full(src.shape, 888, dtype=np.float32))
        return result, np.zeros(dest.n_obs)


class StackPilotTest(unittest.TestCase):
    def test_selection_is_fixed_and_cannot_fall_back(self):
        targets = [f"T{i}" for i in range(20)]
        counts = {t: 64 for t in targets}
        counts["T0"] = 63
        self.assertEqual(pilot.select_targets(targets, counts), pilot.select_targets(targets[::-1], counts))
        self.assertNotIn("T0", pilot.select_targets(targets, counts))
        with self.assertRaises(ValueError):
            pilot.select_targets(targets[:11], counts)

    def test_alignment_uses_measured_intersection_and_correct_order(self):
        x = sp.csr_matrix([[3, 4, 8], [1, 9, 2]], dtype=np.float32)
        actual = pilot.align_shared(x, ["C", "A", "B"], ["B", "D", "C", "A"], {"A", "C"})
        np.testing.assert_array_equal(actual.toarray(), [[0, 0, 3, 4], [0, 0, 1, 9]])
        with self.assertRaises(ValueError):
            pilot.align_shared(x, ["A", "A", "B"], ["A", "B"], {"A"})
        genes, cols = pilot.unique_first(["B", "A", "B", "C"])
        np.testing.assert_array_equal(genes, ["B", "A", "C"])
        np.testing.assert_array_equal(cols, [0, 1, 3])

    def test_paired_null_preserves_baseline_outside_shared_axis(self):
        basal, baseline = np.array([10., 20., 7.]), np.array([20., 10., 7.])
        synthetic = sp.csr_matrix([[1., 1., 500.]])
        out, info = pilot.corrected_profile(basal, baseline, ["A", "B", "C"], ["A", "B", "C"],
                                              {"A", "B"}, synthetic, synthetic)
        np.testing.assert_allclose(out, basal)
        self.assertTrue(info["baseline_mass_preserved_outside_shared"])
        self.assertEqual(info["shared_lfc_rms"], 0)
        pert = sp.csr_matrix([[4., 1., 0.]])
        changed, _ = pilot.corrected_profile(basal, baseline, ["A", "B", "C"], ["A", "B", "C"],
                                              {"A", "B"}, pert, synthetic)
        self.assertGreater(changed[0] / changed[1], basal[0] / basal[1])
        self.assertEqual(changed[2], baseline[2])
        self.assertAlmostEqual(changed.sum(), baseline.sum())

    def test_model_cannot_mutate_inputs_and_rejects_destination_truth(self):
        ctrl = ad.AnnData(sp.csr_matrix([[1, 2], [3, 4]], dtype=np.float32),
                          obs=pd.DataFrame({"gene": [pilot.CONTROL] * 2}, index=["a", "b"]))
        src = ctrl.copy()
        model = FakeStack()
        result = pilot.call_model(model, src, ctrl, Path("unused.pkl"), 1)
        np.testing.assert_array_equal(result.toarray(), ctrl.X.toarray())
        np.testing.assert_array_equal(src.X.toarray(), [[1, 2], [3, 4]])
        self.assertEqual(model.calls[0]["mode"], "mdm")
        ctrl.obs["gene"] = "REAL_PERTURBED_TRUTH"
        with self.assertRaises(ValueError):
            pilot.call_model(model, src, ctrl, Path("unused.pkl"), 1)

    def test_legacy_labels_and_selected_dense_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.h5ad"
            with h5py.File(path, "w") as f:
                obs = f.create_group("obs")
                obs.create_dataset("gene", data=np.array([0, 1, 0, 1], dtype=np.int16))
                cats = obs.create_group("__categories")
                cats.create_dataset("gene", data=np.asarray([pilot.CONTROL, "T"], dtype=object),
                                    dtype=h5py.string_dtype())
                f.create_dataset("X", data=np.array([[1, 2], [999, 999], [3, 4], [998, 998]], dtype=np.float32))
            rows = pilot.rows_for_labels(path, [pilot.CONTROL])[pilot.CONTROL]
            np.testing.assert_array_equal(rows, [0, 2])
            np.testing.assert_array_equal(pilot.read_rows(path, rows).toarray(), [[1, 2], [3, 4]])

    def test_fresh_400_counts_are_capped_without_pinned_group_total(self):
        counts = pilot.sample_counts(np.ones(9), np.full(400, 60), np.random.default_rng(123),
                                      max_stored_per_cell=4, max_counts_per_cell=45)
        pilot.validate_counts(counts)
        self.assertEqual(counts.shape, (400, 9))
        self.assertLessEqual(np.diff(counts.indptr).max(), 4)
        self.assertLessEqual(np.asarray(counts.sum(axis=1)).max(), 45)
        self.assertGreater(np.asarray(counts.sum(axis=1)).var(), 0)

    def test_preparation_reads_no_destination_perturbed_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = [f"T{i:02d}" for i in range(12)]
            source_labels = [pilot.CONTROL] * 512 + [t for t in targets for _ in range(64)]
            source = ad.AnnData(sp.csr_matrix(np.ones((len(source_labels), 2), dtype=np.float32)),
                                obs=pd.DataFrame({"gene": source_labels}), var=pd.DataFrame(index=["A", "B"]))
            source.write_h5ad(root / "source.h5ad")
            matrix = np.vstack([np.ones((512, 2)), np.full((3, 2), 99999)]).astype(np.float32)
            dest = ad.AnnData(sp.csr_matrix(matrix), obs=pd.DataFrame({"gene": [pilot.CONTROL] * 512 + ["TRUTH"] * 3}),
                              var=pd.DataFrame(index=["A", "B"]))
            dest.write_h5ad(root / "dest.h5ad")
            np.savez(root / "transfer.npz", targets=targets, genes=["A", "B"],
                     lfc=np.zeros((12, 2)), observed=np.ones((12, 2), bool))
            pilot.write_json(root / "plan.json", {"targets": targets, "seed": pilot.SEED,
                "protocol_sha256": pilot.sha(pilot.HERE / "PROTOCOLLO_STACK.md"),
                "adapter_sha256": pilot.sha(pilot.__file__)})
            pilot.prepare(SimpleNamespace(plan=root / "plan.json", source=root / "source.h5ad",
                destination=root / "dest.h5ad", effects=root / "transfer.npz", out=root / "bundle"))
            prepared = ad.read_h5ad(root / "bundle/destination_controls.h5ad")
            self.assertEqual(prepared.n_obs, 512)
            self.assertEqual(set(prepared.obs.gene), {pilot.CONTROL})
            self.assertEqual(prepared.X.max(), 1)
            self.assertEqual(len(list((root / "bundle").glob("source_*.h5ad"))), 13)
            bundle = json.loads((root / "bundle/bundle.json").read_text())
            self.assertEqual(len(bundle["destination_control_rows"]), 512)
            self.assertNotIn("destination_perturbed_rows", bundle)


if __name__ == "__main__":
    unittest.main()
