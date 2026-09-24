"""Tests for the contracts that fail silently if they break.

Every test here corresponds to a way this project could produce a confident
wrong number rather than an error: an unmeasured gene read as a zero effect, a
stale manifest overwritten. Speed and coverage are not the point; the point is
that these particular mistakes become loud. (The split, registry and
pseudobulk-parsing contracts left with their modules on 23 September, the
signature and model contracts on 24 September: docs/ARCHIVIO.md.)
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.evaluation import VCC_SCORED_METRICS, delta_metrics  # noqa: E402
from vcc2026.genes import GeneAxis, align_to_axis  # noqa: E402
from vcc2026.manifest import RunManifest, file_fingerprint  # noqa: E402


def tiny_axis(n: int = 8) -> GeneAxis:
    return GeneAxis(symbols=tuple(f"G{i}" for i in range(n)))


class TestGeneAxisAlignment(unittest.TestCase):
    """D-009: an unmeasured gene gets a mask, never a zero."""

    def test_unmeasured_genes_are_masked_not_zeroed(self):
        axis = tiny_axis(5)
        aligned = align_to_axis(
            np.array([[1.0, 2.0]]), ["G1", "G3"], ["t"], axis=axis
        )
        np.testing.assert_array_equal(
            aligned.observed, [False, True, False, True, False]
        )
        # The unmeasured positions hold 0.0, but the mask is what makes them
        # readable; a caller that ignores the mask is the bug this guards.
        self.assertEqual(aligned.values[0, 1], 1.0)
        self.assertEqual(aligned.values[0, 3], 2.0)
        self.assertEqual(aligned.n_observed, 2)

    def test_off_axis_symbols_are_reported_not_silently_dropped(self):
        axis = tiny_axis(3)
        aligned = align_to_axis(
            np.array([[1.0, 2.0, 3.0]]), ["G0", "NOTAGENE", "G2"], ["t"], axis=axis
        )
        self.assertEqual(aligned.dropped, ("NOTAGENE",))

    def test_duplicate_symbols_sum_and_are_recorded(self):
        axis = tiny_axis(3)
        aligned = align_to_axis(
            np.array([[1.0, 2.0, 5.0]]), ["G0", "G0", "G2"], ["t"],
            duplicate_policy="sum", axis=axis,
        )
        self.assertEqual(aligned.values[0, 0], 3.0)
        self.assertEqual(aligned.collapsed, {"G0": 2})

    def test_duplicate_policy_error_raises(self):
        axis = tiny_axis(3)
        with self.assertRaises(ValueError):
            align_to_axis(np.array([[1.0, 2.0]]), ["G0", "G0"], ["t"],
                          duplicate_policy="error", axis=axis)

    def test_shape_mismatch_raises(self):
        axis = tiny_axis(3)
        with self.assertRaises(ValueError):
            align_to_axis(np.array([[1.0, 2.0]]), ["G0", "G1", "G2"], ["t"], axis=axis)


class TestDeltaMetrics(unittest.TestCase):
    def test_perfect_prediction(self):
        t = np.array([1.0, -2.0, 0.5, 3.0, -1.0])
        m = delta_metrics(t, t, np.ones(5, dtype=bool))
        self.assertAlmostEqual(m.pearson, 1.0, places=6)
        self.assertAlmostEqual(m.mse, 0.0, places=12)
        self.assertAlmostEqual(m.sign_agreement, 1.0)

    def test_mask_excludes_rather_than_zero_fills(self):
        pred = np.array([1.0, 999.0, 2.0])
        truth = np.array([1.0, -999.0, 2.0])
        m = delta_metrics(pred, truth, np.array([True, False, True]))
        self.assertEqual(m.n_genes, 2)
        self.assertAlmostEqual(m.mse, 0.0, places=12)

    def test_degenerate_input_gives_nan_not_zero(self):
        m = delta_metrics(np.array([1.0]), np.array([1.0]), np.array([True]))
        self.assertTrue(np.isnan(m.pearson))

    def test_strong_sign_agreement_ignores_near_null_genes(self):
        truth = np.array([2.0, -2.0, 0.01, -0.01])
        pred = np.array([1.0, -1.0, -5.0, 5.0])  # wrong on the two null genes
        m = delta_metrics(pred, truth, np.ones(4, dtype=bool), strong_threshold=0.5)
        self.assertAlmostEqual(m.sign_agreement_strong, 1.0)
        self.assertEqual(m.n_strong, 2)
        self.assertAlmostEqual(m.sign_agreement, 0.5)


class TestManifest(unittest.TestCase):
    def test_manifest_refuses_to_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.json"
            RunManifest(run_id="r", stage="s").write(path)
            with self.assertRaises(FileExistsError):
                RunManifest(run_id="r", stage="s").write(path)
            RunManifest(run_id="r", stage="s").write(path, allow_overwrite=True)

    def test_manifest_records_environment_and_seed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.json"
            RunManifest(run_id="r", stage="s", seed=7).write(path)
            body = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(body["seed"], 7)
            self.assertIn("cell-eval2", body["environment"]["packages"])
            self.assertIn("python", body["environment"])

    def test_fingerprint_marks_sampled_hashes_as_sampled(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.bin"
            p.write_bytes(b"x" * 1024)
            self.assertEqual(file_fingerprint(p)["sha256_mode"], "full")
            self.assertIn("sample", file_fingerprint(p, full=False)["sha256_mode"])

    def test_fingerprint_of_missing_file_says_so(self):
        self.assertFalse(file_fingerprint(Path("nope.bin"))["exists"])


class TestConfigPortability(unittest.TestCase):
    """No new component may depend on a hardcoded Windows path."""

    def test_artifact_root_honours_environment(self):
        old = os.environ.get(config.ARTIFACT_ENV)
        try:
            os.environ[config.ARTIFACT_ENV] = str(Path(tempfile.gettempdir()) / "vccart")
            config.reset_caches()
            self.assertTrue(str(config.artifact_root()).endswith("vccart"))
        finally:
            if old is None:
                os.environ.pop(config.ARTIFACT_ENV, None)
            else:
                os.environ[config.ARTIFACT_ENV] = old
            config.reset_caches()

    def test_run_dir_rejects_path_traversal(self):
        for bad in ("..", "a/b", "a\\b", "", "a:b"):
            with self.assertRaises(ValueError, msg=f"accepted {bad!r}"):
                config.run_dir(bad, create=False)

    def test_no_hardcoded_data_root_in_new_modules(self):
        offenders = []
        for path in (REPO / "src" / "vcc2026").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "C:/Users" in text or "C:\\\\Users" in text:
                offenders.append(path.name)
        self.assertEqual(offenders, [], f"hardcoded paths in {offenders}")


class TestScorerContract(unittest.TestCase):
    def test_six_scored_metrics_are_named(self):
        self.assertEqual(len(VCC_SCORED_METRICS), 6)

    def test_recorded_contract_matches_the_named_metrics(self):
        contract = json.loads(
            (REPO / "reports/scorer/vcc2026_contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sorted(contract["scored_metrics"]), sorted(VCC_SCORED_METRICS))


if __name__ == "__main__":
    unittest.main()
