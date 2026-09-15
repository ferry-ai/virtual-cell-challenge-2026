"""Contracts for the context-conditioned component model.

None of this measures whether conditioning on the destination context helps.
It checks the properties that would let such a measurement be believed: that
the generalisation contains the incumbent exactly, that the common response is
built from training targets only, that an unmeasured gene keeps its mask, and
that components nobody can separate are refused instead of silently pinned.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vcc2026.context import (  # noqa: E402
    ComponentTransfer, basal_gene_features, common_response, fit_components,
)
from vcc2026.genes import GeneAxis  # noqa: E402
from vcc2026.models import ShrunkTransfer  # noqa: E402
from vcc2026.signatures import Signature, SignatureSet  # noqa: E402

N = 6
BIG_SD = 1e6  # prior_sd large enough that per-gene shrinkage is a no-op


def patch_axis(n: int = N) -> GeneAxis:
    """Point every module's official axis at a small test axis."""
    import vcc2026.context as context
    import vcc2026.genes as genes
    import vcc2026.models as models
    import vcc2026.signatures as signatures

    axis = GeneAxis(symbols=tuple(f"G{i}" for i in range(n)))
    if hasattr(genes.official_axis, "cache_clear"):
        genes.official_axis.cache_clear()
    stub = lambda path=None: axis  # noqa: E731
    for mod in (genes, signatures, models, context):
        mod.official_axis = stub
    return axis


def sig(target: str, delta, *, source: str = "k562", observed=None,
        se: float = 0.1) -> Signature:
    delta = np.asarray(delta, dtype=np.float64)
    obs = np.ones(delta.size, dtype=bool) if observed is None else np.asarray(observed)
    return Signature(source, "SRC", target, delta, np.full(delta.size, se),
                     obs, 100, 100, "g1")


class TestComponentFit(unittest.TestCase):
    def setUp(self):
        patch_axis()
        rng = np.random.default_rng(20260915)
        self.targets = tuple(f"T{i}" for i in range(8))
        self.source = SignatureSet([
            sig(t, rng.normal(size=N)) for t in self.targets
        ])

    def _truth_from(self, theta, names):
        """Destination signatures that are exactly theta . components(source)."""
        model = ComponentTransfer(names=names, theta=theta, prior_sd=BIG_SD,
                                  source="k562").fit(self.source)
        return SignatureSet([
            sig(t, model.predict(t).delta, source="rpe1") for t in self.targets
        ])

    def test_fit_recovers_known_coefficients(self):
        names = ("common", "specific")
        theta = np.array([0.30, 0.80])
        truth = self._truth_from(theta, names)
        fit = fit_components(self.source, truth, names=names, prior_sd=BIG_SD)
        np.testing.assert_allclose(fit.theta, theta, rtol=1e-8, atol=1e-10)
        self.assertEqual(fit.n_targets, len(self.targets))
        # The residual comes from ||y||^2 - 2.theta.b + theta'G.theta, which cancels
        # catastrophically when the fit is exact: judge it against the scale of the
        # truth, not against an absolute floor that only float64 noise has to clear.
        self.assertLess(fit.mse_vs_null, 1e-12,
                        "a noise-free fit must close on its own truth")

    def test_a_single_source_component_is_exactly_shrunk_transfer(self):
        """The generalisation contains the incumbent: same alpha, same numbers."""
        alpha = 0.1974
        incumbent = ShrunkTransfer(alpha=alpha, prior_sd=4.0,
                                   source="k562").fit(self.source)
        general = ComponentTransfer(names=("source",), theta=[alpha], prior_sd=4.0,
                                    source="k562").fit(self.source)
        for t in self.targets:
            np.testing.assert_allclose(general.predict(t).delta,
                                       incumbent.predict(t).delta, rtol=1e-12)

    def test_fitting_only_source_recovers_the_amplitude(self):
        truth = self._truth_from(np.array([0.25]), ("source",))
        fit = fit_components(self.source, truth, names=("source",), prior_sd=BIG_SD)
        self.assertAlmostEqual(float(fit.theta[0]), 0.25, places=9)

    def test_components_nobody_can_separate_are_refused(self):
        truth = self._truth_from(np.array([0.5]), ("source",))
        with self.assertRaises(ValueError) as caught:
            fit_components(self.source, truth, names=("source", "source"),
                           prior_sd=BIG_SD)
        self.assertIn("ill-conditioned", str(caught.exception))

    def test_ridge_makes_the_degenerate_case_solvable(self):
        truth = self._truth_from(np.array([0.5]), ("source",))
        fit = fit_components(self.source, truth, names=("source", "source"),
                             prior_sd=BIG_SD, ridge=1e-3)
        self.assertAlmostEqual(float(fit.theta.sum()), 0.5, places=3)

    def test_mse_vs_null_is_reported_against_predicting_nothing(self):
        truth = self._truth_from(np.array([0.5]), ("source",))
        fit = fit_components(self.source, truth, names=("source",), prior_sd=BIG_SD)
        self.assertGreater(fit.mse_null, 0.0)
        self.assertLess(fit.mse_vs_null, 1e-9)

    def test_no_shared_target_raises_instead_of_returning_zeros(self):
        other = SignatureSet([sig("ZZZ", np.ones(N), source="rpe1")])
        with self.assertRaises(ValueError):
            fit_components(self.source, other, names=("source",), prior_sd=BIG_SD)


class TestLeakage(unittest.TestCase):
    def setUp(self):
        patch_axis()

    def test_common_response_uses_only_the_targets_given(self):
        train = SignatureSet([sig("A", [1.0] * N), sig("B", [1.0] * N)])
        held_out = sig("C", [1000.0] * N)
        with_held_out = SignatureSet(list(train) + [held_out])

        only_train = common_response(train, prior_sd=BIG_SD)
        leaked = common_response(with_held_out, prior_sd=BIG_SD)

        np.testing.assert_allclose(only_train, np.ones(N), rtol=1e-6)
        self.assertGreater(leaked[0], 100.0,
                           "sanity: the held-out target would dominate if included")

    def test_fit_builds_common_from_the_chosen_targets_only(self):
        source = SignatureSet([sig("A", [1.0] * N), sig("B", [1.0] * N),
                               sig("C", [1000.0] * N)])
        truth = SignatureSet([sig(t, [1.0] * N, source="rpe1")
                              for t in ("A", "B", "C")])
        fit = fit_components(source, truth, names=("common",), prior_sd=BIG_SD,
                             targets=("A", "B"))
        # common == 1 over A and B, so theta must be 1 to reproduce a truth of 1.
        self.assertAlmostEqual(float(fit.theta[0]), 1.0, places=6)
        self.assertEqual(fit.n_targets, 2)


class TestMasksAndRefusals(unittest.TestCase):
    def setUp(self):
        patch_axis()
        self.source = SignatureSet([
            sig("T1", [1.0, -1.0, 0.5, 0.0, 2.0, -0.5],
                observed=np.array([True, True, False, True, True, True])),
        ])

    def test_unknown_target_is_masked_not_a_confident_zero(self):
        model = ComponentTransfer(names=("source",), theta=[0.5],
                                  source="k562").fit(self.source)
        pred = model.predict("NOPE")
        self.assertEqual(pred.support, 0)
        self.assertFalse(pred.observed.any())

    def test_an_unobserved_gene_stays_unobserved(self):
        model = ComponentTransfer(names=("source",), theta=[0.5],
                                  source="k562").fit(self.source)
        pred = model.predict("T1")
        self.assertFalse(bool(pred.observed[2]))
        self.assertTrue(bool(pred.observed[0]))

    def test_expression_component_without_features_is_refused(self):
        model = ComponentTransfer(names=("expression",), theta=[1.0],
                                  source="k562").fit(self.source)
        with self.assertRaises(ValueError):
            model.predict("T1")

    def test_theta_of_the_wrong_length_is_refused(self):
        with self.assertRaises(ValueError):
            ComponentTransfer(names=("common", "specific"), theta=[1.0])


class TestBasalFeatures(unittest.TestCase):
    def test_z_score_covers_expressed_genes_only(self):
        profile = np.array([0.0, 10.0, 100.0, 1000.0, 0.0, 50.0])
        feats = basal_gene_features(profile)
        expressed = feats["detected"]
        np.testing.assert_array_equal(expressed, profile > 0)
        self.assertTrue(np.allclose(feats["expression_z"][~expressed], 0.0))
        z = feats["expression_z"][expressed]
        self.assertAlmostEqual(float(z.mean()), 0.0, places=9)
        self.assertAlmostEqual(float(z.std()), 1.0, places=9)

    def test_a_flat_profile_gives_no_signal_instead_of_dividing_by_zero(self):
        feats = basal_gene_features(np.full(5, 7.0))
        np.testing.assert_allclose(feats["expression_z"], np.zeros(5))

    def test_an_empty_profile_is_not_a_crash(self):
        feats = basal_gene_features(np.zeros(4))
        np.testing.assert_allclose(feats["cpm"], np.zeros(4))
        self.assertFalse(feats["detected"].any())


if __name__ == "__main__":
    unittest.main()
