"""Production dispersion interpolation preserves both legacy endpoints."""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from vcc2026.inference import BasalProfile
from vcc2026.sampling import sample_counts

spec = importlib.util.spec_from_file_location("stage45_dispersion_test", REPO / "scripts/45_generate_prediction.py")
stage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = stage
spec.loader.exec_module(stage)


class DispersionScaleTests(unittest.TestCase):
    def test_rejects_invalid_or_ineffective_cli_scale(self):
        base = ["stage45", "--run-id", "test", "--trial", "trial-ext-profile"]
        for value in ["-1", "nan", "inf"]:
            with self.subTest(value=value), patch.object(sys, "argv", base + ["--gene-dispersion", "--gene-dispersion-scale", value]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    stage.parse_args()
        with patch.object(sys, "argv", base + ["--gene-dispersion-scale", "0.5"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                stage.parse_args()

    def test_scale_changes_fitted_variance_without_changing_fit_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "control.h5ad"
            with h5py.File(path, "w") as f:
                f.create_dataset("X/indices", data=np.array([0, 1, 0]))
            basal = BasalProfile("A", np.array([3.0, 1.0]), np.array([2, 2]), 2, np.array([2, 1]), str(path))
            fitted = np.array([0.4, 2.0])
            with patch.object(stage, "fit_gene_dispersion", return_value=fitted) as fit:
                full = stage.fit_dispersions({"A": basal}, 2, 12)
                half = stage.fit_dispersions({"A": basal}, 2, 12, scale=0.5)
                zero = stage.fit_dispersions({"A": basal}, 2, 12, scale=0.0)
            np.testing.assert_array_equal(full["A"], fitted)
            np.testing.assert_array_equal(half["A"], fitted / 2)
            np.testing.assert_array_equal(zero["A"], np.zeros(2))
            for call in fit.call_args_list:
                np.testing.assert_array_equal(call.args[2], [0.0, 0.5])
                self.assertEqual(call.kwargs, {"seed": 12})

    def test_zero_vector_is_bit_identical_to_poisson(self):
        profile = np.array([1.0, 3.0, 6.0])
        libraries = np.array([100, 200, 500] * 15)
        kwargs = {"max_stored_per_cell": 3, "max_counts_per_cell": 1000000}
        a = sample_counts(profile, libraries, np.random.default_rng(982), **kwargs)
        b = sample_counts(profile, libraries, np.random.default_rng(982), overdispersion=np.zeros(3), **kwargs)
        for attr in ["data", "indices", "indptr"]:
            np.testing.assert_array_equal(getattr(a, attr), getattr(b, attr))


if __name__ == "__main__":
    unittest.main()
