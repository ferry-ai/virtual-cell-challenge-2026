"""Small tests for independent target selection and exact reused controls."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

import stack_confirmation_pack as pack


class ConfirmationTest(unittest.TestCase):
    def test_selection_is_disjoint_and_rejects_insufficient_pool(self):
        targets = [*pack.EXPECTED, "DEV", "CONF", "PILOT", "SMALL"]
        counts = dict.fromkeys(targets, 64)
        counts["SMALL"] = 63
        actual = pack.select(targets, ["DEV"], ["CONF"], ["PILOT"], counts)
        self.assertEqual(actual, pack.EXPECTED)
        self.assertEqual(actual, pack.select(targets[::-1], ["DEV"], ["CONF"], ["PILOT"], counts))
        with self.assertRaisesRegex(ValueError, "twelve"):
            pack.select(pack.EXPECTED[:-1], [], [], [], counts)

    def test_prepare_reuses_control_bytes_and_preserves_unobserved_axis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, pilot = Path(tmp), pack.pilot
            bundle = root / "pilot"
            bundle.mkdir()
            genes = ["B", "A"]
            pilot.write_counts(bundle / "source_00.h5ad", sp.csr_matrix(np.tile([7, 3], (512, 1)), dtype=np.float32), genes, pilot.CONTROL)
            pilot.write_counts(bundle / "destination_controls.h5ad", sp.csr_matrix(np.tile([5, 6, 7], (2000, 1)), dtype=np.float32), ["A", "MISSING", "B"], pilot.CONTROL)
            pilot.write_json(bundle / "bundle.json", {"targets": ["PILOT"],
                "destination_size": 123456,
                "source_selected_rows": {pilot.CONTROL: list(range(512))}, "destination_control_rows": list(range(2000)),
                "files": {name: pilot.sha(bundle / name) for name in pack.REUSED}})
            source = root / "source.h5ad"
            labels = np.repeat(pack.EXPECTED, 64)
            counts = np.column_stack([np.arange(len(labels)) + 1, np.arange(len(labels)) % 9]).astype(np.float32)
            ad.AnnData(counts, obs=pd.DataFrame({"gene": pd.Categorical(labels)}, index=[str(i) for i in range(len(labels))]),
                       var=pd.DataFrame(index=genes)).write_h5ad(source)
            groups = root / "groups.csv"
            groups.write_text("gene,n_cells_obs,is_ntc\n" + "\n".join(f"{t},64,False" for t in pack.EXPECTED), encoding="utf-8")
            generator = root / "generator.json"
            pilot.write_json(generator, {"eligible": pack.EXPECTED + ["PILOT"], "development": ["PILOT"], "confirmation": []})
            registration = root / "registration.json"
            pilot.write_json(registration, {"confirmation_targets_original": pack.EXPECTED,
                "hashes": {"groups": pilot.sha(groups), "generator": pilot.sha(generator)}})
            effects = root / "effects.npz"
            observed = np.ones((12, 2), dtype=bool)
            observed[0, 0] = False
            np.savez(effects, targets=pack.EXPECTED, genes=genes, lfc=np.zeros((12, 2), dtype=np.float32), observed=observed)
            args = SimpleNamespace(source=source, source_groups=groups, generator_manifest=generator,
                registration=registration, pilot_bundle=bundle, effects=effects, out=root / "plan.json", plan=root / "plan.json")
            pack.plan(args)
            args.out = root / "confirmation"
            pack.prepare(args)
            for name in pack.REUSED:
                self.assertEqual(pilot.sha(args.out / name), pilot.sha(bundle / name))
            with np.load(args.out / "transfer.npz") as z:
                np.testing.assert_array_equal(z["observed"][0], [True, False, False])
                self.assertFalse(z["observed"][:, 1].any())
                np.testing.assert_array_equal(z["lfc"], np.zeros((12, 3)))
            for i, target in enumerate(pack.EXPECTED):
                actual = ad.read_h5ad(args.out / f"source_{i + 1:02d}.h5ad")
                np.testing.assert_array_equal(actual.X.toarray(), counts[labels == target])
            manifest = pack.load_json(args.out / "bundle.json")
            self.assertEqual(manifest["destination_truth_rows_read"], 0)
            self.assertEqual(manifest["destination_size"], 123456)
            self.assertFalse(manifest["inference_authorized"])
            with self.assertRaises(FileExistsError):
                pack.prepare(args)

    def test_modified_reused_control_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in pack.REUSED:
                (root / name).write_bytes(b"original")
            pack.pilot.write_json(root / "bundle.json", {"files": {n: pack.pilot.sha(root / n) for n in pack.REUSED}})
            (root / pack.REUSED[0]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "differs"):
                pack.verify_reused(root)


if __name__ == "__main__":
    unittest.main()
