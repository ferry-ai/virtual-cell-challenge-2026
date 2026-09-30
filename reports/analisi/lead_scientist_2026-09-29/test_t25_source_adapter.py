"""Synthetic-only production parity and neural-operator adapter checks."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import numpy as np
import pandas as pd
import torch

import t25_source_adapter as A
from neural_sources import SourceAttention
from vcc2026.multisource import AxisTable, mix


def fixture():
    rng = np.random.default_rng(29)
    genes = np.array(["T0", "near", "g2", "g3", "g4", "unmeasured"])
    targets = ["T0", "T1", "T2"]
    tables = {}
    for name in A.TOKENS:
        x = rng.normal(0, .3, (3, 6)).astype(np.float32)
        x[:, -1] = np.nan
        x[1, 3] = 0  # a measured zero must never become an absent measurement
        if name == "cd4_Rest":
            x[2, 2] = np.nan
        tables[name] = AxisTable(name, targets, x, x, np.ones_like(x), rng.integers(30, 500, 3))
    cd4, weight = mix([tables[n] for n in A.CD4], targets, gamma=0.)
    cd4 = np.where(weight > 0, cd4, np.nan).astype(np.float32)
    cells = sum(tables[n].n_cells for n in A.CD4)
    tables["cd4_mix"] = AxisTable("cd4_mix", targets, cd4, cd4, np.ones_like(cd4), cells, {"from": list(A.CD4)})
    spec = {"amplitude": 1.576, "weights": {n: 1. for n in A.SOURCES}}
    effect, weight = mix([tables[n] for n in A.SOURCES], targets, weights=spec["weights"], gamma=1., reliability_scale=100.)
    effect *= spec["amplitude"]
    effect[0, 1] -= .5  # fixed cis head, outside the amplitude
    observed = weight > 0
    observed[0, 1] = True
    effect[:, -1] = -0.  # preserve bit identity, including signed zero
    reference = {"targets": np.asarray(targets), "genes": genes, "lfc": effect.astype(np.float32), "observed": observed}
    factors = {"tokens": np.asarray(A.TOKENS), "targets": np.asarray(targets), "genes": genes,
               "ratio": np.ones((6, 3, 6), np.float32), "gate": np.ones((6, 3, 6), np.float32)}
    coordinates = pd.DataFrame({"symbol": ["T0", "near", "g2", "T1", "T2"],
                                "chrom": ["1", "1", "1", "2", "3"], "tss": [10000, 14999, 30000, 40000, 40000]}).set_index("symbol")
    return tables, spec, reference, factors, coordinates


class AdapterTests(unittest.TestCase):
    def test_neutral_network_preserves_t25_arrays_bit_for_bit(self):
        tables, spec, ref, factors, coords = fixture()
        output, report = A.adapt(ref, factors, A.ProductionContributions(tables), spec, coords)
        for k in ref:
            self.assertEqual(ref[k].tobytes(), output[k].tobytes(), k)
        self.assertEqual(sum(r["changed_pairs"] for r in report), 0)

    def test_six_tokens_exactly_reconstruct_four_source_recipe(self):
        tables, spec, ref, _, _ = fixture()
        expected, _ = mix([tables[n] for n in A.SOURCES], ref["targets"], gamma=1., weights=spec["weights"])
        pc = A.ProductionContributions(tables)
        for i, target in enumerate(ref["targets"]):
            _, _, actual, observed = pc.contributions(target, spec["weights"])
            np.testing.assert_allclose(actual, expected[i], atol=1e-15)
            self.assertTrue(observed[3])

    def test_gate_applies_after_gamma_and_before_amplitude_preserves_cis(self):
        tables, spec, ref, factors, coords = fixture()
        factors["gate"][0, :, :] = 1.2
        pc = A.ProductionContributions(tables)
        output, _ = A.adapt(ref, factors, pc, spec, coords)
        for i, t in enumerate(ref["targets"]):
            values, w, old, _ = pc.contributions(t, spec["weights"])
            g = np.ones_like(values)
            g[0] = 1.2
            new = np.divide((w * g * values).sum(0), w.sum(0), out=np.zeros(6), where=w.sum(0) > 0)
            expected = ref["lfc"][i].astype(float) + .5 * spec["amplitude"] * (new - old)
            protected = A.protected_mask(t, ref["genes"], coords)
            check = ~protected & ref["observed"][i]
            np.testing.assert_allclose(output["lfc"][i, check], expected[check], atol=2e-8)
            np.testing.assert_array_equal(output["lfc"][i, protected], ref["lfc"][i, protected])
        np.testing.assert_array_equal(output["observed"], ref["observed"])

    def test_cd4_state_reweighting_changes_state_mix_without_new_common(self):
        tables, spec, ref, factors, coords = fixture()
        factors["ratio"][A.TOKENS.index("cd4_Stim48hr")] = 3
        output, _ = A.adapt(ref, factors, A.ProductionContributions(tables), spec, coords)
        self.assertGreater(np.linalg.norm(output["lfc"] - ref["lfc"]), 0)
        self.assertEqual(output["lfc"][0, 1], ref["lfc"][0, 1])

    def test_labeled_axes_realign_and_do_not_trust_shape_only(self):
        tables, spec, ref, factors, coords = fixture()
        factors["ratio"][0, 1, 2] = 2
        pc = A.ProductionContributions(tables)
        a, _ = A.adapt(ref, factors, pc, spec, coords)
        shuffled = dict(factors)
        shuffled["genes"] = factors["genes"][::-1]
        shuffled["tokens"] = factors["tokens"][::-1]
        shuffled["targets"] = factors["targets"][::-1]
        for k in ("ratio", "gate"):
            shuffled[k] = factors[k][::-1, ::-1, ::-1]
        b, _ = A.adapt(ref, shuffled, pc, spec, coords)
        np.testing.assert_array_equal(a["lfc"], b["lfc"])
        shuffled["genes"] = np.array(["WRONG", *shuffled["genes"][1:]])
        with self.assertRaises(ValueError):
            A.adapt(ref, shuffled, pc, spec, coords)

    def test_wrong_baseline_cache_or_unbounded_modifiers_are_refused(self):
        tables, spec, ref, factors, coords = fixture()
        wrong = dict(ref, lfc=ref["lfc"].copy())
        wrong["lfc"][1, 2] += .001
        with self.assertRaisesRegex(ValueError, "reconstruction"):
            A.adapt(wrong, factors, A.ProductionContributions(tables), spec, coords)
        tables["cd4_mix"].shrunk[1, 2] += .01
        with self.assertRaisesRegex(ValueError, "decomposition|reconstruction"):
            A.adapt(ref, factors, A.ProductionContributions(tables), spec, coords)
        with self.assertRaisesRegex(ValueError, "bounds"):
            A.relative_delta(np.ones((6, 4)), np.ones((6, 4)), np.full((6, 4), 10), np.ones((6, 4)))

    def test_neural_modifier_identity_and_fallback_is_never_direct_source(self):
        model = SourceAttention(4)
        batch = {"value": torch.ones(2, 6, 8), "features": torch.zeros(2, 6, 8, 20),
                 "priors": torch.zeros(2, 4), "mask": torch.ones(2, 6, 8, dtype=torch.bool)}
        r, h = A.token_modifiers(model, batch)
        self.assertTrue(torch.equal(r, torch.ones_like(r)))
        self.assertTrue(torch.equal(h, torch.ones_like(h)))
        with torch.no_grad():
            model.token[-1].bias[:] = torch.tensor([1., 1.])
        batch["features"][:, 0, :, 17] = 1
        batch["mask"][:, 1] = False
        r, h = A.token_modifiers(model, batch)
        self.assertTrue(torch.equal(r[:, :2], torch.ones_like(r[:, :2])))
        self.assertTrue(torch.equal(h[:, :2], torch.ones_like(h[:, :2])))
        self.assertTrue((r[:, 2:] > 1).all())

    def test_cli_apply_roundtrip_and_original_sha_verification(self):
        tables, spec, ref, factors, coords = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache, reference, factor_dir = tmp / "cache", tmp / "reference", tmp / "factors"
            for directory in (cache, reference, factor_dir):
                directory.mkdir()
            for name, table in tables.items():
                np.savez_compressed(cache / f"{name}.npz", targets=np.asarray(table.targets), shrunk=table.shrunk,
                                    n_cells=table.n_cells, meta=json.dumps(table.meta))
            coords_path = tmp / "coords.tsv"
            coords.reset_index().to_csv(coords_path, sep="\t", index=False)
            recipe = {"name": "t25", "effect": "shrunk", "gamma": 1., "reliability_scale": 100,
                      "contexts": {c: spec for c in "ABC"}, "cis": {"max_distance_bp": 5000, "scale": 2.}}
            recipe_path = tmp / "recipe.json"
            recipe_path.write_text(json.dumps(recipe))
            ref_manifest = {"recipe": recipe, "cis": {"coords_sha256": A.digest(coords_path)}, "contexts": {}}
            factor_manifest = {"contexts": {}, "candidate": "t25_relative_source_delta"}
            for c in "ABC":
                np.savez_compressed(reference / f"effects_{c}.npz", **ref)
                np.savez_compressed(factor_dir / f"factors_{c}.npz", **factors)
                ref_manifest["contexts"][c] = {"sha256": A.digest(reference / f"effects_{c}.npz")}
                factor_manifest["contexts"][c] = {"sha256": A.digest(factor_dir / f"factors_{c}.npz")}
            (reference / "manifest.json").write_text(json.dumps(ref_manifest))
            (factor_dir / "manifest.json").write_text(json.dumps(factor_manifest))
            args = SimpleNamespace(out=tmp / "out", recipe=recipe_path, reference=reference, factors=factor_dir,
                                   cache=cache, coords=coords_path)
            A.apply(args)
            with np.load(args.out / "effects_A.npz", allow_pickle=False) as z:
                self.assertEqual(z["lfc"].tobytes(), ref["lfc"].tobytes())
                self.assertEqual(z["genes"].dtype.kind, "U")
            report = json.loads((args.out / "manifest.json").read_text())
            self.assertTrue(all(c["arrays_identical"] for c in report["contexts"].values()))
            ref_manifest["contexts"]["A"]["sha256"] = "bad"
            (reference / "manifest.json").write_text(json.dumps(ref_manifest))
            args.out = tmp / "refused"
            with self.assertRaisesRegex(ValueError, "reference hash"):
                A.apply(args)


if __name__ == "__main__":
    torch.set_num_threads(2)
    unittest.main()
