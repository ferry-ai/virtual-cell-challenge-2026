"""The optional depth generator preserves the live contract and the preregistered arm."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import h5py
import numpy as np
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.depth_generator import DepthGenerator
from vcc2026.inference import BasalProfile, predicted_profile


def load_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def controls_fixture():
    # The gene absent in all cells must remain absent. The low/high depth states
    # have different gene proportions and some bin-specific zero support.
    return sp.csr_matrix(np.array([
        [8 + i, 1, 2, 0, 0] if i < 8 else [5, 20 + 3*i, 5 + i, 3, 0]
        for i in range(32)
    ], dtype=np.float32))


def write_control(path, counts):
    with h5py.File(path, "w") as f:
        group = f.create_group("X")
        group.attrs["shape"] = counts.shape
        group.create_dataset("data", data=counts.data)
        group.create_dataset("indices", data=counts.indices)
        group.create_dataset("indptr", data=counts.indptr)


class DepthGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "control.h5ad"
        self.counts = controls_fixture()
        write_control(self.path, self.counts)
        self.libs = np.asarray(self.counts.sum(axis=1), dtype=np.float64).ravel()
        self.basal = np.asarray(self.counts.sum(axis=0), dtype=np.float64).ravel()
        self.model = DepthGenerator.fit_h5ad(self.path, self.libs, self.basal, block_rows=3)

    def test_streamed_fit_and_sample_match_preregistered_research_arm(self):
        research_path = REPO / "reports/analisi/lead_scientist_2026-09-29/generatore"
        with mock.patch.object(sys, "path", [str(research_path), *sys.path]):
            research = load_file(research_path / "depth_candidate.py", "depth_candidate_for_production_test")
        reference = research.DepthCandidate.fit(self.counts)
        self.assertEqual(self.model.diagnostics["selected"], reference.selection["selected"])
        np.testing.assert_array_equal(self.model.profiles, reference.model.profiles)
        np.testing.assert_array_equal(self.model.cell_bins, reference.model.cell_bins)
        effect = np.array([-.5, .3, 0, .4, 0])
        observed = np.array([True, True, True, False, False])
        profile, _ = predicted_profile(self.basal, effect / np.log(2), observed)
        actual, _ = self.model.sample(profile, 37, np.random.default_rng(6),
                                      max_stored_per_cell=5, max_counts_per_cell=1000000)
        expected, _ = reference.sample(effect, observed, 37, np.random.default_rng(6),
                                        max_stored_per_cell=5, max_counts_per_cell=1000000)
        np.testing.assert_array_equal(actual.toarray(), expected.toarray())

    def test_observed_zero_and_unobserved_nonzero_keep_stage45_population_profile(self):
        observed = np.array([True, True, True, False, False])
        # The unobserved nonzero is ignored; the observed zero takes the same
        # compositional correction production uses on every supported gene.
        profile, _ = predicted_profile(self.basal, np.array([-.4, .2, 0, 5, 6]), observed)
        profiles, detail = self.model.calibrated_profiles(profile)
        expected = profile / profile.sum()
        realised = self.model.depth_weights @ profiles
        np.testing.assert_allclose(realised, expected, atol=1e-12)
        np.testing.assert_allclose(realised[~observed], self.model.pooled[~observed], atol=1e-12)
        self.assertLess(detail["max_absolute_pooled_error"], 1e-12)

    def test_support_smoothing_can_move_a_gene_outside_its_original_bin_margin(self):
        profile = self.basal.copy()
        profile[3] *= 200
        profiles, _ = self.model.calibrated_profiles(profile)
        np.testing.assert_allclose(self.model.depth_weights @ profiles, profile / profile.sum(), atol=1e-12)
        self.assertTrue(np.all(profiles[:, 4] == 0))

    def test_mismatched_basal_input_is_rejected(self):
        wrong = self.libs.copy()
        wrong[2] += 1
        with self.assertRaisesRegex(ValueError, "library sizes changed"):
            DepthGenerator.fit_h5ad(self.path, wrong, self.basal)
        wrong_profile = self.basal.copy()
        wrong_profile[0] += 1
        with self.assertRaisesRegex(ValueError, "pooled profile changed"):
            DepthGenerator.fit_h5ad(self.path, self.libs, wrong_profile)

    def test_invalid_target_and_nonconvergence_fail_instead_of_silent_fallback(self):
        unsupported = self.basal.copy()
        unsupported[-1] = 1
        with self.assertRaisesRegex(ValueError, "absent from all controls"):
            self.model.calibrated_profiles(unsupported)
        moved = self.basal * np.array([.001, 1, 1, 100, 1])
        with self.assertRaisesRegex(RuntimeError, "calibration failed"):
            self.model.calibrated_profiles(moved, max_iterations=1)

    def test_sample_remains_stochastic_integer_and_caps_are_reported(self):
        a, _ = self.model.sample(self.basal, 30, np.random.default_rng(2),
                                  max_stored_per_cell=5, max_counts_per_cell=1000000)
        b, _ = self.model.sample(self.basal, 30, np.random.default_rng(3),
                                  max_stored_per_cell=5, max_counts_per_cell=1000000)
        self.assertFalse(np.array_equal(np.asarray(a.sum(axis=0)), np.asarray(b.sum(axis=0))))
        capped, detail = self.model.sample(self.basal, 30, np.random.default_rng(3),
                                            max_stored_per_cell=1, max_counts_per_cell=10)
        self.assertTrue(np.equal(a.data, np.floor(a.data)).all())
        self.assertTrue(np.all(capped.getnnz(axis=1) <= 1))
        self.assertTrue(np.all(np.asarray(capped.sum(axis=1)).ravel() <= 10))
        self.assertGreater(detail["count_cap_cells"] + detail["storage_cap_cells"], 0)


class Stage45DepthIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = load_file(REPO / "scripts/45_generate_prediction.py", "stage45_for_depth_test")

    def test_cli_default_and_conflicting_dispersion_are_explicit(self):
        args = ["45", "--run-id", "test", "--trial", "trial-ext-profile"]
        with mock.patch.object(sys, "argv", args):
            self.assertFalse(self.stage.parse_args().depth_bins)
        for extra in [["--depth-bins", "--gene-dispersion"], ["--depth-bins", "--overdispersion", "0.1"]]:
            with mock.patch.object(sys, "argv", args + extra), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.stage.parse_args()

    def test_written_depth_blocks_match_model_and_record_population_error(self):
        counts = controls_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            control = path / "controls.h5ad"
            write_control(control, counts)
            libraries = np.asarray(counts.sum(axis=1)).ravel()
            raw = np.asarray(counts.sum(axis=0)).ravel()
            model = DepthGenerator.fit_h5ad(control, libraries, raw)
            basal = BasalProfile("A", raw, libraries, counts.shape[0], counts.getnnz(axis=1), str(control))
            axis = SimpleNamespace(symbols=[f"G{i}" for i in range(5)])
            # generate calls len(axis), so this tiny fixture supplies that one method.
            axis = type("Axis", (), {"symbols": axis.symbols, "__len__": lambda self: len(self.symbols)})()
            ch = SimpleNamespace(pert_col="target_gene", context_col="context", max_stored_per_cell=5, max_counts_per_cell=1000000)
            delta, observed = np.array([-.3, .1, 0, 1, 0]), np.array([True, True, True, False, False])
            with contextlib.redirect_stdout(io.StringIO()):
                generated = self.stage.generate(path / "prediction.h5ad", axis, ch, ["A"], ["T"], {"A": basal},
                                                {"A": {"T": (delta, observed)}}, {}, None, 37,
                                                np.random.default_rng(2), depth_models={"A": model})
            profile, _ = predicted_profile(raw, delta, observed)
            expected, _ = model.sample(profile, 37, np.random.default_rng(2), max_stored_per_cell=5, max_counts_per_cell=1000000)
            expected.sort_indices()
            with h5py.File(path / "prediction.h5ad") as f:
                np.testing.assert_array_equal(f["X/data"][:], expected.data)
                np.testing.assert_array_equal(f["X/indices"][:], expected.indices)
                np.testing.assert_array_equal(f["X/indptr"][:], expected.indptr)
            self.assertLess(generated.per_block[0]["depth_bins"]["max_absolute_pooled_error"], 1e-12)


if __name__ == "__main__":
    unittest.main()
