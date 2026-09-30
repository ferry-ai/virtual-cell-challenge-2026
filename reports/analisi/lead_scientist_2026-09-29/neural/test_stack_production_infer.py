"""Synthetic integration: profile correction, cardinality cache and exact fallback."""
from pathlib import Path
import json
import tempfile
import unittest

import anndata as ad
import numpy as np
import scipy.sparse as sp
import stack_production_infer as prod


class ProductionTests(unittest.TestCase):
    def gate(self):
        return ({"status": "complete", "passes_confirmation": True,
                 "protocol_sha256": prod.CONFIRM_PROTOCOL_SHA, "delta_projection": .01,
                 "per_seed_delta": [.01, .011, .009], "mean_pds_raw_delta": 0.,
                 "paired_target_bootstrap_ci95": [.001, .019], "bootstrap_complete_fraction": 1.},
                {"production_inference_authorized": True, "bundle_sha256": "bundle",
                 "adapter_sha256": "adapter", "baseline": "t25_unscaled",
                 "regime_extension_acknowledged": True, "contexts": ["A", "B", "C"]})

    def test_two_distinct_gates_required(self):
        confirmation, decision = self.gate()
        prod.check_gate(confirmation, decision, "bundle", "adapter")
        for key, bad in [("passes_confirmation", False), ("delta_projection", .0049),
                         ("per_seed_delta", [.03, -.001, .01]),
                         ("mean_pds_raw_delta", -.0001),
                         ("paired_target_bootstrap_ci95", [0., .02])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                prod.check_gate(confirmation | {key: bad}, decision, "bundle", "adapter")
        with self.assertRaises(ValueError):
            prod.check_gate(confirmation, decision | {"production_inference_authorized": False}, "bundle", "adapter")

    def test_context_export_matches_frozen_formula_and_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            genes = [f"G{i:03d}" for i in range(600)]
            source_genes = genes[:530]
            controls = sp.csr_matrix(np.tile(np.arange(600) % 7 + 1, (520, 1)), dtype=np.float32)
            prod.pilot.write_counts(root / "full_controls_A.h5ad", controls, genes, prod.pilot.CONTROL)
            prod.pilot.write_counts(root / "model_controls_A.h5ad", controls[:512], genes, prod.pilot.CONTROL)
            prod.pilot.write_counts(root / "source_000.h5ad", sp.csr_matrix(np.ones((512, 530))), source_genes, prod.pilot.CONTROL)
            files = {prod.pilot.CONTROL: "source_000.h5ad"}
            for i, target in enumerate(["T1", "T2"], 1):
                x = np.ones((64, 530))
                x[:, i] = 6
                files[target] = f"source_{i:03d}.h5ad"
                prod.pilot.write_counts(root / files[target], sp.csr_matrix(x), source_genes, target)
            lfc = np.zeros((3, 600), dtype=np.float32)
            lfc[:, 0] = [.4, -.2, .1]
            np.savez(root / "fallback_t25_A.npz", targets=["T2", "T1", "T3"], genes=genes,
                     lfc=lfc, observed=np.ones_like(lfc, dtype=bool))
            bundle = {"official_targets": ["T3", "T1", "T2"], "targets": ["T1", "T2"],
                      "fallback_targets": ["T3"], "source_files": files}
            calls = []
            outputs = {}
            def fake(model, source, ctrl, genelist, batch_size):
                target = source.obs.gene.astype(str).iloc[0]
                self.assertEqual(source.n_obs, 64)
                self.assertEqual(ctrl.shape, (512, 600))
                self.assertEqual(ctrl.X[:, 530:].nnz, 0)
                calls.append(target)
                x = np.tile(np.asarray(source.X.sum(0)).ravel(), (512, 1))
                x += 1
                outputs[target] = sp.csr_matrix(x)
                return outputs[target]
            out = root / "out"
            prod.context_profiles(None, root, bundle, "A", genes, root / "unused.pkl", out=out, model_call=fake)
            self.assertEqual(calls, [prod.pilot.CONTROL, "T1", "T2"])
            receipt = json.loads((out / "complete.json").read_text())
            self.assertEqual(receipt["model_calls"], 3)
            basal = np.asarray(controls.sum(0), dtype=np.float64).ravel()
            for j, target in enumerate(bundle["official_targets"]):
                i = ["T2", "T1", "T3"].index(target)
                expected, _ = prod.pilot.predicted_profile(basal, lfc[i] / np.log(2.), np.ones(600, dtype=bool))
                with np.load(out / f"profile_{j:03d}.npz", allow_pickle=False) as z:
                    self.assertEqual(z["stack"].dtype, np.float64)
                    np.testing.assert_array_equal(z["transfer"], expected)
                    if target == "T3":
                        np.testing.assert_array_equal(z["stack"], expected)
                    else:
                        corrected, _ = prod.pilot.corrected_profile(basal, expected, genes, genes,
                            set(source_genes), outputs[target], outputs[prod.pilot.CONTROL])
                        np.testing.assert_array_equal(z["stack"], corrected)
                    np.testing.assert_array_equal(z["stack"][530:], expected[530:])
            with self.assertRaises(FileExistsError):
                prod.context_profiles(None, root, bundle, "A", genes, root / "unused.pkl", out=out, model_call=fake)

    def test_no_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                prod.inside(Path(tmp), "../other")

    def test_control_reduction_is_bit_exact_even_with_float32_rounding(self):
        control = sp.csr_matrix(np.array([[16777216, 1, 3], [1, 5, 2], [4, 7, 9]], dtype=np.float32))
        perturb = control.copy()
        perturb.data *= np.float32(1.25)
        expected = np.asarray(control.sum(0), dtype=np.float64)
        reduced = prod.control_summary(control)
        np.testing.assert_array_equal(reduced.toarray(), expected)
        args = (np.array([2., 3., 5.]), np.array([.2, .3, .5]), ["A", "B", "C"], ["A", "B", "C"], {"A", "B", "C"}, perturb)
        full, full_info = prod.pilot.corrected_profile(*args, control)
        small, small_info = prod.pilot.corrected_profile(*args, reduced)
        np.testing.assert_array_equal(full, small)
        self.assertEqual(full_info, small_info)


if __name__ == "__main__":
    unittest.main()
