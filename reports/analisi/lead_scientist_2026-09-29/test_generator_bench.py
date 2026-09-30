"""Small, synthetic checks of the new bench's scientific invariants."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("generator_bench_tested", HERE / "generator_bench.py")
bench = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bench
spec.loader.exec_module(bench)


class ReaderTests(unittest.TestCase):
    def test_prepare_writes_pickle_free_gene_axis(self):
        import anndata as ad
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            truth = root / "truth.h5ad"
            genes = np.array(["T1", "T2", "G1", "G2"], dtype=object)
            labels = ["T1"] * 4 + ["T2"] * 4 + ["non-targeting"] * 5
            matrix = ad.AnnData(np.ones((13, 4), dtype=np.float32),
                                obs=pd.DataFrame({"gene": labels}, index=[f"c{i}" for i in range(13)]),
                                var=pd.DataFrame(index=genes))
            matrix.write_h5ad(truth)
            effects = root / "effects.npz"
            np.savez(effects, targets=np.array(["T1", "T2"]), genes=genes.astype(str),
                     lfc=np.zeros((2, 4), np.float32), observed=np.ones((2, 4), bool))
            panel = root / "targets.txt"
            panel.write_text("T1\nT2\n", encoding="utf-8")
            bulk = root / "bulk.h5ad"
            bulk.write_bytes(b"Unused because effects carry an explicit observed mask")
            args = SimpleNamespace(out=root / "prepared", hepg2=truth, targets_file=panel,
                                   effects=effects, k562_bulk=bulk, selection_seed=20260929,
                                   control_seed=2026, n_development=1, n_confirmation=1,
                                   control_cells=3, truth="full", data_root=root)
            bench.prepare(args)
            with np.load(args.out / "prepared_effects.npz", allow_pickle=False) as archive:
                for key in archive.files:
                    self.assertNotEqual(archive[key].dtype.kind, "O")
                np.testing.assert_array_equal(archive["genes"], genes)

    def test_dense_and_csr_selected_rows_preserve_axis_and_counts(self):
        matrix = np.arange(60, dtype=np.float32).reshape(10, 6)
        matrix[matrix % 3 == 0] = 0
        rows, cols = np.array([1, 3, 8]), np.array([0, 3, 5])
        with tempfile.TemporaryDirectory() as tmp:
            dense, sparse = (Path(tmp) / name for name in ["dense.h5ad", "sparse.h5ad"])
            with h5py.File(dense, "w") as handle:
                handle.create_dataset("X", data=matrix)
            csr = sp.csr_matrix(matrix)
            with h5py.File(sparse, "w") as handle:
                group = handle.create_group("X")
                group.attrs["shape"] = csr.shape
                group.attrs["encoding-type"] = "csr_matrix"
                for name in ["data", "indices", "indptr"]:
                    group.create_dataset(name, data=getattr(csr, name))
            for path in [dense, sparse]:
                result = bench.read_selected_rows(path, rows, cols, block_rows=2)
                np.testing.assert_array_equal(result.toarray(), matrix[rows][:, cols])
            with self.assertRaises(ValueError):
                bench.read_selected_rows(dense, np.array([3, 1]), cols)

    def test_observed_zero_is_not_missing_and_missing_axis_is_masked(self):
        values, observed = bench.map_effects(np.array(["A", "B", "C"]),
                                             np.array([[0, 2, 3]], dtype=np.float32),
                                             np.array([[True, True, False]]), np.array(["B", "D", "A", "C"]))
        np.testing.assert_array_equal(values, [[2, 0, 0, 3]])
        np.testing.assert_array_equal(observed, [[True, False, True, False]])

    def test_target_partition_is_disjoint_stable_and_ignores_outcomes(self):
        panel = [f"T{i}" for i in range(20)]
        counts = {t: 10 for t in panel}
        a = bench.select_targets(panel, panel, counts, 20260929, 4, 8)
        b = bench.select_targets(panel[::-1], panel, counts, 20260929, 4, 8)
        self.assertEqual(a, b)
        self.assertFalse(set(a[1]) & set(a[2]))
        self.assertEqual((len(a[1]), len(a[2])), (4, 8))

    def test_source_mask_keeps_source_zero_and_applies_control_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bulk.h5ad"
            with h5py.File(path, "w") as handle:
                handle.create_dataset("X", data=np.array([[10, 20, 5, 0], [10, 20, 5, 0]], np.float32))
                obs = handle.create_group("obs")
                obs.create_dataset("gene_transcript", data=np.array([b"non-targeting", b"0_T_P1_x"]))
                obs.create_dataset("num_cells_filtered", data=np.array([1000, 200]))
                var = handle.create_group("var")
                var.attrs["_index"] = "_index"
                var.create_dataset("_index", data=np.array([b"e1", b"e2", b"e3", b"e4"]))
                var.create_dataset("gene_name", data=np.array([b"A", b"B", b"C", b"ZERO"]))
            mask, _ = bench.source_mask(path, ["T"], np.array(["A", "B", "C", "ZERO", "ABSENT"]))
            np.testing.assert_array_equal(mask, [[True, True, True, False, False]])


class GeneratorTests(unittest.TestCase):
    def test_matches_stage45_sequence_for_poisson_and_scaled_phi(self):
        from vcc2026.inference import predicted_profile
        from vcc2026.sampling import resample_library_sizes, sample_counts
        basal = np.array([30., 50., 100., 10., 9.])
        lfc = np.array([0, 0.25, -0.4, 4.8, 8], dtype=np.float32)
        observed = np.array([True, True, True, True, False])
        libraries = np.array([100, 200, 400])
        phi = np.array([0, 0.3, 1, 0.1, 0.2])
        challenge = bench.config.challenge()
        for phi_scale in [0, 0.25, 1]:
            stream = bench.target_rng(11, "TARGET")
            profile, _ = predicted_profile(basal, 1.5 * lfc / np.log(2.0), observed)
            libs = resample_library_sizes(libraries, 23, stream)
            expected = sample_counts(profile, libs, stream,
                                     max_stored_per_cell=challenge.max_stored_per_cell,
                                     max_counts_per_cell=challenge.max_counts_per_cell,
                                     overdispersion=None if phi_scale == 0 else phi * phi_scale)
            actual, _ = bench.generate_block(basal, lfc, observed, libraries, 23,
                                              1.5, phi_scale, phi, 11, "TARGET")
            self.assertEqual((expected != actual).nnz, 0)

    def test_target_seed_is_order_independent_and_distinct(self):
        a = bench.target_rng(1, "A").integers(2**31, size=8)
        bench.target_rng(1, "B").integers(2**31, size=1234)
        np.testing.assert_array_equal(a, bench.target_rng(1, "A").integers(2**31, size=8))
        self.assertFalse(np.array_equal(a, bench.target_rng(1, "B").integers(2**31, size=8)))
        self.assertFalse(np.array_equal(a, bench.target_rng(2, "A").integers(2**31, size=8)))


class ProjectionTests(unittest.TestCase):
    def test_joint_design_does_not_duplicate_pooled_baselines(self):
        arms = bench.REGISTERED_ARMS
        self.assertEqual(len(arms), 14)
        self.assertEqual(len(set(arms)), 14)
        self.assertEqual(arms.count((1., 0., "pooled")), 1)
        self.assertEqual(arms.count((2., 0., "pooled")), 1)
        self.assertEqual(sum(generator == "bins" for _, _, generator in arms), 2)
        for arm in arms:
            self.assertEqual(bench.parse_arm(bench.arm_cli(arm)), arm)

    def test_joint_shortlist_has_two_total_and_deterministic_family_tie(self):
        def candidate(a, phi, kind, value):
            return {"amplitude": a, "phi_scale": phi, "generator": kind, "delta_projection": value}
        candidates = [candidate(2, 0, "bins", .05), candidate(1.5, .25, "pooled", .06),
                      candidate(1, 0, "bins", .02), candidate(1, .5, "pooled", .01)]
        self.assertEqual(bench.joint_shortlist(candidates), [[1.5, .25, "pooled"], [2, 0, "bins"]])
        tied = [candidate(1, 0, "bins", .0205), candidate(1, 0, "pooled", .0200),
                candidate(1.5, 0, "pooled", .0209)]
        self.assertEqual(bench.joint_shortlist(tied)[0], [1, 0, "pooled"])

    def test_windows_manifest_can_relocate_on_remote_runner(self):
        manifest = {"path_roots": {"repo": "C:\\old\\repo", "data": "C:\\old\\data"}}
        self.assertEqual(bench.relocated_path("C:\\old\\data\\raw\\a.h5ad", manifest, Path("/remote/data")),
                         Path("/remote/data/raw/a.h5ad"))
        self.assertEqual(bench.relocated_path("C:\\old\\repo\\src\\x.py", manifest, Path("/remote/data")),
                         bench.REPO / "src/x.py")

    def test_bins_integration_preserves_target_bulk_and_has_fresh_counts(self):
        from vcc2026.inference import predicted_profile
        depth_class = bench.load_depth_candidate()
        rng = np.random.default_rng(12)
        # Depth is deliberately coupled to composition; both genes remain positive.
        means = np.vstack([np.tile([8., 2., 3., 1.], (100, 1)),
                           np.tile([10., 90., 20., 15.], (100, 1))])
        controls = sp.csr_matrix(rng.poisson(means).astype(np.float32))
        model = depth_class.fit(controls)
        lfc, observed = np.array([.2, -.3, 0., .4], np.float32), np.array([True, True, False, True])
        counts, detail = model.sample(lfc, observed, 400, bench.target_rng(1, "T"), amplitude=1,
                                      generator="bins", max_stored_per_cell=4)
        self.assertEqual(counts.shape, (400, 4))
        self.assertTrue(np.all(counts.data == np.floor(counts.data)))
        self.assertEqual(detail["generator"], "bins")
        expected, _ = predicted_profile(model.model.pooled, lfc.astype(float) / np.log(2), observed)
        # A stochastic sum is close to the desired bulk; it is not pinned to it.
        actual = np.asarray(counts.sum(0)).ravel()
        np.testing.assert_allclose(actual / actual.sum(), expected / expected.sum(), atol=.04)
        self.assertFalse(np.array_equal(actual / actual.sum(), expected / expected.sum()))

    def test_projection_uses_each_members_eligible_denominator(self):
        ref = pd.DataFrame(np.ones((4, 5)), columns=bench.FIVE)
        cand = ref.copy()
        ref.iloc[0, 1] = cand.iloc[0, 1] = np.nan
        cand += np.array([0.1, -0.2, 0.3, 0.4, 0.5])
        idx = np.array([[0, 1, 2, 3], [1, 2, 3, 1]])
        with np.errstate(invalid="ignore"):
            result, draws = bench.projected_contrast([cand], [ref], [1, -1, 1, 1, 1], idx)
        self.assertAlmostEqual(result["delta_projection"], 1.5 / 6)
        np.testing.assert_allclose(draws, [1.5 / 6, 1.5 / 6])
        self.assertEqual(result["eligible_targets_per_member"][bench.FIVE[1]], 3)

    def test_changed_eligibility_is_refused(self):
        ref = pd.DataFrame(np.ones((4, 5)), columns=bench.FIVE)
        cand = ref.copy()
        cand.iloc[0, 1] = np.nan
        with self.assertRaises(ValueError):
            bench.projected_contrast([cand], [ref], np.ones(5), np.array([[0, 1, 2, 3]]))

    def test_fulltruth_never_offers_overlapping_replica(self):
        uninitialised = object.__new__(bench.FullTruthBench)
        with self.assertRaises(RuntimeError):
            uninitialised.anchors()

    def test_fulltruth_small_real_scorer_integration(self):
        rng = np.random.default_rng(29)
        genes = np.array(["T1", "T2", "T3", *[f"G{i}" for i in range(37)]])
        ctrl = rng.poisson(30, size=(100, len(genes))).astype(np.float32)
        blocks = []
        for i in range(3):
            profile = np.full(len(genes), 30.)
            profile[i * 10:(i + 1) * 10] *= 2
            blocks.append(rng.poisson(profile, size=(40, len(genes))).astype(np.float32))
        x = sp.csr_matrix(np.vstack([ctrl, *blocks]))
        rows = {f"T{i + 1}": np.arange(100 + 40 * i, 140 + 40 * i) for i in range(3)}
        with tempfile.TemporaryDirectory() as tmp:
            instance = bench.FullTruthBench(x, rows, np.arange(100), genes, Path(tmp))
            self.assertEqual(instance.cfg.device, "cpu")
            self.assertEqual(instance.real_ad.shape[0], 220)
            self.assertEqual(sum(len(v) for v in instance.half_a.values()), 120)
            result = instance.score("synthetic", sp.vstack([sp.csr_matrix(b) for b in blocks]),
                                    np.repeat(["T1", "T2", "T3"], 40))
            self.assertEqual(set(result["raw"]), set(bench.SCORED))
            self.assertGreater(result["raw"]["pds_cosine"], 0.99)


if __name__ == "__main__":
    unittest.main()
