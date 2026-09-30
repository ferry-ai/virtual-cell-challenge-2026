"""Run frozen pilot and new exporter with the same fake model; compare exact q."""
import hashlib
import json
from pathlib import Path
import pickle
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import anndata as ad
import numpy as np
import scipy.sparse as sp

import stack_pilot as pilot
import stack_confirmation_infer as confirm
from stack_confirmation_pack import EXPECTED


class FakeModel:
    n_cells, n_genes, n_hidden, token_dim = 512, 601, 5, 2

    def __init__(self):
        self.calls = []

    def to(self, _):
        return self

    def eval(self):
        return self

    def parameters(self):
        return []

    def get_incontext_generation(self, **kw):
        src, dest = kw["base_adata_or_path"], kw["test_adata_or_path"]
        target = str(src.obs.gene.iloc[0])
        self.calls.append((target, src.n_obs, kw["random_seed"], kw["num_steps"], kw["prompt_ratio"],
                           hashlib.sha256(sp.csr_matrix(src.X).data.tobytes()).hexdigest(),
                           hashlib.sha256(sp.csr_matrix(dest.X).data.tobytes()).hexdigest()))
        x = sp.csr_matrix(dest.X).copy()
        if target != pilot.CONTROL:
            weights = np.ones(x.shape[1])
            weights[EXPECTED.index(target)] = 2
            x = x.multiply(weights).tocsr()
        return x, np.zeros(dest.n_obs)


class ProfileParityTest(unittest.TestCase):
    def test_exact_export_matches_frozen_pilot_before_sampling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            bundle.mkdir()
            genes = [f"G{i:03d}" for i in range(600)]
            destination_genes = genes + ["OUTSIDE_1", "OUTSIDE_2"]
            pilot.write_counts(bundle / "source_00.h5ad", sp.csr_matrix(np.tile(np.arange(600) % 3 + 1, (512, 1)), dtype=np.float32), genes, pilot.CONTROL)
            pilot.write_counts(bundle / "destination_controls.h5ad", sp.csr_matrix(np.tile(np.arange(602) % 4 + 1, (2000, 1)), dtype=np.float32), destination_genes, pilot.CONTROL)
            for i, target in enumerate(EXPECTED):
                pilot.write_counts(bundle / f"source_{i + 1:02d}.h5ad", sp.csr_matrix(np.ones((64 + i % 2, 600)), dtype=np.float32), genes, target)
            lfc = np.zeros((12, 602), dtype=np.float32)
            lfc[:, 600] = .3
            lfc[:, 10] = -.2
            observed = np.ones_like(lfc, dtype=bool)
            observed[:, 601] = False
            np.savez(bundle / "transfer.npz", targets=EXPECTED, genes=destination_genes, lfc=lfc, observed=observed)
            manifest = {"targets": EXPECTED, "adapter_sha256": pilot.sha(pilot.__file__),
                "inference_adapter_sha256": pilot.sha(confirm.__file__), "protocol_sha256": confirm.PROTOCOL_SHA,
                "files": {p.name: pilot.sha(p) for p in bundle.iterdir()}}
            pilot.write_json(bundle / "bundle.json", manifest)
            checkpoint, genelist = root / "fake.ckpt", root / "genes.pkl"
            checkpoint.write_bytes(b"fake checkpoint, no torch")
            with genelist.open("wb") as stream:
                pickle.dump(genes + ["MODEL_ONLY"], stream)
            args = SimpleNamespace(bundle=bundle, checkpoint=checkpoint, genelist=genelist,
                                   out=root / "old", device="cpu", batch_size=1)
            fake_torch, fake_stack, fake_loading = [ModuleType(x) for x in ("torch", "stack", "stack.model_loading")]
            fake_torch.device = lambda x: x
            models = []
            def load(*a, **kw):
                obj = FakeModel(); models.append(obj); return obj
            fake_loading.load_model_from_checkpoint = load
            fake_stack.model_loading = fake_loading
            captured = []
            original_sample = pilot.sample_counts
            def capture(profile, *a, **kw):
                captured.append(np.asarray(profile, dtype=np.float64).copy())
                return original_sample(profile, *a, **kw)
            modules = {"torch": fake_torch, "stack": fake_stack, "stack.model_loading": fake_loading}
            with patch.dict("sys.modules", modules), patch("importlib.metadata.version", return_value="fixture"), \
                 patch.object(pilot, "CHECKPOINT_SHA", pilot.sha(checkpoint)), patch.object(pilot, "GENELIST_SHA", pilot.sha(genelist)), \
                 patch.object(confirm, "CHECKPOINT_SHA", pilot.sha(checkpoint)), patch.object(confirm, "GENELIST_SHA", pilot.sha(genelist)), \
                 patch.object(pilot, "N_OUTPUT", 3), patch.object(pilot, "sample_counts", side_effect=capture):
                with ad.settings.override(allow_write_nullable_strings=True):
                    pilot.infer(args)
                args.out = root / "new"
                confirm.infer(args)
            self.assertEqual(models[0].calls, models[1].calls)
            self.assertEqual(len(captured), 24)
            with np.load(args.out / "profiles.npz", allow_pickle=False) as exported:
                self.assertEqual(exported["stack"].dtype, np.float64)
                np.testing.assert_array_equal(exported["transfer"], np.stack(captured[::2]))
                np.testing.assert_array_equal(exported["stack"], np.stack(captured[1::2]))
                np.testing.assert_array_equal(exported["stack"][:, -2:], exported["transfer"][:, -2:])
                self.assertEqual(list(exported["targets"]), EXPECTED)
                self.assertEqual(int(exported["shared"].sum()), 600)
            self.assertFalse((args.out / "prediction_stack.h5ad").exists())
            finished = json.loads((args.out / "finished.json").read_text())
            self.assertEqual(finished["profile_sha256"], pilot.sha(args.out / "profiles.npz"))
            self.assertEqual(finished["final_poisson_seeds"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
