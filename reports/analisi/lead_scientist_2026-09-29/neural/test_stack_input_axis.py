"""Verify B preserves context-only inputs while leaving output support frozen."""
import ast
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

import stack_pilot as a
import stack_input_axis_pilot as b


class FakeModel:
    n_cells, n_genes, n_hidden, token_dim = 512, 503, 5, 2

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
        label = str(src.obs.gene.iloc[0])
        self.calls.append((label, src.n_obs, kw["random_seed"], kw["num_steps"], kw["prompt_ratio"],
                           np.asarray(src.X.sum(axis=0)).ravel(), np.asarray(dest.X.sum(axis=0)).ravel()))
        x = sp.csr_matrix(dest.X).copy()
        if label != a.CONTROL:
            weight = np.ones(x.shape[1])
            weight[int(label[-1])] = 2 + int(dest.X[:, 501].sum()) // 500
            x = x.multiply(weight).tocsr()
        return x, np.zeros(dest.n_obs)


class InputAxisTest(unittest.TestCase):
    def test_all_scientific_helpers_remain_identical(self):
        functions = lambda module: {node.name: ast.dump(node) for node in ast.parse(Path(module.__file__).read_text()).body
                                    if isinstance(node, ast.FunctionDef) and node.name != "infer"}
        self.assertEqual(functions(a), functions(b))
        self.assertEqual(a.sha(a.__file__), b.PREPARATION_ADAPTER_SHA)
        self.assertEqual(a.sha(Path(b.__file__).with_name("PROTOCOLLO_STACK_AB.md")), b.AB_PROTOCOL_SHA)

    def test_context_only_inputs_retained_and_output_outside_shared_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root / "bundle"; bundle.mkdir()
            common = [f"G{i:03d}" for i in range(500)]
            sg, dg = common + ["SOURCE_ONLY"], common + ["DEST_ONLY", "OUTSIDE_MODEL"]
            targets = ["T0", "T1"]
            with ad.settings.override(allow_write_nullable_strings=True):
                a.write_counts(bundle / "source_00.h5ad", sp.csr_matrix(np.ones((128, 501), dtype=np.float32)), sg, a.CONTROL)
                a.write_counts(bundle / "destination_controls.h5ad", sp.csr_matrix(np.ones((512, 502), dtype=np.float32)), dg, a.CONTROL)
                for i, target in enumerate(targets):
                    a.write_counts(bundle / f"source_{i+1:02d}.h5ad", sp.csr_matrix(np.full((64, 501), 2, dtype=np.float32)), sg, target)
            np.savez(bundle / "transfer.npz", targets=targets, genes=dg,
                     lfc=np.zeros((2, 502), dtype=np.float32), observed=np.ones((2, 502), dtype=bool))
            a.write_json(bundle / "bundle.json", {"targets": targets, "adapter_sha256": a.sha(a.__file__),
                                                  "files": {p.name: a.sha(p) for p in bundle.iterdir()}})
            checkpoint = root / "fake.ckpt"; checkpoint.write_bytes(b"fixture only")
            genelist = root / "genes.pkl"
            with genelist.open("wb") as stream:
                pickle.dump(common + ["SOURCE_ONLY", "DEST_ONLY", "MODEL_ONLY"], stream)
            args = SimpleNamespace(bundle=bundle, checkpoint=checkpoint, genelist=genelist, out=root / "A", device="cpu", batch_size=1)
            fake_torch, fake_stack, fake_loading = [ModuleType(x) for x in ("torch", "stack", "stack.model_loading")]
            fake_torch.device = lambda x: x
            models = []
            def load(*args, **kw):
                model = FakeModel(); models.append(model); return model
            fake_loading.load_model_from_checkpoint = load; fake_stack.model_loading = fake_loading
            modules = {"torch": fake_torch, "stack": fake_stack, "stack.model_loading": fake_loading}
            captured = [[], []]
            for index, module in enumerate([a, b]):
                args.out = root / ["A", "B"][index]
                original_sample = module.sample_counts
                def capture(profile, *args, **kw):
                    captured[index].append(np.asarray(profile).copy())
                    return original_sample(profile, *args, **kw)
                with patch.dict("sys.modules", modules), patch("importlib.metadata.version", return_value="fixture"), \
                     patch.object(module, "CHECKPOINT_SHA", a.sha(checkpoint)), patch.object(module, "GENELIST_SHA", a.sha(genelist)), \
                     patch.object(module, "N_OUTPUT", 3), patch.object(module, "sample_counts", side_effect=capture), \
                     ad.settings.override(allow_write_nullable_strings=True):
                    module.infer(args)
            self.assertEqual(len(models[0].calls), 3)  # one cached paired control + two targets
            self.assertEqual(len(models[1].calls), 3)
            for ca, cb in zip(models[0].calls, models[1].calls):
                self.assertEqual(ca[:5], cb[:5])
                np.testing.assert_array_equal(ca[5][:500], cb[5][:500])
                np.testing.assert_array_equal(ca[6][:500], cb[6][:500])
                np.testing.assert_array_equal(ca[5][500:], [0, 0, 0])
                np.testing.assert_array_equal(ca[6][500:], [0, 0, 0])
                self.assertGreater(cb[5][500], 0); self.assertGreater(cb[6][501], 0)
                np.testing.assert_array_equal(cb[5][501:], [0, 0])
                self.assertEqual(cb[6][500], 0); self.assertEqual(cb[6][502], 0)
            for q_a, q_b in zip(captured[0][::2], captured[1][::2]):
                np.testing.assert_array_equal(q_a, q_b)
            for q0, q1 in zip(captured[1][::2], captured[1][1::2]):
                np.testing.assert_array_equal(q0[-2:], q1[-2:])
                self.assertAlmostEqual(q0[:500].sum(), q1[:500].sum())
            transfer_a = ad.read_h5ad(root / "A" / "prediction_transfer.h5ad")
            transfer_b = ad.read_h5ad(root / "B" / "prediction_transfer.h5ad")
            self.assertEqual((transfer_a.X != transfer_b.X).nnz, 0)
            manifest = json.loads((root / "B" / "inference_manifest.json").read_text())
            self.assertEqual(manifest["adapter_sha256"], a.sha(b.__file__))
            self.assertEqual(manifest["preparation_adapter_sha256"], a.sha(a.__file__))
            self.assertEqual(manifest["input_axis_policy"], "own_measured_support")
            self.assertEqual(manifest["shared_genes"], 500)


if __name__ == "__main__":
    unittest.main()
