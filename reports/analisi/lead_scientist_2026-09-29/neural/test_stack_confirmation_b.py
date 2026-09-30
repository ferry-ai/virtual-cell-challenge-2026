"""Prospective B exporter parity and unchanged scorer mathematics, no model."""
import ast
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

import stack_pilot as a
import stack_input_axis_pilot as b
import stack_confirmation_b_infer as infer
import stack_confirmation_score as score_a
import stack_confirmation_b_score as score_b
import derive_stack_confirmation_b_bundle as derive
from stack_confirmation_pack import EXPECTED
from test_stack_ab_selection_guard import receipt


class FakeModel:
    n_cells, n_genes, n_hidden, token_dim = 512, 503, 5, 2

    def __init__(self):
        self.calls = []

    def to(self, device):
        return self

    def eval(self):
        return self

    def parameters(self):
        return []

    def get_incontext_generation(self, **kw):
        src, dest = kw["base_adata_or_path"], kw["test_adata_or_path"]
        label = str(src.obs.gene.iloc[0])
        self.calls.append((label, src.n_obs, kw["random_seed"], kw["num_steps"], kw["prompt_ratio"],
            hashlib.sha256(src.X.data.tobytes()).hexdigest(), hashlib.sha256(dest.X.data.tobytes()).hexdigest()))
        assert src.X[:, 500].sum() > 0 and dest.X[:, 501].sum() > 0
        assert src.X[:, 501:].nnz == 0 and dest.X[:, 500].nnz == 0
        x = dest.X.copy()
        if label != a.CONTROL:
            weight = np.ones(x.shape[1])
            weight[EXPECTED.index(label)] = 2 + int(dest.X[:, 501].sum()) // 500
            x = x.multiply(weight).tocsr()
        return x, np.zeros(dest.n_obs)


class ConfirmationBTests(unittest.TestCase):
    def test_all_scorer_numerical_functions_and_generation_loops_unchanged(self):
        def nodes(module):
            return ast.parse(Path(module.__file__).read_text()).body
        def functions(module):
            return {n.name: ast.dump(n) for n in nodes(module)
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name != "run"}
        self.assertEqual(functions(score_a), functions(score_b))
        def loops(module):
            run = next(n for n in nodes(module) if isinstance(n, ast.FunctionDef) and n.name == "run")
            return [ast.dump(n) for n in run.body if isinstance(n, ast.For)]
        self.assertEqual(loops(score_a), loops(score_b))

    def test_manifest_rebind_only_after_selected_b_and_preserves_data_hashes(self):
        s, _, blobs, _ = receipt(.01, .02)
        old = {"targets": EXPECTED, "inference_adapter_sha256": derive.A_INFER,
            "scoring_code_sha256": derive.A_SCORE, "protocol_sha256": derive.A_PROTOCOL,
            "status": "prepared_no_model_no_scores", "files": {"transfer.npz": "unchanged"},
            "adapter_sha256": a.sha(a.__file__), "source_selected_rows": {"one": [1, 3, 5]}}
        params = dict(source_sha="old", selector_sha=s["selector_sha256"], adapter_sha="new_adapter",
                      scorer_sha="new_scorer", protocol_sha="new_protocol")
        result = derive.rebind(old, json.dumps(s).encode(), blobs, **params)
        self.assertEqual(result["files"], old["files"])
        self.assertEqual(result["source_selected_rows"], old["source_selected_rows"])
        self.assertEqual(result["adapter_sha256"], old["adapter_sha256"])
        s2, _, blobs2, _ = receipt(.02, .01)
        with self.assertRaisesRegex(ValueError, "not the unique"):
            derive.rebind(old, json.dumps(s2).encode(), blobs2, **params)

    def test_exact_export_matches_b_pilot_profiles_and_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root / "bundle"; bundle.mkdir()
            common = [f"G{i:03d}" for i in range(500)]
            sg, dg = common + ["SOURCE_ONLY"], common + ["DEST_ONLY", "OUTSIDE_MODEL"]
            with ad.settings.override(allow_write_nullable_strings=True):
                a.write_counts(bundle / "source_00.h5ad", sp.csr_matrix(np.ones((512, 501)), dtype=np.float32), sg, a.CONTROL)
                a.write_counts(bundle / "destination_controls.h5ad", sp.csr_matrix(np.ones((2000, 502)), dtype=np.float32), dg, a.CONTROL)
                for i, target in enumerate(EXPECTED):
                    a.write_counts(bundle / f"source_{i+1:02d}.h5ad", sp.csr_matrix(np.full((64+i%2, 501), 2), dtype=np.float32), sg, target)
            lfc = np.zeros((12, 502), dtype=np.float32); lfc[:, 500] = .3; lfc[:, 10] = -.2
            observed = np.ones_like(lfc, dtype=bool); observed[:, 501] = False
            np.savez(bundle / "transfer.npz", targets=EXPECTED, genes=dg, lfc=lfc, observed=observed)
            protocol = root / "fixture_protocol.txt"; protocol.write_text("Synthetic test only; not a final registered protocol")
            s, _, blobs, _ = receipt(.01, .02)
            selection_bytes = json.dumps(s).encode()
            manifest = {"targets": EXPECTED, "adapter_sha256": a.sha(a.__file__),
                "inference_adapter_sha256": a.sha(infer.__file__), "protocol_sha256": a.sha(protocol),
                "ab_protocol_sha256": b.AB_PROTOCOL_SHA, "selected_variant": "B",
                "ab_selector_sha256": s["selector_sha256"], "ab_selection_json": selection_bytes.decode(),
                "ab_selection_sha256": hashlib.sha256(selection_bytes).hexdigest(),
                "ab_comparison_json": {v: value.decode() for v, value in blobs.items()},
                "files": {p.name: a.sha(p) for p in bundle.iterdir()}}
            a.write_json(bundle / "bundle.json", manifest)
            checkpoint = root / "fake.ckpt"; checkpoint.write_bytes(b"fixture only")
            genelist = root / "genes.pkl"
            with genelist.open("wb") as stream:
                pickle.dump(common + ["SOURCE_ONLY", "DEST_ONLY", "MODEL_ONLY"], stream)
            args = SimpleNamespace(bundle=bundle, checkpoint=checkpoint, genelist=genelist, out=root / "pilot_b", device="cpu", batch_size=1)
            torch, stack, loading = [ModuleType(x) for x in ("torch", "stack", "stack.model_loading")]
            torch.device = lambda x: x
            models = []
            def load(*args, **kwargs):
                model = FakeModel(); models.append(model); return model
            loading.load_model_from_checkpoint = load; stack.model_loading = loading
            modules = {"torch": torch, "stack": stack, "stack.model_loading": loading}
            captured = []; sample = b.sample_counts
            def capture(profile, *args, **kwargs):
                captured.append(np.asarray(profile, dtype=np.float64).copy())
                return sample(profile, *args, **kwargs)
            with patch.dict("sys.modules", modules), patch("importlib.metadata.version", return_value="fixture"), \
                 patch.object(b, "CHECKPOINT_SHA", a.sha(checkpoint)), patch.object(b, "GENELIST_SHA", a.sha(genelist)), \
                 patch.object(infer, "CHECKPOINT_SHA", a.sha(checkpoint)), patch.object(infer, "GENELIST_SHA", a.sha(genelist)), \
                 patch.object(infer, "B_PROTOCOL_PATH", protocol), patch.object(b, "N_OUTPUT", 3), \
                 patch.object(b, "sample_counts", side_effect=capture), ad.settings.override(allow_write_nullable_strings=True):
                b.infer(args)
                args.out = root / "confirmation_b"
                infer.infer(args)
            self.assertEqual(models[0].calls, models[1].calls)
            self.assertEqual(len(models[0].calls), 14)
            with np.load(args.out / "profiles.npz", allow_pickle=False) as result:
                self.assertEqual(result["stack"].dtype, np.float64)
                np.testing.assert_array_equal(result["transfer"], np.stack(captured[::2]))
                np.testing.assert_array_equal(result["stack"], np.stack(captured[1::2]))
                np.testing.assert_array_equal(result["stack"][:, 500:], result["transfer"][:, 500:])
                self.assertEqual(int(result["shared"].sum()), 500)
            self.assertFalse((args.out / "prediction_stack.h5ad").exists())
            provenance = json.loads((args.out / "inference_manifest.json").read_text())
            self.assertEqual(provenance["input_axis_policy"], "own_measured_support")
            self.assertEqual(provenance["ab_selection_sha256"], manifest["ab_selection_sha256"])


if __name__ == "__main__":
    unittest.main()
