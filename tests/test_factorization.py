"""Factorisation contract: exact vs randomized, centring, pooled bootstrap.

These tests do not claim that randomized SVD is interchangeable with the
exact one on real data. They make the silent failures loud: a missing seed,
an uncentred matrix treated as centred, a bootstrap that averages ratios
and calls the result pooled_mse_vs_null, or two aggregations that can
disagree in sign being treated as a contradiction.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.benchmark.evaluate import (  # noqa: E402
    aggregate_targets,
    paired_difference,
    paired_pooled_difference,
    score_matrix,
)
from vcc2026.benchmark.factorization import (  # noqa: E402
    FactorizationSpec,
    factorize,
    ranks_compatible_with_shape,
    reconstruct,
    relative_reconstruction_error,
)
from vcc2026.benchmark.models import MaskedLowRank, ModularFrozen  # noqa: E402
from vcc2026.benchmark.protocol import TrainArrays  # noqa: E402
from vcc2026.benchmark.universe import GeneUniverse  # noqa: E402


def _lowrank_matrix(n=40, p=25, rank=5, seed=0, noise=1e-6):
    rng = np.random.default_rng(seed)
    U = rng.normal(size=(n, rank))
    V = rng.normal(size=(p, rank))
    S = np.linspace(5.0, 1.0, rank)
    A = (U * S) @ V.T
    A = A - A.mean(axis=0, keepdims=True)
    A = A + noise * rng.normal(size=A.shape)
    return A


class TestExactMatchesNumpy(unittest.TestCase):
    def test_exact_matches_linalg_svd(self):
        A = _lowrank_matrix()
        k = 5
        fac = factorize(A, k, FactorizationSpec(method="exact"))
        U, S, Vt = np.linalg.svd(A, full_matrices=False)
        np.testing.assert_allclose(fac.S, S[:k], atol=1e-10)
        np.testing.assert_allclose(fac.U, U[:, :k], atol=1e-10)
        np.testing.assert_allclose(fac.Vt, Vt[:k], atol=1e-10)
        self.assertEqual(fac.method_used, "exact")
        self.assertIsNone(fac.fallback)

    def test_exact_does_not_centre(self):
        rng = np.random.default_rng(1)
        raw = rng.normal(size=(30, 12)) + 4.0
        centred = raw - raw.mean(axis=0, keepdims=True)
        k = 3
        fac_raw = factorize(raw, k, FactorizationSpec(method="exact"))
        fac_c = factorize(centred, k, FactorizationSpec(method="exact"))
        # A constant column shift moves the leading direction. If factorize
        # centred on its own, the two calls would agree.
        self.assertFalse(np.allclose(fac_raw.S, fac_c.S, atol=1e-6))


class TestRandomizedContract(unittest.TestCase):
    def test_requires_an_explicit_seed(self):
        with self.assertRaisesRegex(ValueError, "explicit seed"):
            FactorizationSpec(method="randomized")

    def test_same_seed_same_factors(self):
        A = _lowrank_matrix(seed=2)
        spec = FactorizationSpec(method="randomized", seed=2026, n_oversamples=10, n_iter=2)
        a = factorize(A, 5, spec)
        b = factorize(A, 5, spec)
        np.testing.assert_allclose(a.U, b.U)
        np.testing.assert_allclose(a.S, b.S)
        np.testing.assert_allclose(a.Vt, b.Vt)

    def test_shapes_and_reconstruction_on_low_rank(self):
        A = _lowrank_matrix(n=50, p=30, rank=4, noise=0.0)
        spec = FactorizationSpec(
            method="randomized", seed=7, n_oversamples=10, n_iter=2
        )
        fac = factorize(A, 4, spec)
        self.assertEqual(fac.U.shape, (50, 4))
        self.assertEqual(fac.S.shape, (4,))
        self.assertEqual(fac.Vt.shape, (4, 30))
        self.assertEqual(fac.k, 4)
        err = relative_reconstruction_error(A, fac.U, fac.S, fac.Vt)
        self.assertLess(err, 1e-8)

    def test_wide_sketch_falls_back_to_exact(self):
        A = _lowrank_matrix(n=12, p=10, rank=3)
        spec = FactorizationSpec(
            method="randomized", seed=1, n_oversamples=50, n_iter=1
        )
        fac = factorize(A, 3, spec)
        self.assertEqual(fac.method_used, "exact")
        self.assertIsNotNone(fac.fallback)
        U, S, Vt = np.linalg.svd(A, full_matrices=False)
        np.testing.assert_allclose(fac.S, S[:3], atol=1e-10)

    def test_do_not_compare_vectors_elementwise_across_seeds(self):
        """Signs and bases move; reconstruction is the quantity to check."""
        A = _lowrank_matrix(n=60, p=40, rank=6, noise=1e-3)
        a = factorize(A, 6, FactorizationSpec(method="randomized", seed=1))
        b = factorize(A, 6, FactorizationSpec(method="randomized", seed=2))
        recon_a = relative_reconstruction_error(A, a.U, a.S, a.Vt)
        recon_b = relative_reconstruction_error(A, b.U, b.S, b.Vt)
        self.assertLess(recon_a, 0.05)
        self.assertLess(recon_b, 0.05)
        # Elementwise disagreement is allowed and is not a test failure.
        _ = np.max(np.abs(a.Vt - b.Vt))

    def test_incompatible_ranks_are_dropped_not_silently_clipped(self):
        self.assertEqual(ranks_compatible_with_shape([16, 32, 64, 128], (40, 100)), [16, 32])
        self.assertEqual(ranks_compatible_with_shape([128], (20, 50)), [19])


class TestModelsStillCentre(unittest.TestCase):
    def setUp(self):
        self.uni = GeneUniverse(
            observed=np.array([1, 1, 1, 1, 0], dtype=bool),
            per_source_n={"a": 4}, n_official=5,
        )
        rng = np.random.default_rng(3)
        self.X = rng.normal(size=(24, 3))
        basis = rng.normal(size=(3, 4))
        z = rng.normal(size=(24, 3))
        self.Y = z @ basis + 2.5
        self.arrays = TrainArrays(
            X=self.X, Y=self.Y,
            targets=tuple(f"T{i}" for i in range(24)),
            feature_names=("f0", "f1", "f2"),
            feature_specs=(), uses_context_features=True,
            n_unique_context_rows=1,
        )

    def test_lowrank_stores_the_column_mean(self):
        m = MaskedLowRank(rank=3, ridge=1.0)
        m.fit(self.arrays, self.uni)
        np.testing.assert_allclose(m._mean_y[0], self.Y.mean(axis=0), atol=1e-12)
        self.assertEqual(m._factorization_info["method_used"], "exact")

    def test_randomized_lowrank_is_reproducible(self):
        spec = FactorizationSpec(method="randomized", seed=11, n_iter=2)
        a = MaskedLowRank(rank=3, ridge=1.0, factorization=spec)
        b = MaskedLowRank(rank=3, ridge=1.0, factorization=spec)
        a.fit(self.arrays, self.uni)
        b.fit(self.arrays, self.uni)
        np.testing.assert_allclose(
            a.predict_delta(self.X[:4]), b.predict_delta(self.X[:4]), atol=1e-10
        )

    def test_frozen_randomized_shapes(self):
        spec = FactorizationSpec(method="randomized", seed=4, n_iter=1)
        m = ModularFrozen(
            rank=3, hidden=4, epochs=2, patience=2, batch=8, seed=1,
            factorization=spec,
        )
        m.fit(self.arrays, self.uni)
        pred = m.predict_delta(self.X[:2])
        self.assertEqual(pred.shape, (2, 4))
        self.assertEqual(m._k, 3)


class TestPooledBootstrap(unittest.TestCase):
    def test_null_still_has_pooled_ratio_one(self):
        truth = np.array([[1.0, -2.0, 0.5], [0.5, 0.5, -1.0]])
        pred = np.zeros_like(truth)
        out = score_matrix(pred, truth, targets=["A", "B"], strong_threshold=0.5)
        self.assertAlmostEqual(out["pooled_mse_vs_null"], 1.0)
        self.assertAlmostEqual(out["per_target"][0]["sse"] / out["per_target"][0]["sst"],
                               out["per_target"][0]["mse_vs_null"])

    def test_pooled_interval_is_the_ratio_of_sums(self):
        rng = np.random.default_rng(0)
        truth = rng.normal(size=(20, 6))
        pred = 0.5 * truth
        out = score_matrix(
            pred, truth, targets=[f"T{i}" for i in range(20)], strong_threshold=0.5
        )
        agg = aggregate_targets(out, n_boot=50, seed=1)
        self.assertEqual(agg["pooled"]["aggregation"], "ratio_of_pooled_sums")
        self.assertEqual(
            agg["bootstrap_over_targets"]["mse_vs_null"]["aggregation"],
            "mean_of_per_target_values",
        )
        lo, hi = agg["pooled"]["ci95"]
        self.assertLessEqual(lo, out["pooled_mse_vs_null"])
        self.assertGreaterEqual(hi, out["pooled_mse_vs_null"])

    def test_mean_of_ratios_is_not_the_pooled_ratio(self):
        # One large-effect target and one small one: the two aggregations diverge.
        truth = np.array([
            [10.0, 10.0],
            [0.1, 0.1],
        ])
        pred = np.array([
            [9.0, 9.0],
            [1.1, 1.1],
        ])
        out = score_matrix(pred, truth, targets=["big", "small"], strong_threshold=0.5)
        pooled = out["pooled_mse_vs_null"]
        mean_ratio = out["mse_vs_null_mean"]
        self.assertFalse(np.isclose(pooled, mean_ratio, atol=0.05))

    def test_paired_aggregations_can_disagree_in_sign(self):
        """Mean of ratios vs ratio of sums: opposite signs are not a contradiction."""
        per_a, per_b = [], []
        for i in range(5):
            per_a.append({"target": f"L{i}", "sse": 90.0, "sst": 100.0, "mse_vs_null": 0.9})
            per_b.append({"target": f"L{i}", "sse": 50.0, "sst": 100.0, "mse_vs_null": 0.5})
        for i in range(5):
            per_a.append({"target": f"S{i}", "sse": 0.1, "sst": 1.0, "mse_vs_null": 0.1})
            per_b.append({"target": f"S{i}", "sse": 2.0, "sst": 1.0, "mse_vs_null": 2.0})
        mean_diff = paired_difference(
            per_a, per_b, key="mse_vs_null", n_boot=80, seed=2
        )
        pooled_diff = paired_pooled_difference(per_a, per_b, n_boot=80, seed=2)
        self.assertEqual(mean_diff["aggregation"], "mean_of_per_target_differences")
        self.assertEqual(pooled_diff["aggregation"], "paired_pooled_ratio_difference")
        self.assertLess(mean_diff["mean_a_minus_b"], 0.0)
        self.assertGreater(pooled_diff["mean_a_minus_b"], 0.0)
        self.assertTrue(mean_diff["ci95_excludes_zero"])
        self.assertTrue(pooled_diff["ci95_excludes_zero"])

    def test_paired_pooled_resamples_the_same_targets(self):
        per_a = [{"target": f"T{i}", "sse": 1.0 + i, "sst": 4.0, "mse_vs_null": (1.0 + i) / 4.0}
                 for i in range(12)]
        per_b = [{"target": f"T{i}", "sse": 2.0, "sst": 4.0, "mse_vs_null": 0.5}
                 for i in range(12)]
        once = paired_pooled_difference(per_a, per_b, n_boot=40, seed=9)
        twice = paired_pooled_difference(per_a, per_b, n_boot=40, seed=9)
        self.assertEqual(once["ci95"], twice["ci95"])
        self.assertAlmostEqual(once["point_a"] - once["point_b"], once["mean_a_minus_b"])


class TestReconstructHelper(unittest.TestCase):
    def test_reconstruct_roundtrip_exact(self):
        A = _lowrank_matrix(noise=0.0)
        fac = factorize(A, 5, FactorizationSpec(method="exact"))
        np.testing.assert_allclose(reconstruct(fac.U, fac.S, fac.Vt), A, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
