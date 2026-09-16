"""Contracts for the expression gate: the ways it could be wrong in silence.

Nothing here claims the gate helps. These make the silent failures loud: a gate
acting where there is no measurement, a permuted control that is not a permutation,
a selection that reads the context it is about to be tested on, a "gate" that is
really a step function, a base that is not the arm it claims to extend, and a
decision rule that would promote on a missing comparison.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.genes import GeneAxis  # noqa: E402
from vcc2026.models import WeightedTransfer  # noqa: E402
from vcc2026.presence import (  # noqa: E402
    GenePresence,
    combine_log10_presence,
    gate_output,
    gate_rows,
    logistic_weight,
    permute_among,
    presence_summary,
)
from vcc2026.signatures import Signature, SignatureSet  # noqa: E402
from vcc2026.benchmark.descriptors import ControlProfile  # noqa: E402
from vcc2026.benchmark.gate import (  # noqa: E402
    GateArm,
    GateCandidate,
    apply_gate,
    candidate_grid,
    evaluate_decision,
    gate_arms_from_config,
    internal_pair,
    presence_vector,
    run_gate_arm,
    select_gate,
    select_on_internal_pair,
    target_log10,
)
from vcc2026.benchmark.protocol import make_split  # noqa: E402
from vcc2026.benchmark.universe import GeneUniverse  # noqa: E402

N_GENES = 12
TARGETS = tuple(f"G{i}" for i in range(N_GENES))


def tiny_axis(n: int = N_GENES) -> GeneAxis:
    return GeneAxis(symbols=tuple(f"G{i}" for i in range(n)))


def patch_axis(axis: GeneAxis) -> GeneAxis:
    import vcc2026.genes as genes
    import vcc2026.models as models
    import vcc2026.signatures as signatures
    import vcc2026.benchmark.descriptors as descriptors
    import vcc2026.benchmark.gate as gate
    import vcc2026.benchmark.universe as universe

    if hasattr(genes.official_axis, "cache_clear"):
        genes.official_axis.cache_clear()
    stub = lambda path=None: axis  # noqa: E731
    for mod in (genes, signatures, models, descriptors, universe, gate):
        mod.official_axis = stub
    return axis


def profile(context: str, source_id: str, cpm: np.ndarray, observed=None) -> ControlProfile:
    cpm = np.asarray(cpm, dtype=np.float64)
    observed = np.ones(cpm.shape, dtype=bool) if observed is None else np.asarray(observed, bool)
    return ControlProfile(
        context=context, source_id=source_id,
        log1p_cpm=np.log1p(np.where(observed, cpm, 0.0)), observed=observed,
        n_cells=5000.0, library=1e8, provenance=f"test NTC {context}",
    )


def sig(source, context, target, delta, se=0.1, observed=None) -> Signature:
    delta = np.asarray(delta, dtype=np.float64)
    observed = np.ones(delta.shape, bool) if observed is None else np.asarray(observed, bool)
    return Signature(source, context, target, delta, np.full(delta.shape, se),
                     observed, 50.0, 100.0, "g1")


class TestPresenceQuantity(unittest.TestCase):
    """An unmeasured gene and a gene measured at zero are not the same thing."""

    def setUp(self):
        self.axis = patch_axis(tiny_axis())

    def test_unmeasured_is_nan_and_measured_zero_is_zero(self):
        cpm = np.zeros(N_GENES)
        cpm[0] = 500.0
        observed = np.ones(N_GENES, bool)
        observed[-1] = False
        p = GenePresence.from_control_profile(profile("K562", "k562_gwps", cpm, observed))
        self.assertTrue(np.isnan(p.cpm[-1]))
        self.assertEqual(p.cpm[1], 0.0)
        self.assertAlmostEqual(p.cpm[0], 500.0, places=6)
        self.assertEqual(int(p.measured.sum()), N_GENES - 1)

    def test_basal_profile_of_an_official_control_file_becomes_cpm(self):
        from vcc2026.inference import BasalProfile

        counts = np.arange(1, N_GENES + 1, dtype=np.float64)
        basal = BasalProfile(
            context="A", profile=counts, library_sizes=np.full(3, 10),
            n_cells=3, nnz_per_cell=np.full(3, 5), source_path="test",
        )
        p = GenePresence.from_basal_profile(basal)
        self.assertAlmostEqual(float(p.cpm.sum()), 1e6, places=3)
        self.assertTrue(np.all(p.measured))

    def test_log10_needs_a_positive_pseudocount(self):
        p = GenePresence.from_control_profile(profile("K562", "s", np.ones(N_GENES)))
        with self.assertRaises(ValueError):
            p.log10_cpm(0.0)

    def test_combining_contexts_ignores_the_unmeasured_one(self):
        a = np.array([1.0, np.nan, 2.0])
        b = np.array([3.0, 4.0, np.nan])
        out = combine_log10_presence([a, b])
        self.assertAlmostEqual(out[0], 2.0)
        self.assertAlmostEqual(out[1], 4.0)
        self.assertAlmostEqual(out[2], 2.0)

    def test_summary_counts_below_thresholds(self):
        cpm = np.array([0.0, 0.5, 4.0, 20.0, np.nan])
        out = presence_summary(cpm, thresholds=(1.0, 5.0))
        self.assertEqual(out["n_measured"], 4)
        self.assertEqual(out["n_unmeasured"], 1)
        self.assertEqual(out["n_below_cpm"]["1.0"], 2)
        self.assertEqual(out["n_below_cpm"]["5.0"], 3)


class TestWeightIsGradedNotAThreshold(unittest.TestCase):
    def test_half_at_the_midpoint_and_monotone(self):
        x = np.log10(np.array([0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]) + 0.01)
        w = logistic_weight(x, midpoint_cpm=10.0, slope_per_decade=2.0)
        self.assertTrue(np.all(np.diff(w) > 0))
        mid = logistic_weight(np.log10(np.array([10.0])), midpoint_cpm=10.0,
                              slope_per_decade=2.0)
        self.assertAlmostEqual(float(mid[0]), 0.5, places=6)
        self.assertLess(w[0], 0.02)
        self.assertGreater(w[-1], 0.98)

    def test_no_step_anywhere_on_the_shipped_grid(self):
        x = np.linspace(-2.0, 3.0, 501)
        for slope in (2.0, 4.0):
            w = logistic_weight(x, midpoint_cpm=10.0, slope_per_decade=slope)
            self.assertLess(float(np.max(np.abs(np.diff(w)))), 0.05,
                            msg=f"slope {slope} behaves like a switch")

    def test_unmeasured_presence_never_gates(self):
        w = logistic_weight(np.array([np.nan, -2.0]), midpoint_cpm=10.0,
                            slope_per_decade=4.0)
        self.assertEqual(w[0], 1.0)
        self.assertLess(w[1], 0.001)

    def test_a_gate_that_falls_with_expression_is_refused(self):
        with self.assertRaises(ValueError):
            logistic_weight(np.zeros(3), midpoint_cpm=10.0, slope_per_decade=-2.0)
        with self.assertRaises(ValueError):
            logistic_weight(np.zeros(3), midpoint_cpm=0.0, slope_per_decade=2.0)


class TestGateArithmetic(unittest.TestCase):
    def setUp(self):
        self.delta = np.array([[-2.0, 1.0, -0.5], [0.0, -1.0, 3.0]])

    def test_weight_one_changes_nothing_at_all(self):
        out = gate_output(self.delta, np.ones(3))
        np.testing.assert_array_equal(out, self.delta)

    def test_symmetric_scales_both_signs(self):
        w = np.array([0.0, 0.5, 1.0])
        out = gate_output(self.delta, w, positive_attenuation=1.0)
        np.testing.assert_allclose(out[0], [0.0, 0.5, -0.5])

    def test_asymmetric_leaves_an_increase_intact(self):
        w = np.array([0.0, 0.0, 1.0])
        out = gate_output(self.delta, w, positive_attenuation=0.0)
        self.assertEqual(out[0, 0], 0.0)      # a decrease on an absent gene: gone
        self.assertEqual(out[0, 1], 1.0)      # an increase on an absent gene: kept
        self.assertEqual(out[1, 2], 3.0)

    def test_partial_attenuation_is_between_the_two(self):
        w = np.array([0.0, 0.0, 1.0])
        half = gate_output(self.delta, w, positive_attenuation=0.5)
        self.assertAlmostEqual(half[0, 1], 0.5)
        self.assertAlmostEqual(half[0, 0], 0.0)

    def test_attenuation_outside_the_unit_interval_is_refused(self):
        with self.assertRaises(ValueError):
            gate_output(self.delta, np.ones(3), positive_attenuation=1.5)

    def test_row_gate_scales_a_whole_response(self):
        out = gate_rows(self.delta, np.array([0.25, 1.0]))
        np.testing.assert_allclose(out[0], self.delta[0] * 0.25)
        np.testing.assert_array_equal(out[1], self.delta[1])

    def test_shape_mismatch_is_refused(self):
        with self.assertRaises(ValueError):
            gate_output(self.delta, np.ones(4))
        with self.assertRaises(ValueError):
            gate_rows(self.delta, np.ones(3))


class TestPermutationIsAControl(unittest.TestCase):
    def test_same_seed_same_permutation_and_values_preserved(self):
        values = np.arange(10.0)
        pos = np.arange(4, 10)
        a = permute_among(values, pos, 20260916)
        b = permute_among(values, pos, 20260916)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(np.sort(a[pos]), np.sort(values[pos]))
        np.testing.assert_array_equal(a[:4], values[:4])
        self.assertTrue(np.any(a[pos] != values[pos]), "nothing was permuted")

    def test_distinct_positions_are_required(self):
        with self.assertRaises(ValueError):
            permute_among(np.arange(5.0), np.array([1, 1, 2]), 1)

    def test_target_permutation_reuses_one_map(self):
        axis = patch_axis(tiny_axis())
        position = axis.position()
        values = np.arange(float(N_GENES))
        first = target_log10(values, ["G0", "G1"], position=position,
                             permuted_over=TARGETS, seed=7)
        again = target_log10(values, ["G0", "G1"], position=position,
                             permuted_over=TARGETS, seed=7)
        np.testing.assert_array_equal(first, again)
        plain = target_log10(values, TARGETS, position=position)
        shuffled = target_log10(values, TARGETS, position=position,
                                permuted_over=TARGETS, seed=7)
        np.testing.assert_array_equal(np.sort(shuffled), np.sort(plain))

    def test_a_target_off_the_axis_has_no_presence(self):
        axis = patch_axis(tiny_axis())
        out = target_log10(np.arange(float(N_GENES)), ["NOT_A_GENE"],
                           position=axis.position())
        self.assertTrue(np.isnan(out[0]))


class TestCandidateGrid(unittest.TestCase):
    GRID = {"midpoint_cpm": [1.0, 10.0], "slope_per_decade": [2.0, 4.0],
            "positive_attenuation": [0.0, 0.5], "include_identity": True}

    def test_identity_comes_first_so_a_tie_does_nothing(self):
        grid = candidate_grid("G1", self.GRID)
        self.assertTrue(grid[0].identity)
        self.assertEqual(len(grid), 1 + 4)

    def test_only_the_asymmetric_variant_spends_the_second_parameter(self):
        self.assertEqual(len(candidate_grid("G2", self.GRID)), 1 + 8)
        self.assertEqual({c.positive_attenuation for c in candidate_grid("G1", self.GRID)},
                         {1.0})

    def test_identity_returns_the_prediction_untouched(self):
        pred = np.array([[1.0, -2.0]])
        out = apply_gate(pred, variant="G1", candidate=GateCandidate(),
                         gene_log10=np.array([-5.0, -5.0]), target_log10=None)
        np.testing.assert_array_equal(out, pred)


class TestSelectionUsesTrainingOnly(unittest.TestCase):
    """The gate is chosen on the internal cross-context pair, never on the test."""

    def setUp(self):
        self.axis = patch_axis(tiny_axis())
        self.universe = GeneUniverse(
            observed=np.ones(N_GENES, bool),
            per_source_n={"k562_gwps": N_GENES}, n_official=N_GENES,
        )
        # RPE1 (the internal destination) expresses the first half only.
        self.cpm_rpe1 = np.array([500.0] * 6 + [0.05] * 6)
        self.profiles_train = {
            "K562": profile("K562", "k562_gwps", np.full(N_GENES, 500.0)),
            "RPE1": profile("RPE1", "rpe1_essential", self.cpm_rpe1),
        }
        self.sources_by_context = {"K562": ["k562_gwps"], "RPE1": ["rpe1_essential"]}
        donor = [sig("k562_gwps", "K562", t, np.ones(N_GENES)) for t in TARGETS]
        # Destination truth: the donor's signal survives where RPE1 expresses.
        dest_delta = np.array([1.0] * 6 + [0.0] * 6)
        dest = [sig("rpe1_essential", "RPE1", t, dest_delta) for t in TARGETS]
        self.train = SignatureSet(donor + dest)
        self.calib = {"label": "cross_context_within_training", "alpha": 1.0,
                      "prior_sd": 1e6}

    def select(self, arm, calib=None, val_targets=TARGETS):
        return select_on_internal_pair(
            arm,
            gate_cfg={
                "presence": {"log10_pseudocount_cpm": 0.01},
                "permutation": {"seed": 20260916},
                "grid": {"midpoint_cpm": [1.0, 10.0], "slope_per_decade": [2.0, 4.0],
                         "positive_attenuation": [0.0, 0.5], "include_identity": True},
            },
            train_sigs=self.train,
            train_profiles=self.profiles_train,
            base_calib=calib or self.calib,
            sources_by_context=self.sources_by_context,
            internal_dest_context="RPE1",
            inner_val_targets=val_targets,
            universe=self.universe,
            fold_targets=list(TARGETS),
            position=self.axis.position(),
        )

    def test_a_gate_is_chosen_when_the_destination_does_not_express(self):
        out = self.select(GateArm("gate_G1", "G1", "destination", False))
        self.assertFalse(out["chosen"].identity)
        self.assertIsNone(out["why_identity"])
        self.assertEqual(len(out["val_targets"]), N_GENES)
        best = min(out["grid"], key=lambda r: r["val_mse"])
        self.assertFalse(best["identity"])

    def test_identity_is_chosen_when_gating_can_only_hurt(self):
        # Destination truth equals the donor prediction on every gene: any gate
        # moves the prediction away from it.
        dest = [sig("rpe1_essential", "RPE1", t, np.ones(N_GENES)) for t in TARGETS]
        self.train = SignatureSet(
            [s for s in self.train if s.source == "k562_gwps"] + dest
        )
        out = self.select(GateArm("gate_G1", "G1", "destination", False))
        self.assertTrue(out["chosen"].identity)

    def test_selection_never_reads_the_held_out_context(self):
        # HepG2 is the test context of this fold and is simply not in the map the
        # selection is given: if it were read, this would be a KeyError.
        out = self.select(GateArm("gate_G1", "G1", "destination", False))
        self.assertNotIn("HepG2", self.profiles_train)
        self.assertEqual(out["internal_dest_context"], "RPE1")
        self.assertEqual(out["donor_contexts"], ["K562"])

    def test_a_predetermined_amplitude_falls_back_to_the_identity(self):
        out = self.select(GateArm("gate_G1", "G1", "destination", False),
                          calib={"label": "predetermined_heuristic", "alpha": 1.0,
                                 "prior_sd": 4.0, "why_predetermined": "pair too small"})
        self.assertTrue(out["chosen"].identity)
        self.assertIn("pair too small", out["why_identity"])

    def test_too_few_validation_targets_falls_back_to_the_identity(self):
        out = self.select(GateArm("gate_G1", "G1", "destination", False),
                          val_targets=("G0", "G1"))
        self.assertTrue(out["chosen"].identity)
        self.assertIn("2 validation targets", out["why_identity"])

    def test_the_internal_pair_is_donor_to_destination(self):
        P, D, used = internal_pair(
            self.train, sources_by_context=self.sources_by_context,
            internal_dest_context="RPE1", inner_val_targets=TARGETS,
            prior_sd=1e6, alpha=1.0, universe=self.universe,
        )
        self.assertEqual(len(used), N_GENES)
        np.testing.assert_allclose(P[0], np.ones(N_GENES), atol=1e-6)
        np.testing.assert_allclose(D[0], np.array([1.0] * 6 + [0.0] * 6))

    def test_source_presence_never_uses_the_destination(self):
        with self.assertRaises(ValueError):
            presence_vector(self.profiles_train, role="source", destination="RPE1",
                            sources=["K562", "RPE1"], pseudocount=0.01)

    def test_select_gate_refuses_mismatched_shapes(self):
        with self.assertRaises(ValueError):
            select_gate(np.zeros((2, 3)), np.zeros((2, 4)), variant="G1",
                        candidates=[GateCandidate()], gene_log10=np.zeros(3),
                        target_log10=None)


class TestRunGateArm(unittest.TestCase):
    """One factor varies: the arm is the base transfer times a weight."""

    def setUp(self):
        self.axis = patch_axis(tiny_axis())
        self.universe = GeneUniverse(
            observed=np.ones(N_GENES, bool),
            per_source_n={"k562_gwps": N_GENES}, n_official=N_GENES,
        )
        self.sources_by_context = {"K562": ["k562_gwps"], "RPE1": ["rpe1_essential"]}
        donor = [sig("k562_gwps", "K562", t, np.ones(N_GENES)) for t in TARGETS]
        dest_delta = np.array([1.0] * 6 + [0.0] * 6)
        dest = [sig("rpe1_essential", "RPE1", t, dest_delta) for t in TARGETS]
        self.train = SignatureSet(donor + dest)
        self.profiles = {
            "K562": profile("K562", "k562_gwps", np.full(N_GENES, 500.0)),
            "RPE1": profile("RPE1", "rpe1_essential", np.array([500.0] * 6 + [0.05] * 6)),
            "HepG2": profile("HepG2", "nadig_hepg2", np.array([500.0] * 3 + [0.05] * 9)),
        }
        self.split = make_split(
            protocol="new_context_seen_target",
            direction={
                "id": "k562_rpe1_to_hepg2", "train_context": "K562+RPE1",
                "test_context": "HepG2", "train_sources": ["k562_gwps", "rpe1_essential"],
                "test_source": "nadig_hepg2", "internal_dest_source": "rpe1_essential",
                "n_train_contexts": 2, "context_dependence_identifiable": True,
            },
            shared_targets=list(TARGETS), seed=2026,
            unseen_fraction=0.3, inner_val_fraction=0.2,
        )
        self.base_calib = {"label": "cross_context_within_training", "alpha": 1.0,
                           "prior_sd": 1e6}
        self.base = WeightedTransfer(
            {"k562_gwps": 1.0, "rpe1_essential": 1.0}, alpha=1.0, prior_sd=1e6
        ).fit(self.train)
        self.Y_test = np.tile(np.array([1.0] * 3 + [0.0] * 9), (len(TARGETS), 1))
        self.cfg = {
            "expression_gate": {
                "base_arm": "shrunk_transfer",
                "presence": {"log10_pseudocount_cpm": 0.01},
                "permutation": {"seed": 20260916},
                "grid": {"midpoint_cpm": [1.0, 10.0], "slope_per_decade": [2.0, 4.0],
                         "positive_attenuation": [0.0, 0.5], "include_identity": True},
            },
            "evaluation": {"n_boot": 20, "strong_threshold": 0.5,
                           "save_full_predictions": False},
        }

    def run_arm(self, arm, profiles=None, base_row=None):
        with tempfile.TemporaryDirectory() as tmp:
            return run_gate_arm(
                arm=arm, cfg=self.cfg, split=self.split, universe=self.universe,
                train_sigs=self.train, base_model=self.base, base_calib=self.base_calib,
                sources_by_context=self.sources_by_context,
                internal_dest_context="RPE1",
                inner_val_targets=self.split.inner_val_targets,
                profiles=self.profiles if profiles is None else profiles,
                Y_test=self.Y_test, targets_test=list(self.split.test_targets),
                seed=2026, out_dir=Path(tmp), base_row=base_row,
            )

    def test_the_row_carries_the_gate_it_chose_and_what_it_touched(self):
        row, _ = self.run_arm(GateArm("gate_G1", "G1", "destination", False))
        self.assertEqual(row["model"], "gate_G1")
        self.assertFalse(row["verdict_eligible"])
        self.assertTrue(row["not_a_vcc_score"])
        self.assertEqual(row["calibration_label"], "cross_context_within_training")
        gate = row["gate"]
        self.assertIn("identity_chosen", gate)
        self.assertIn("exposure_on_test", gate)
        self.assertIn("fraction_abs_delta_removed", gate["exposure_on_test"])

    def test_a_disagreeing_base_stops_the_run(self):
        with self.assertRaises(RuntimeError):
            self.run_arm(GateArm("gate_G1", "G1", "destination", False),
                         base_row={"pooled_mse_vs_null": 0.123})

    def test_the_base_row_is_accepted_when_it_matches(self):
        pred = np.vstack([self.universe.slice(self.base.predict(t).delta)
                          for t in self.split.test_targets])
        pooled = float(np.mean(np.square(pred - self.Y_test))
                       / np.mean(np.square(self.Y_test)))
        row, _ = self.run_arm(GateArm("gate_G1", "G1", "destination", False),
                              base_row={"pooled_mse_vs_null": pooled})
        self.assertTrue(row["gate"]["base_check"]["identical"])

    def test_the_source_arm_needs_no_query_controls(self):
        without_query = {k: v for k, v in self.profiles.items() if k != "HepG2"}
        row, _ = self.run_arm(GateArm("gate_G1_src", "G1", "source", False),
                              profiles=without_query)
        self.assertFalse(row["reads_query_context_controls"])
        self.assertFalse(row["uses_context"])

    def test_the_destination_arm_does_read_the_query_controls(self):
        without_query = {k: v for k, v in self.profiles.items() if k != "HepG2"}
        with self.assertRaises(KeyError):
            self.run_arm(GateArm("gate_G1", "G1", "destination", False),
                         profiles=without_query)

    def test_the_target_gate_reports_which_targets_it_compressed(self):
        row, _ = self.run_arm(GateArm("gate_G3", "G3", "destination", False))
        exposure = row["gate"]["exposure_on_test"]
        self.assertIn("n_targets_weight_below_0_5", exposure)
        self.assertEqual(exposure["n_test_targets"], len(self.split.test_targets))

    def test_one_training_context_is_refused(self):
        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp:
                run_gate_arm(
                    arm=GateArm("gate_G1", "G1", "destination", False), cfg=self.cfg,
                    split=self.split, universe=self.universe, train_sigs=self.train,
                    base_model=self.base, base_calib=self.base_calib,
                    sources_by_context={"K562": ["k562_gwps"]},
                    internal_dest_context=None,
                    inner_val_targets=self.split.inner_val_targets,
                    profiles=self.profiles, Y_test=self.Y_test,
                    targets_test=list(self.split.test_targets), seed=2026,
                    out_dir=Path(tmp), base_row=None,
                )

    def test_the_test_context_inside_training_is_refused(self):
        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp:
                run_gate_arm(
                    arm=GateArm("gate_G1", "G1", "destination", False), cfg=self.cfg,
                    split=self.split, universe=self.universe, train_sigs=self.train,
                    base_model=self.base, base_calib=self.base_calib,
                    sources_by_context={"K562": ["k562_gwps"], "HepG2": ["nadig_hepg2"]},
                    internal_dest_context="K562",
                    inner_val_targets=self.split.inner_val_targets,
                    profiles=self.profiles, Y_test=self.Y_test,
                    targets_test=list(self.split.test_targets), seed=2026,
                    out_dir=Path(tmp), base_row=None,
                )


def paired_entry(a, b, mean, excludes, direction="d1", seed=2026,
                 protocol="new_context_seen_target"):
    return {
        "protocol": protocol, "direction_id": direction, "seed": seed,
        "a": a, "b": b,
        "diff": {"mean_a_minus_b": mean, "ci95": [mean - 0.01, mean + 0.01],
                 "ci95_excludes_zero": excludes},
    }


class TestDecisionRule(unittest.TestCase):
    RULE = {
        "protocol": "new_context_seen_target",
        "statistic": "diff",
        "variants": ["gate_G1"],
        "fixed_before_the_run": True,
        "owner_confirmed": False,
        "clauses": [
            {"id": "beats_shrunk_transfer", "a": "{V}", "b": "shrunk_transfer",
             "require": "negative_ci_excludes_zero"},
            {"id": "permuted_does_not_beat", "a": "{V}_perm", "b": "{V}",
             "require": "not_negative_ci_excludes_zero"},
            {"id": "source_measurably_worse", "a": "{V}_src", "b": "{V}",
             "require": "positive_ci_excludes_zero"},
        ],
        "reading_clauses": [
            {"id": "permuted_measurably_worse", "a": "{V}_perm", "b": "{V}",
             "require": "positive_ci_excludes_zero"},
        ],
    }

    def evaluate(self, paired, directions=("d1",), seeds=(2026,)):
        return evaluate_decision(paired, self.RULE, directions=list(directions),
                                 seeds=list(seeds))

    def all_good(self, direction="d1", seed=2026):
        return [
            paired_entry("gate_G1", "shrunk_transfer", -0.05, True, direction, seed),
            paired_entry("gate_G1_perm", "gate_G1", 0.04, True, direction, seed),
            paired_entry("gate_G1_src", "gate_G1", 0.03, True, direction, seed),
        ]

    def test_all_clauses_holding_promotes_to_candidate_not_to_a_winner(self):
        out = self.evaluate(self.all_good())
        self.assertTrue(out["variants"]["gate_G1"]["promoted_to_candidate"])
        self.assertFalse(out["winner_declared"])

    def test_one_split_that_does_not_beat_the_baseline_is_enough_to_stop_it(self):
        paired = self.all_good("d1") + self.all_good("d2")
        paired[3] = paired_entry("gate_G1", "shrunk_transfer", 0.0, False, "d2")
        out = self.evaluate(paired, directions=("d1", "d2"))
        self.assertFalse(out["variants"]["gate_G1"]["promoted_to_candidate"])

    def test_a_permuted_gate_that_wins_stops_it(self):
        paired = self.all_good()
        paired[1] = paired_entry("gate_G1_perm", "gate_G1", -0.02, True)
        out = self.evaluate(paired)
        clause = out["variants"]["gate_G1"]["clauses"][1]
        self.assertFalse(clause["holds"])
        self.assertFalse(out["variants"]["gate_G1"]["promoted_to_candidate"])

    def test_a_permuted_gate_that_ties_still_costs_the_reading(self):
        paired = self.all_good()
        paired[1] = paired_entry("gate_G1_perm", "gate_G1", 0.001, False)
        out = self.evaluate(paired)
        self.assertTrue(out["variants"]["gate_G1"]["promoted_to_candidate"])
        reading = [r for r in out["reading_clauses"]
                   if r["id"] == "permuted_measurably_worse"][0]
        self.assertFalse(reading["holds"])

    def test_a_source_gate_that_does_as_well_stops_it(self):
        paired = self.all_good()
        paired[2] = paired_entry("gate_G1_src", "gate_G1", 0.001, False)
        out = self.evaluate(paired)
        self.assertFalse(out["variants"]["gate_G1"]["promoted_to_candidate"])

    def test_a_missing_comparison_never_promotes(self):
        out = self.evaluate(self.all_good()[:2])
        self.assertFalse(out["variants"]["gate_G1"]["promoted_to_candidate"])
        clause = out["variants"]["gate_G1"]["clauses"][2]
        self.assertEqual(clause["splits"][0]["status"], "missing_or_skipped")

    def test_a_skipped_bootstrap_never_promotes(self):
        paired = self.all_good()
        paired[0] = {"protocol": "new_context_seen_target", "direction_id": "d1",
                     "seed": 2026, "a": "gate_G1", "b": "shrunk_transfer",
                     "diff": {"n": 2, "skipped": "too few paired targets"}}
        out = self.evaluate(paired)
        self.assertFalse(out["variants"]["gate_G1"]["promoted_to_candidate"])


class TestShippedGateConfig(unittest.TestCase):
    """The protocol of the run, read from the file that ran it."""

    @classmethod
    def setUpClass(cls):
        from vcc2026.benchmark.protocol import load_yaml_config

        cls.cfg = load_yaml_config(REPO / "configs" / "benchmark_expression_gate.yaml")

    def test_the_bans_of_every_other_benchmark_config_still_hold(self):
        self.assertAlmostEqual(
            float(self.cfg["amplitude"]["forbidden_trial_alpha"]), 0.1974)
        self.assertNotAlmostEqual(
            float(self.cfg["amplitude"]["predetermined_alpha"]), 0.1974)
        self.assertIsNone(self.cfg["non_inferiority_margin"])
        self.assertFalse(self.cfg["zero_fill_missing"])
        self.assertEqual(self.cfg["gene_universe"], "intersection_measured")
        self.assertFalse(self.cfg["generator_x_predictor"]["execute_six_metrics"])

    def test_development_seeds_only_and_the_confirmation_seed_stays_shut(self):
        self.assertEqual(self.cfg["pilot"]["seeds"], [2026, 2027])
        self.assertNotIn(4242, self.cfg["pilot"]["seeds"])

    def test_the_gate_lives_where_the_base_predicts_something(self):
        self.assertEqual(self.cfg["protocols"], ["new_context_seen_target"])
        self.assertEqual(self.cfg["expression_gate"]["base_arm"], "shrunk_transfer")

    def test_every_variant_carries_both_controls(self):
        arms = gate_arms_from_config(self.cfg["expression_gate"])
        by_name = {a.name: a for a in arms}
        for variant in self.cfg["decision_rule"]["variants"]:
            self.assertIn(variant, by_name)
            self.assertFalse(by_name[variant].permuted)
            self.assertEqual(by_name[variant].presence_from, "destination")
            self.assertTrue(by_name[f"{variant}_perm"].permuted, "C1 missing")
            self.assertEqual(by_name[f"{variant}_src"].presence_from, "source",
                             "C2 missing")

    def test_the_decision_rule_was_fixed_before_the_run_and_says_so(self):
        rule = self.cfg["decision_rule"]
        self.assertTrue(rule["fixed_before_the_run"])
        self.assertIn("owner_confirmed", rule)
        self.assertIn("promoted_means", rule)
        self.assertEqual(rule["missing_or_skipped_comparison"], "fails_the_clause")
        ids = {c["id"] for c in rule["clauses"]}
        self.assertEqual(
            ids, {"beats_shrunk_transfer", "permuted_does_not_beat",
                  "source_measurably_worse"})

    def test_the_declared_comparisons_name_arms_that_will_exist(self):
        names = {a.name for a in gate_arms_from_config(self.cfg["expression_gate"])}
        names |= {"shrunk_transfer"}
        for pair in self.cfg["paired_comparisons"]:
            self.assertIn(pair["a"], names)
            self.assertIn(pair["b"], names)
        for clause in self.cfg["decision_rule"]["clauses"]:
            for variant in self.cfg["decision_rule"]["variants"]:
                self.assertIn(clause["a"].replace("{V}", variant), names)
                self.assertIn(clause["b"].replace("{V}", variant), names)

    def test_the_grid_keeps_the_do_nothing_option_and_no_switches(self):
        grid = self.cfg["expression_gate"]["grid"]
        self.assertTrue(grid["include_identity"])
        self.assertTrue(all(float(m) > 0 for m in grid["midpoint_cpm"]))
        self.assertTrue(all(float(s) > 0 for s in grid["slope_per_decade"]))
        self.assertTrue(all(0.0 <= float(b) < 1.0 for b in grid["positive_attenuation"]),
                        "positive_attenuation 1.0 would make G2 a copy of G1")
        self.assertIsInstance(self.cfg["expression_gate"]["permutation"]["seed"], int)


if __name__ == "__main__":
    unittest.main()
