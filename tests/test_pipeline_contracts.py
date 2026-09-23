"""Tests for the contracts that fail silently if they break.

Every test here corresponds to a way this project could produce a confident
wrong number rather than an error: an unmeasured gene read as a zero effect, a
stale manifest overwritten. Speed and coverage are not the point; the point is
that these particular mistakes become loud. (The split, registry and
pseudobulk-parsing contracts left with their modules on 23 September:
docs/ARCHIVIO.md.)
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
from vcc2026.models import (  # noqa: E402
    NullModel, ShrunkTransfer, WeightedTransfer,
)
from vcc2026.signatures import Signature, SignatureSet, delta_from_pseudobulk  # noqa: E402


def tiny_axis(n: int = 8) -> GeneAxis:
    return GeneAxis(symbols=tuple(f"G{i}" for i in range(n)))


def patch_axis(axis: GeneAxis):
    """Point the module-level official axis at a small test axis.

    Idempotent: after the first call the name no longer refers to an lru_cache
    wrapper, so clearing the cache is conditional. Without that guard every
    setUp after the first raises AttributeError.
    """
    import vcc2026.genes as genes
    import vcc2026.models as models
    import vcc2026.signatures as signatures

    if hasattr(genes.official_axis, "cache_clear"):
        genes.official_axis.cache_clear()
    stub = lambda path=None: axis  # noqa: E731
    for mod in (genes, signatures, models):
        mod.official_axis = stub
    return axis


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


class TestSignatureUncertainty(unittest.TestCase):
    """Numerosity must move the standard error, or weighting is meaningless."""

    def setUp(self):
        self.axis = patch_axis(tiny_axis(4))

    def test_standard_error_shrinks_as_cells_increase(self):
        symbols = ["G0", "G1", "G2", "G3"]
        base = np.array([[100.0, 200.0, 50.0, 25.0]])
        ctrl = np.array([100.0, 200.0, 50.0, 25.0])

        ses = []
        for scale in (1, 10, 100):
            aligned = align_to_axis(base * scale, symbols, ["t"], axis=self.axis)
            _, se, _ = delta_from_pseudobulk(
                aligned, ctrl * scale, np.ones(4, dtype=bool),
                library_sizes=np.array([375.0 * scale]),
                control_library_size=375.0 * scale,
            )
            ses.append(float(np.median(se)))
        self.assertGreater(ses[0], ses[1])
        self.assertGreater(ses[1], ses[2])
        # Poisson: ten times the counts should roughly cut the SE by sqrt(10).
        self.assertAlmostEqual(ses[0] / ses[1], np.sqrt(10), delta=0.3)

    def test_identical_profiles_give_zero_delta(self):
        symbols = ["G0", "G1", "G2", "G3"]
        counts = np.array([[100.0, 200.0, 50.0, 25.0]])
        aligned = align_to_axis(counts, symbols, ["t"], axis=self.axis)
        delta, _, _ = delta_from_pseudobulk(
            aligned, counts[0], np.ones(4, dtype=bool),
            library_sizes=np.array([375.0]), control_library_size=375.0,
        )
        np.testing.assert_allclose(delta, 0.0, atol=1e-12)

    def test_shrinkage_pulls_noisy_genes_harder(self):
        sig = Signature(
            source="s", context="c", target="T",
            delta=np.array([1.0, 1.0, 1.0, 1.0]),
            se=np.array([0.01, 0.1, 1.0, 10.0]),
            observed=np.ones(4, dtype=bool),
            n_cells=100, n_control_cells=100,
        )
        out = sig.shrunk(prior_sd=1.0)
        self.assertTrue(np.all(np.diff(out) < 0), "shrinkage must be monotone in se")
        self.assertGreater(out[0], 0.99)      # well measured: barely touched
        self.assertLess(out[3], 0.02)         # hopeless: nearly erased

    def test_collapse_guides_never_narrows_below_observed_disagreement(self):
        """Guides that disagree must widen the interval, not average it away."""
        obs = np.ones(4, dtype=bool)
        se = np.full(4, 0.01)
        agree = SignatureSet([
            Signature("s", "c", "T", np.full(4, 1.0), se.copy(), obs, 50, 50, f"g{i}")
            for i in range(4)
        ])
        disagree = SignatureSet([
            Signature("s", "c", "T", np.full(4, v), se.copy(), obs, 50, 50, f"g{i}")
            for i, v in enumerate([-2.0, 1.0, 2.0, 3.0])
        ])
        se_agree = agree.collapse_guides().signatures[0].se
        se_disagree = disagree.collapse_guides().signatures[0].se
        self.assertTrue(np.all(se_disagree > se_agree))
        self.assertEqual(agree.collapse_guides().signatures[0].meta["n_guides"], 4)

    def test_negative_standard_error_rejected(self):
        with self.assertRaises(ValueError):
            Signature("s", "c", "T", np.zeros(4), np.array([-1.0, 0, 0, 0]),
                      np.ones(4, dtype=bool), 1, 1)


class TestModels(unittest.TestCase):
    def setUp(self):
        self.axis = patch_axis(tiny_axis(4))
        obs = np.ones(4, dtype=bool)
        self.train = SignatureSet([
            Signature("k562", "K562", "T1", np.array([1.0, -1.0, 0.5, 0.0]),
                      np.full(4, 0.1), obs, 100, 100, "g1"),
            Signature("cd4", "CD4", "T1", np.array([2.0, -2.0, 1.0, 0.0]),
                      np.full(4, 0.1), obs, 100, 100, "g1"),
        ])

    def test_null_predicts_zero_everywhere(self):
        pred = NullModel().fit(self.train).predict("anything")
        np.testing.assert_array_equal(pred.delta, np.zeros(4))
        self.assertEqual(pred.support, 0)

    def test_unknown_target_is_unsupported_not_zero(self):
        pred = ShrunkTransfer(source="k562").fit(self.train).predict("NOPE")
        self.assertEqual(pred.support, 0)
        self.assertFalse(pred.observed.any(),
                         "an unknown target must be masked, not a confident zero")

    def test_alpha_scales_amplitude_linearly(self):
        half = ShrunkTransfer(alpha=0.5, prior_sd=1e6, source="k562").fit(
            self.train).predict("T1")
        full = ShrunkTransfer(alpha=1.0, prior_sd=1e6, source="k562").fit(
            self.train).predict("T1")
        np.testing.assert_allclose(half.delta * 2, full.delta, rtol=1e-6)

    def test_weighted_transfer_respects_weights(self):
        model = WeightedTransfer({"k562": 1.0, "cd4": 0.0}, prior_sd=1e6).fit(self.train)
        only_k562 = model.predict("T1")
        model2 = WeightedTransfer({"k562": 0.0, "cd4": 1.0}, prior_sd=1e6).fit(self.train)
        only_cd4 = model2.predict("T1")
        np.testing.assert_allclose(only_cd4.delta, only_k562.delta * 2, rtol=1e-6)

    def test_weighted_transfer_rejects_negative_weights(self):
        with self.assertRaises(ValueError):
            WeightedTransfer({"k562": -1.0})


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
