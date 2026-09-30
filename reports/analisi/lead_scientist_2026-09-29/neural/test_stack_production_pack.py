"""Synthetic source-shard, axis, provenance and fallback tests; no real data."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

import stack_production_pack as pack


class PackTest(unittest.TestCase):
    def fixture(self, root):
        source, controls, effects = [root / x for x in ("source", "controls", "effects")]
        for path in (source, controls, effects):
            path.mkdir()
        labels = [pack.pilot.CONTROL] * 530 + ["T1"] * 130 + ["T2"] * 65 + ["T3"] * 63
        rows = np.arange(len(labels))
        x = np.column_stack([rows + 1, rows % 11, np.full(len(rows), 999)])
        # Intentionally non-monotone shard source IDs, duplicate measured gene.
        for i, positions in enumerate((rows[1::2][::-1], rows[::2])):
            obs = pd.DataFrame({"gene": pd.Categorical(np.array(labels)[positions]), "source_row": positions},
                               index=[str(x) for x in positions])
            ad.AnnData(sp.csr_matrix(x[positions], dtype=np.float32), obs=obs,
                       var=pd.DataFrame(index=["B", "A", "B"])).write_h5ad(source / f"cells_part{i:03d}.h5ad")
        pack.pilot.write_json(source / "report.json", {"source": "synthetic", "raw_counts": True})
        axis, targets = ["A", "MISSING", "B"], ["T3", "T2", "T1", "T4"]
        (controls / "gene_names.csv").write_text("gene_name\n" + "\n".join(axis), encoding="utf-8")
        (controls / "pert_counts.csv").write_text("target_gene\n" + "\n".join(targets), encoding="utf-8")
        for context in pack.CONTEXTS:
            pack.pilot.write_counts(controls / f"context_{context}.h5ad",
                sp.csr_matrix(np.tile([3, 2, 1], (520, 1)), dtype=np.float32), axis, pack.pilot.CONTROL)
            observed = np.ones((4, 3), dtype=bool)
            observed[0, 1] = False
            np.savez(effects / f"effects_{context}.npz", targets=targets, genes=axis,
                     lfc=np.zeros((4, 3), dtype=np.float32), observed=observed)
        pack.pilot.write_json(effects / "manifest.json", {"recipe": "synthetic_t25"})
        pack.pilot.write_json(root / "registration.json", {
            "production_targets_subset_ge64": ["T1", "T2"], "production_fallback_targets": ["T3", "T4"],
            "counts_per_panel_target": {"T1": 130, "T2": 65, "T3": 63, "T4": 0}})
        return SimpleNamespace(source=source, controls=controls, effects=effects,
                               registration=root / "registration.json", out=root / "plan.json", plan=root / "plan.json"), x

    def test_roundtrip_preserves_counts_ids_first_axis_and_explicit_masks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args, original = self.fixture(root)
            pack.plan(args)
            plan = json.loads(args.out.read_text())
            self.assertEqual(plan["targets"], ["T1", "T2"])
            self.assertEqual(plan["fallback_targets"], ["T3", "T4"])
            self.assertEqual(plan["source_observed_on_official"], [True, False, True])
            self.assertEqual(len(plan["source_cells"]["T1"]["source_rows"]), 128)
            args.out = root / "bundle"
            pack.prepare(args)
            bundle = json.loads((args.out / "bundle.json").read_text())
            for target, filename in bundle["source_files"].items():
                actual = ad.read_h5ad(args.out / filename)
                self.assertEqual(list(actual.var_names), ["B", "A"])
                ids = plan["source_cells"][target]["source_rows"]
                np.testing.assert_array_equal(actual.X.toarray(), original[ids, :2])
                self.assertEqual(bundle["source_row_ids"][target], ids)
            with np.load(args.out / "fallback_t25_A.npz") as z:
                self.assertTrue(z["observed"][0, 0])
                self.assertFalse(z["observed"][0, 1])
                self.assertEqual(z["lfc"][0, 0], z["lfc"][0, 1])
            self.assertEqual(pack.pilot.sha(args.controls / "context_A.h5ad"),
                             pack.pilot.sha(args.out / "full_controls_A.h5ad"))
            self.assertEqual(ad.read_h5ad(args.out / "model_controls_A.h5ad").n_obs, 512)
            with self.assertRaises(FileExistsError):
                pack.prepare(args)

    def test_selection_ignores_shard_order_and_refuses_repeated_ids(self):
        ids = np.arange(1000)
        np.testing.assert_array_equal(pack.pick(ids, 128, "T"), pack.pick(ids[::-1], 128, "T"))
        self.assertEqual(len(pack.pick(ids[:64], 128, "T")), 64)
        with self.assertRaises(ValueError):
            pack.pick([2, 2], 1, "T")

    def test_changed_lineage_fails_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, _ = self.fixture(Path(tmp))
            pack.plan(args)
            (args.source / "report.json").write_text("{}", encoding="utf-8")
            args.out = Path(tmp) / "bundle"
            with self.assertRaisesRegex(ValueError, "lineage"):
                pack.prepare(args)
            self.assertFalse(args.out.exists())

    def test_non_boolean_mask_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, _ = self.fixture(Path(tmp))
            path = args.effects / "effects_A.npz"
            with np.load(path) as z:
                contents = {name: z[name] for name in z.files}
            contents["observed"] = contents["observed"].astype(float)
            np.savez(path, **contents)
            with self.assertRaisesRegex(ValueError, "boolean observed"):
                pack.plan(args)


if __name__ == "__main__":
    unittest.main()
