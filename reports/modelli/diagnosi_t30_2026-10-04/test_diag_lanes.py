"""Tests of the effect arithmetic of diag_lanes.py on synthetic arrays (no cube, no scorer).

    .\\scripts\\py.cmd -m unittest reports/modelli/diagnosi_t30_2026-10-04/test_diag_lanes.py
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diag_lanes as D  # noqa: E402


def synthetic(seed=0, n=40, g=300):
    rng = np.random.default_rng(seed)
    T_all = rng.normal(0, 0.1, (n, g)).astype(np.float32)
    T_prod = (T_all + rng.normal(0, 0.05, (n, g))).astype(np.float32)
    T_all[:, :10] = np.nan                      # genes the anchor does not define
    T_prod[3] = np.nan                          # a target the recipe's sources do not have
    R = (rng.normal(0, 0.03, (n, g)) + rng.normal(0, 0.02, (1, g))).astype(np.float32)
    R[5, 20:40] = np.nan
    w = rng.uniform(0.1, 0.5, n)
    return T_all, T_prod, R, w


class EffectArms(unittest.TestCase):
    def setUp(self):
        self.T_all, self.T_prod, self.R, self.w = synthetic()
        self.eff, self.diag = D.build_effects(self.T_all, self.T_prod, self.R, self.w, 0.65)

    def test_parity_arm_is_the_baseline_bit_for_bit(self):
        self.assertTrue(np.array_equal(self.eff["all_w0"], self.T_all.astype(np.float64), equal_nan=True))

    def test_bench_case_is_the_hybrid_of_the_original_lane(self):
        self.assertTrue(np.array_equal(self.eff["all_wR"], D.HL.hybrid(self.T_all, self.R, self.w), equal_nan=True))

    def test_specific_plus_common_is_the_whole_correction_where_the_anchor_is_defined(self):
        ok = np.isfinite(self.T_all)
        whole = self.eff["all_wR"] - self.T_all
        parts = (self.eff["all_wRspec"] - self.T_all) + (self.eff["all_wRcom"] - self.T_all)
        np.testing.assert_allclose(parts[ok], whole[ok], atol=2e-7)

    def test_specific_part_has_no_common_component_and_dose_reaches_the_requested_share(self):
        spec, com = D.split_common(self.R, np.isfinite(self.T_all))
        self.assertLess(D.common_share(spec), 1e-10)
        self.assertAlmostEqual(self.diag["common_share_dose"], 0.65, places=4)
        self.assertGreater(self.diag["dose_factor"], 0)

    def test_arms_keep_the_support_of_their_baseline(self):
        for name, lfc in self.eff.items():
            base = self.T_all if name.startswith("all") else self.T_prod
            self.assertTrue(np.array_equal(np.isfinite(lfc), np.isfinite(base)), name)
        self.assertEqual(self.diag["targets_without_T_prod"], 1)

    def test_x15_scales_the_whole_effect(self):
        ok = np.isfinite(self.T_prod)
        np.testing.assert_allclose(self.eff["prod_wR_x15"][ok], 1.5 * self.eff["prod_wR"][ok], rtol=1e-12)

    def test_a_correction_without_common_component_has_no_dose_arm(self):
        spec, com = D.split_common(self.R, np.isfinite(self.T_all))
        with self.assertRaises(SystemExit):
            D.dose_factor(spec, np.zeros_like(com), 0.65)


class NoisePlan(unittest.TestCase):
    def test_every_arm_gets_every_seed_at_both_cell_counts_and_seed_zero_is_the_bench(self):
        plan = D.noise_plan(20260912, 5, 400)
        self.assertEqual(len(plan), 4 * 5 * 2)
        self.assertEqual(len({p[0] for p in plan}), len(plan))
        self.assertIn(("all_wR@nbs0", "all_wR", 20260912, None), plan)
        self.assertIn(("prod@n400s4", "prod", 20260916, 400), plan)
        for arm in D.NOISE_ARMS:
            self.assertEqual(sorted(p[2] for p in plan if p[1] == arm and p[3] is None),
                             [20260912 + k for k in range(5)])


class FaithfulArm(unittest.TestCase):
    """Protocol §8: the correction computed by the export procedure on a line's own control cells."""

    def test_controls_from_a_matrix_equal_the_exporter_reading_the_same_cells_from_a_file(self):
        import tempfile

        import h5py
        import scipy.sparse as sp
        import export_abc as EX
        rng = np.random.default_rng(1)
        var = [f"g{i}" for i in (7, 0, 3, 99, 5, 2)]              # one gene off the model, another order
        model_genes = [f"g{i}" for i in range(9)]
        input_genes = np.array([0, 2, 5, 8], np.int64)             # g8 is not in the file
        x = sp.random(11, len(var), density=0.6, random_state=2, format="csr", dtype=np.float32)
        x.data = np.round(x.data * 40 + 1).astype(np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controls.h5ad"
            with h5py.File(path, "w") as f:
                g = f.create_group("X")
                g.create_dataset("data", data=x.data)
                g.create_dataset("indices", data=x.indices)
                g.create_dataset("indptr", data=x.indptr)
                g.attrs["shape"] = np.array(x.shape)
                v = f.create_group("var")
                v.attrs["_index"] = "_index"
                v.create_dataset("_index", data=np.array(var, dtype="S"))
            ref = EX.read_controls(path, model_genes, input_genes)
        got = D.controls_from_matrix(x, var, model_genes, input_genes)
        self.assertEqual(set(ref), set(got))
        for k in ref:
            if isinstance(ref[k], np.ndarray):
                self.assertTrue(np.array_equal(ref[k], got[k]), k)
            else:
                self.assertEqual(ref[k], got[k], k)
        self.assertEqual(got["var_off_model"], 1)
        self.assertEqual(got["input_genes_absent"], 1)

    def test_anchors_sit_on_every_cube_gene_of_the_model_axis_and_missing_values_are_zero(self):
        T = np.array([[0.5, np.nan, -0.25], [np.nan, np.nan, np.nan], [1.0, 2.0, 3.0]], np.float32)
        anc = D.anchors_on_model(T, ["b", "x", "d"], ["a", "b", "c", "d"], np.array([3, 0, 2]), 9,
                                 {"S0", "S1"}, ["S0", "S1", "S2"])
        np.testing.assert_array_equal(anc["anchor"][0], np.array([0, 0.5, 0, -0.25], np.float16))
        np.testing.assert_array_equal(anc["anchor"][1], np.zeros(4, np.float16))
        self.assertEqual(anc["anchor"].dtype, np.float16)
        np.testing.assert_allclose(anc["info"][:, 0], [3 / 9, 0, 2 / 9], rtol=1e-6)
        self.assertEqual(anc["eligible"].tolist(), [True, False, False])   # no anchor; symbol unknown to the network

    def test_faithful_arms_change_only_the_correction(self):
        T_all, T_prod, R, w = synthetic()
        R_exp = (R * 1.5 + 0.03).astype(np.float32)
        eff, diag = D.faithful_arms(T_all, T_prod, R, R_exp, w)
        self.assertTrue(np.array_equal(eff["all_wRexp"], D.HL.hybrid(T_all, R_exp, w), equal_nan=True))
        self.assertTrue(np.array_equal(eff["prod_wRexp"], D.HL.hybrid(T_prod, R_exp, w), equal_nan=True))
        self.assertTrue(np.array_equal(np.isfinite(eff["all_wRexpspec"]), np.isfinite(T_all)))
        self.assertGreater(diag["common_share_R_exp"], diag["common_share_R"])
        self.assertGreater(diag["cos_mean_R_exp_vs_R"], 0.5)


DATA = Path(os.environ.get("VCC2026_DATA_ROOT", "C:/Users/ferra/vcc2026-data"))
EXPORTED = DATA / "processed/ibrido_selettivo_2026-10-04/export_abc_r2/correction_A.npz"
MANIFEST = Path(__file__).resolve().parents[2] / "invii/trial_2026-10-04/t30_effects_manifest.json"


@unittest.skipUnless(EXPORTED.exists() and os.environ.get("VCC_SLOW_TESTS"),
                     "needs the t30 export on disk and VCC_SLOW_TESTS=1 (about three minutes)")
class FaithfulArmReproducesTheExport(unittest.TestCase):
    def test_context_A_controls_through_the_faithful_arm_give_back_the_stored_correction(self):
        import json
        from types import SimpleNamespace

        import h5py
        import scipy.sparse as sp
        import export_abc as EX
        argv = json.loads(MANIFEST.read_text(encoding="utf-8"))["argv"]
        args = SimpleNamespace(**{argv[i].lstrip("-").replace("-", "_"): Path(argv[i + 1])
                                  for i in range(1, len(argv), 2)})
        import torch
        ck = torch.load(args.model, map_location="cpu", weights_only=False)
        model_genes = [str(g) for g in ck["genes"]]
        with np.load(args.effects / "effects_A.npz", allow_pickle=False) as z:
            targets, official = [str(t) for t in z["targets"]], [str(g) for g in z["genes"]]
        anc = EX.panel_anchors(args, model_genes, targets)
        pick = np.flatnonzero(anc["eligible"])[:6]
        with h5py.File(args.controls / "context_A.h5ad", "r") as f:
            X = f["X"]
            x = sp.csr_matrix((X["data"][:], X["indices"][:], X["indptr"][:]),
                              shape=tuple(int(v) for v in X.attrs["shape"]))
            var = [str(v) for v in EX.CN.h5_column(f["var"], f["var"].attrs.get("_index", "_index"))]
        R_exp, how = D.export_style_R(args.model, x, var, [targets[i] for i in pick], anc["T_cube"][pick],
                                      [str(g) for g in anc["cube"].genes], anc["support"][pick], anc["max_sources"],
                                      log=lambda m: None)
        with np.load(EXPORTED, allow_pickle=False) as z:
            stored = z["R"][pick].astype(np.float32)
        col = {g: i for i, g in enumerate(official)}
        idx = np.array([col[g] for g in var])
        ref = stored[:, idx]
        self.assertEqual(how["targets_computed"], len(pick))
        self.assertTrue(np.array_equal(np.isfinite(R_exp), np.isfinite(ref)))
        ok = np.isfinite(ref)
        self.assertLessEqual(float(np.abs(R_exp[ok].astype(np.float16).astype(np.float32) - ref[ok]).max()), 2.0 ** -10)


if __name__ == "__main__":
    unittest.main()
