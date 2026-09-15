"""Contracts for the modular pilot: masks, leakage, save/load, prediction identity.

These tests do not claim that modularity wins. They make the silent failures
loud: zero-filling a missing gene, reading a held-out context, using the trial
alpha in a LOCO fold, leaking an unseen target's response into features, or
writing a model that does not reload to the same prediction.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026.genes import GeneAxis  # noqa: E402
from vcc2026.models import ShrunkTransfer  # noqa: E402
from vcc2026.signatures import Signature, SignatureSet  # noqa: E402
from vcc2026.benchmark.descriptors import DescriptorBank, ControlProfile  # noqa: E402
from vcc2026.benchmark.evaluate import score_matrix, paired_difference  # noqa: E402
from vcc2026.benchmark.models import (  # noqa: E402
    CompactMLP,
    MaskedLowRank,
    ModularFrozen,
    ModularJoint,
    apply_loaded,
    fit_amplitude,
    load_weights,
)
from vcc2026.benchmark.protocol import (  # noqa: E402
    FORBIDDEN_TRIAL_ALPHA,
    TrainArrays,
    assert_no_test_context_in_train,
    assert_unseen_targets_absent,
    make_split,
    reject_forbidden_alpha,
)
from vcc2026.benchmark.universe import (  # noqa: E402
    GeneUniverse,
    assert_no_zero_fill,
    common_measured_universe,
)


N = 8


def tiny_axis(n: int = N) -> GeneAxis:
    return GeneAxis(symbols=tuple(f"G{i}" for i in range(n)))


def patch_axis(axis: GeneAxis):
    import vcc2026.genes as genes
    import vcc2026.models as models
    import vcc2026.signatures as signatures
    import vcc2026.benchmark.descriptors as descriptors
    import vcc2026.benchmark.universe as universe

    if hasattr(genes.official_axis, "cache_clear"):
        genes.official_axis.cache_clear()
    stub = lambda path=None: axis  # noqa: E731
    for mod in (genes, signatures, models, descriptors, universe):
        mod.official_axis = stub
    return axis


def sig(source, context, target, delta, observed, guide="g1", se=None):
    delta = np.asarray(delta, dtype=np.float64)
    observed = np.asarray(observed, dtype=bool)
    se = np.full(delta.shape, 0.1) if se is None else np.asarray(se)
    return Signature(
        source, context, target, delta, se, observed, 50.0, 100.0, guide
    )


class TestUniverseNoZeroFill(unittest.TestCase):
    def setUp(self):
        self.axis = patch_axis(tiny_axis(6))

    def test_intersection_drops_unmeasured_not_zero(self):
        obs_a = np.array([1, 1, 1, 1, 0, 0], dtype=bool)
        obs_b = np.array([1, 1, 0, 0, 1, 1], dtype=bool)
        a = SignatureSet([sig("a", "A", "T1", np.arange(6), obs_a)])
        b = SignatureSet([sig("b", "B", "T1", np.arange(6) + 1, obs_b)])
        uni = common_measured_universe({"a": a, "b": b})
        np.testing.assert_array_equal(uni.observed, [True, True, False, False, False, False])
        self.assertEqual(uni.n_dropped, 4)
        self.assertFalse(uni.as_dict()["zero_fill_missing"])

    def test_svd_on_official_width_is_rejected(self):
        observed = np.array([1, 1, 1, 0, 0, 0], dtype=bool)
        uni = GeneUniverse(observed=observed, per_source_n={"a": 3}, n_official=6)
        Y = np.zeros((4, 6))
        with self.assertRaisesRegex(ValueError, "official-axis width"):
            assert_no_zero_fill(uni, Y)
        assert_no_zero_fill(uni, Y[:, observed])

    def test_zero_fill_across_panels_changes_the_basis(self):
        """Two panels with different support: filling the holes with 0 is not SVD on the overlap."""
        rng = np.random.default_rng(0)
        ya = rng.normal(size=(12, 4))
        yb = rng.normal(size=(12, 4))
        filled = np.zeros((24, 6))
        filled[:12, :4] = ya
        filled[12:, 2:] = yb
        overlap = np.vstack([ya[:, 2:], yb[:, :2]])
        _, _, vt_fill = np.linalg.svd(filled, full_matrices=False)
        _, _, vt_overlap = np.linalg.svd(overlap, full_matrices=False)
        # Overlap lives in columns 2-3 of the filled matrix.
        self.assertFalse(
            np.allclose(np.abs(vt_fill[0, 2:4]), np.abs(vt_overlap[0]), atol=1e-3)
        )


class TestSplitsLeakage(unittest.TestCase):
    def setUp(self):
        self.axis = patch_axis(tiny_axis(4))
        obs = np.ones(4, dtype=bool)
        self.shared = [f"T{i}" for i in range(20)]
        members = []
        for t in self.shared:
            members.append(sig("k562_gwps", "K562", t, np.ones(4), obs, "gA"))
            members.append(sig("k562_gwps", "K562", t, np.ones(4) * 1.1, obs, "gB"))
            members.append(sig("rpe1_essential", "RPE1", t, np.ones(4) * 0.5, obs, "gA"))
        self.sigs = SignatureSet(members)
        self.direction = {
            "id": "k562_to_rpe1",
            "train_context": "K562",
            "test_context": "RPE1",
            "train_sources": ["k562_gwps"],
            "test_source": "rpe1_essential",
            "n_train_contexts": 1,
            "context_dependence_identifiable": False,
            "note": "one training context",
            "internal_dest_source": "k562_essential",
        }

    def test_seen_target_split_shares_targets_not_contexts(self):
        split = make_split(
            protocol="new_context_seen_target", direction=self.direction,
            shared_targets=self.shared, seed=2026,
            unseen_fraction=0.3, inner_val_fraction=0.2,
        )
        self.assertEqual(set(split.train_targets), set(split.test_targets))
        train = self.sigs.filter(source="k562_gwps", targets=set(split.train_targets))
        assert_no_test_context_in_train(train, "RPE1")
        self.assertFalse(split.context_dependence_identifiable)
        self.assertIn("single training context", split.as_dict()["limitation"])

    def test_unseen_target_excludes_from_all_training_responses(self):
        split = make_split(
            protocol="new_context_unseen_target", direction=self.direction,
            shared_targets=self.shared, seed=2026,
            unseen_fraction=0.3, inner_val_fraction=0.2,
        )
        self.assertTrue(set(split.train_targets).isdisjoint(split.test_targets))
        train = self.sigs.filter(source="k562_gwps", targets=set(split.train_targets))
        assert_unseen_targets_absent(train, set(split.test_targets))
        # Guides of a training target all stay in train.
        train_guides = [s.guide_id for s in train if s.target == split.train_targets[0]]
        self.assertGreaterEqual(len(train_guides), 2)

    def test_leaked_test_context_raises(self):
        with self.assertRaises(ValueError):
            assert_no_test_context_in_train(self.sigs, "RPE1")

    def test_leaked_unseen_target_raises(self):
        train = self.sigs.filter(source="k562_gwps")
        with self.assertRaises(ValueError):
            assert_unseen_targets_absent(train, {"T0"})

    def test_inner_val_is_subset_of_train_not_test_unseen(self):
        split = make_split(
            protocol="new_context_unseen_target", direction=self.direction,
            shared_targets=self.shared, seed=1,
            unseen_fraction=0.3, inner_val_fraction=0.2,
        )
        self.assertTrue(set(split.inner_val_targets) <= set(split.train_targets))
        self.assertTrue(set(split.inner_val_targets).isdisjoint(split.test_targets))


class TestForbiddenAlpha(unittest.TestCase):
    def test_trial_alpha_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "trial value"):
            reject_forbidden_alpha(FORBIDDEN_TRIAL_ALPHA)
        with self.assertRaisesRegex(ValueError, "trial value"):
            reject_forbidden_alpha(0.1974)

    def test_predetermined_one_is_allowed(self):
        reject_forbidden_alpha(1.0)
        reject_forbidden_alpha(0.25)

    def test_amplitude_helper_never_emits_trial_alpha(self):
        rng = np.random.default_rng(0)
        pred = rng.normal(size=(10, 5))
        # Construct a truth whose LS alpha would be exactly 0.1974.
        truth = 0.1974 * pred
        with self.assertRaises(ValueError):
            fit_amplitude(
                pred, truth, predetermined=1.0, forbidden=0.1974, has_internal=True
            )


class TestDescriptorProvenance(unittest.TestCase):
    def setUp(self):
        self.axis = patch_axis(tiny_axis(6))
        observed = np.array([1, 1, 1, 1, 1, 0], dtype=bool)
        uni = GeneUniverse(observed=observed, per_source_n={"a": 5}, n_official=6)
        prof = ControlProfile(
            context="K562", source_id="k562_gwps",
            log1p_cpm=np.linspace(0, 2, 6), observed=observed,
            n_cells=100, library=1e6,
            provenance="test NTC",
        )
        codes = {"T1": np.array([1.0, -1.0])}
        self.bank = DescriptorBank(
            universe=uni,
            context_profiles={"K562": prof, "RPE1": prof},
            train_contexts=("K562",),
            high_expr=np.array([0, 1, 2]),
            target_index={"G0": 0, "T1": 1},
            codes_by_target=codes,
            code_dim=2,
            include_context=True,
            include_response_codes=True,
        )
        self.bank.build_specs()

    def test_response_codes_are_marked_and_dropped_for_unseen(self):
        specs = [s for s in self.bank.specs if s.derived_from_perturbative_response]
        self.assertTrue(specs)
        self.assertTrue(all(not s.allowed_in_unseen_target for s in specs))
        X_seen = self.bank.transform(["T1"], "RPE1", allow_response_codes=True)
        X_unseen = self.bank.transform(["T1"], "RPE1", allow_response_codes=False)
        # Last two columns are the codes.
        np.testing.assert_array_equal(X_seen[0, -2:], [1.0, -1.0])
        np.testing.assert_array_equal(X_unseen[0, -2:], [0.0, 0.0])

    def test_without_context_has_fewer_columns(self):
        self.bank.include_context = False
        self.bank.build_specs()
        n_no = len(self.bank.names)
        self.bank.include_context = True
        self.bank.build_specs()
        self.assertGreater(len(self.bank.names), n_no)

    def test_single_context_is_not_identifiable(self):
        self.assertEqual(self.bank.n_unique_context_vectors(), 1)
        self.assertFalse(self.bank.as_dict()["context_dependence_identifiable"])


class TestSaveLoadAndMasks(unittest.TestCase):
    def setUp(self):
        self.axis = patch_axis(tiny_axis(6))
        self.uni = GeneUniverse(
            observed=np.array([1, 1, 1, 1, 0, 0], dtype=bool),
            per_source_n={"a": 4}, n_official=6,
        )
        rng = np.random.default_rng(2026)
        self.X = rng.normal(size=(30, 5))
        basis = rng.normal(size=(3, 4))
        z = rng.normal(size=(30, 3))
        self.Y = z @ basis
        self.arrays = TrainArrays(
            X=self.X, Y=self.Y,
            targets=tuple(f"T{i}" for i in range(30)),
            feature_names=tuple(f"f{i}" for i in range(5)),
            feature_specs=(),
            uses_context_features=True,
            n_unique_context_rows=1,
        )

    def _roundtrip(self, model):
        model.fit(self.arrays, self.uni)
        pred = model.predict_delta(self.X[:5])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.npz"
            model.save(path)
            payload = load_weights(path)
            clone = object.__new__(type(model))
            apply_loaded(clone, payload, self.uni)
            pred2 = clone.predict_delta(self.X[:5])
        np.testing.assert_allclose(pred, pred2, atol=1e-7, rtol=1e-6)
        self.assertEqual(pred.shape[1], self.uni.n_kept)

    def test_lowrank_roundtrip(self):
        self._roundtrip(MaskedLowRank(rank=3, ridge=1.0))

    def test_mlp_roundtrip(self):
        self._roundtrip(CompactMLP(hidden=4, epochs=4, patience=4, batch=8, seed=1))

    def test_modular_frozen_roundtrip(self):
        self._roundtrip(ModularFrozen(rank=3, hidden=4, epochs=4, patience=4, batch=8, seed=1))

    def test_modular_joint_roundtrip(self):
        self._roundtrip(ModularJoint(
            rank=3, hidden=4, epochs=3, patience=3, batch=8, seed=1,
            joint_epochs=2, joint_lr=0.01,
        ))

    def test_lowrank_refuses_zero_filled_y(self):
        bad = TrainArrays(
            X=self.X, Y=np.concatenate([self.Y, np.zeros((30, 2))], axis=1),
            targets=self.arrays.targets, feature_names=self.arrays.feature_names,
            feature_specs=(), uses_context_features=True, n_unique_context_rows=1,
        )
        with self.assertRaisesRegex(ValueError, "official-axis width"):
            MaskedLowRank(rank=2).fit(bad, self.uni)

    def test_same_seed_same_mlp_prediction(self):
        a = CompactMLP(hidden=4, epochs=5, patience=5, batch=8, seed=7)
        b = CompactMLP(hidden=4, epochs=5, patience=5, batch=8, seed=7)
        a.fit(self.arrays, self.uni)
        b.fit(self.arrays, self.uni)
        np.testing.assert_allclose(
            a.predict_delta(self.X[:3]), b.predict_delta(self.X[:3]), atol=1e-8
        )


class TestShrunkTransferUnknownTarget(unittest.TestCase):
    def setUp(self):
        self.axis = patch_axis(tiny_axis(4))
        obs = np.ones(4, dtype=bool)
        self.train = SignatureSet([
            sig("k562_gwps", "K562", "T1", np.array([1.0, -1.0, 0.5, 0.0]), obs),
        ])

    def test_unseen_target_is_unsupported(self):
        pred = ShrunkTransfer(source="k562_gwps").fit(self.train).predict("UNSEEN")
        self.assertEqual(pred.support, 0)
        self.assertFalse(pred.observed.any())


class TestProxyScoring(unittest.TestCase):
    def test_null_has_mse_vs_null_one(self):
        truth = np.array([[1.0, -2.0, 0.5], [0.5, 0.5, -1.0]])
        pred = np.zeros_like(truth)
        out = score_matrix(pred, truth, targets=["A", "B"], strong_threshold=0.5)
        self.assertAlmostEqual(out["pooled_mse_vs_null"], 1.0)
        self.assertTrue(out["not_a_vcc_score"])

    def test_paired_difference_detects_a_shift(self):
        per_a = [{"target": f"T{i}", "mse_vs_null": 0.8} for i in range(20)]
        per_b = [{"target": f"T{i}", "mse_vs_null": 1.0} for i in range(20)]
        d = paired_difference(per_a, per_b, key="mse_vs_null", n_boot=50, seed=1)
        self.assertTrue(d["ci95_excludes_zero"])
        self.assertAlmostEqual(d["mean_a_minus_b"], -0.2, places=6)


class TestConfigForbidsTrialAlpha(unittest.TestCase):
    def test_shipped_config_does_not_use_trial_alpha(self):
        from vcc2026.benchmark.protocol import load_yaml_config

        cfg = load_yaml_config(REPO / "configs" / "benchmark.yaml")
        self.assertNotAlmostEqual(
            float(cfg["amplitude"]["predetermined_alpha"]), 0.1974
        )
        self.assertAlmostEqual(
            float(cfg["amplitude"]["forbidden_trial_alpha"]), 0.1974
        )
        self.assertIsNone(cfg["non_inferiority_margin"])
        self.assertFalse(cfg["zero_fill_missing"])
        self.assertEqual(cfg["gene_universe"], "intersection_measured")
        self.assertFalse(cfg["generator_x_predictor"]["execute_six_metrics"])

    def test_svd_and_rank_configs_keep_the_same_bans(self):
        from vcc2026.benchmark.protocol import load_yaml_config

        for name in (
            "benchmark_svd_exact.yaml",
            "benchmark_svd_randomized.yaml",
            "benchmark_rank.yaml",
        ):
            cfg = load_yaml_config(REPO / "configs" / name)
            self.assertAlmostEqual(
                float(cfg["amplitude"]["forbidden_trial_alpha"]), 0.1974, msg=name
            )
            self.assertNotAlmostEqual(
                float(cfg["amplitude"]["predetermined_alpha"]), 0.1974, msg=name
            )
            self.assertIsNone(cfg["non_inferiority_margin"], msg=name)
            self.assertFalse(cfg["zero_fill_missing"], msg=name)
            self.assertFalse(cfg.get("descriptors", {}).get("include_go_slim", False), msg=name)


if __name__ == "__main__":
    unittest.main()


class TestThreeContextTraining(unittest.TestCase):
    """What a second training context changes, and what it does not.

    With one training context the context block of the design matrix is a
    constant column: a with-context arm and a without-context arm differ by
    columns that carry no information, and any difference between them is noise.
    These check that the second context actually varies, that a target's two
    rows both survive the split, and that combining two sources does not hand
    one cell line two votes.
    """

    def setUp(self):
        self.axis = patch_axis(tiny_axis(6))
        observed = np.array([1, 1, 1, 1, 1, 0], dtype=bool)
        self.uni = GeneUniverse(observed=observed, per_source_n={"a": 5}, n_official=6)
        self.k562 = ControlProfile(
            context="K562", source_id="k562_gwps",
            log1p_cpm=np.linspace(0.0, 2.0, 6), observed=observed,
            n_cells=100, library=1e6, provenance="test NTC K562",
        )
        self.rpe1 = ControlProfile(
            context="RPE1", source_id="rpe1_essential",
            log1p_cpm=np.linspace(2.0, 0.0, 6), observed=observed,
            n_cells=250, library=3e6, provenance="test NTC RPE1",
        )

    def bank(self, contexts):
        from vcc2026.benchmark.descriptors import fit_descriptor_bank

        return fit_descriptor_bank(
            universe=self.uni,
            profiles={"K562": self.k562, "RPE1": self.rpe1},
            train_contexts=contexts,
            train_sigs=SignatureSet(),
            codes_by_target=None,
            include_context=True,
            include_response_codes=False,
            n_high_expr=3,
        )

    def test_two_training_contexts_make_the_descriptor_vary(self):
        one = self.bank(("K562",))
        two = self.bank(("K562", "RPE1"))
        self.assertEqual(one.n_unique_context_vectors(), 1)
        self.assertFalse(one.as_dict()["context_dependence_identifiable"])
        self.assertEqual(two.n_unique_context_vectors(), 2)
        self.assertTrue(two.as_dict()["context_dependence_identifiable"])

    def test_each_row_carries_its_own_context(self):
        bank = self.bank(("K562", "RPE1"))
        rows = bank.transform_rows(
            [("T1", "K562"), ("T1", "RPE1")], allow_response_codes=False
        )
        self.assertEqual(rows.shape[0], 2)
        self.assertFalse(np.allclose(rows[0], rows[1]),
                         "two contexts produced the same descriptor row")
        # and the single-context call is still the old behaviour
        same = bank.transform(["T1", "T1"], "K562", allow_response_codes=False)
        np.testing.assert_allclose(same[0], same[1])

    def test_a_target_keeps_every_row_in_the_split(self):
        from vcc2026.benchmark.run import _index_of, _rows_of

        row_targets = ["A", "B", "A", "B"]          # two contexts, two targets
        self.assertEqual(sorted(_rows_of(row_targets, ["A"])), [0, 2])
        # the target-keyed index keeps one row per target: that is what
        # `_rows_of` exists to replace when training spans contexts
        self.assertEqual(_index_of(row_targets, ["A"]), [2])

    def test_one_cell_line_does_not_get_two_votes(self):
        from vcc2026.benchmark.models import context_equal_weights

        weights = context_equal_weights(
            {"K562": ["k562_gwps", "k562_essential"], "RPE1": ["rpe1_essential"]}
        )
        self.assertAlmostEqual(weights["k562_gwps"], 0.5)
        self.assertAlmostEqual(weights["k562_essential"], 0.5)
        self.assertAlmostEqual(weights["rpe1_essential"], 1.0)
        self.assertAlmostEqual(
            weights["k562_gwps"] + weights["k562_essential"],
            weights["rpe1_essential"],
            msg="a context with two datasets must not outweigh one with a single dataset",
        )

    def test_multi_source_transfer_refuses_the_trial_alpha(self):
        from vcc2026.benchmark.models import select_multi_source_transfer

        train = SignatureSet([
            sig("k562_gwps", "K562", "T1", [1.0] * 6, [1] * 5 + [0]),
            sig("rpe1_essential", "RPE1", "T1", [0.5] * 6, [1] * 5 + [0]),
        ])
        with self.assertRaises(ValueError):
            select_multi_source_transfer(
                train,
                sources_by_context={"K562": ["k562_gwps"], "RPE1": ["rpe1_essential"]},
                inner_dest_context=None,
                inner_val_targets=(),
                prior_sd_grid=[1.0],
                predetermined_alpha=FORBIDDEN_TRIAL_ALPHA,
                forbidden_alpha=FORBIDDEN_TRIAL_ALPHA,
            )

    def test_the_three_context_config_holds_the_two_k562_datasets_together(self):
        import yaml

        cfg = yaml.safe_load(
            (REPO / "configs" / "benchmark_3ctx.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["amplitude"]["forbidden_trial_alpha"], FORBIDDEN_TRIAL_ALPHA)
        self.assertNotEqual(cfg["amplitude"]["predetermined_alpha"], FORBIDDEN_TRIAL_ALPHA)
        self.assertIsNone(cfg["non_inferiority_margin"])
        self.assertFalse(cfg["zero_fill_missing"])
        used = set(cfg["signatures"]["sources"])
        self.assertNotIn("k562_essential", used,
                         "k562_essential is excluded so the two K562 datasets cannot "
                         "land on opposite sides of a split")
        for direction in cfg["directions"]:
            sides = set(direction["train_sources"]) | {direction["test_source"]}
            self.assertNotIn("k562_essential", sides)
            self.assertEqual(direction["n_train_contexts"], 2)
            self.assertNotIn(direction["test_source"], direction["train_sources"])

    def test_the_amplitude_label_follows_the_pair_it_was_fitted_on(self):
        """A label is a claim, and this one was hard-coded.

        While the only internal pair available was K562 genome-wide against K562
        essential, `internal_same_line_limited` was true of every fit. With a
        third context a fold can calibrate between two different biological
        contexts, and the same string then travels into the comparison table
        asserting something nobody checked.
        """
        from vcc2026.benchmark.models import fit_amplitude

        pred = np.array([[1.0, 2.0], [3.0, 4.0]])
        truth = pred * 0.5
        same = fit_amplitude(pred, truth, predetermined=1.0,
                             forbidden=FORBIDDEN_TRIAL_ALPHA, has_internal=True)
        cross = fit_amplitude(pred, truth, predetermined=1.0,
                              forbidden=FORBIDDEN_TRIAL_ALPHA, has_internal=True,
                              label="cross_context_within_training")
        self.assertEqual(same["label"], "internal_same_line_limited")
        self.assertTrue(same["not_cross_context_calibration"])
        self.assertEqual(cross["label"], "cross_context_within_training")
        self.assertFalse(cross["not_cross_context_calibration"])
        self.assertAlmostEqual(same["alpha"], cross["alpha"],
                               msg="the label must not change the number")
        # and with no pair at all it stays predetermined whatever the label says
        none = fit_amplitude(pred[:0], truth[:0], predetermined=1.0,
                             forbidden=FORBIDDEN_TRIAL_ALPHA, has_internal=False,
                             label="cross_context_within_training")
        self.assertEqual(none["label"], "predetermined_heuristic")

    def test_a_perturbed_context_is_not_defined_by_its_file_format(self):
        """«Contesto perturbato locale» was a count of pseudobulk files.

        True while every perturbed source was a Replogle-style pseudobulk, and
        false the moment a single-cell perturbation source landed on disk: HepG2
        was present, enabled and missing from the list, so the inventory kept
        reporting two perturbed contexts while three were usable.
        """
        from vcc2026.benchmark.inventory import build_inventory

        inventory = build_inventory(include_target_lists=False)
        contexts = set(inventory["perturbed_contexts_local"])
        kinds = {s["id"]: s["matrix_kind"] for s in inventory["sources"]}
        states = {s["id"]: (s.get("cell_state") or "") for s in inventory["sources"]}
        for source in inventory["sources"]:
            on_disk = source["file"]["exists"]
            perturbed = states[source["id"]] != "unperturbed"
            usable_kind = kinds[source["id"]] in ("pseudobulk_mean", "single_cell_counts")
            if on_disk and perturbed and usable_kind:
                self.assertIn(source["context"], contexts,
                              f"{source['id']} is on disk and perturbed but its context "
                              f"is not counted")
        # the unperturbed official controls are never a perturbed context
        for source in inventory["sources"]:
            if states[source["id"]] == "unperturbed" and source["file"]["exists"]:
                self.assertNotIn(source["context"], contexts - {"K562", "RPE1", "HepG2"})


class TestGoSlimDescriptors(unittest.TestCase):
    """The five checks docs/ENCODER_INPUTS.md section 7 asks for, plus the leak.

    The GO slim block is the one descriptor extension that is legal for a target
    excluded from every training response, and that legality is a property of
    where the numbers come from -- not of the column names. These fail loudly if
    the join silently stops resolving, if a missing annotation starts reading as
    «annotated, none apply», or if a response-derived column reaches mode B.
    """

    TABLE = Path(r"C:/Users/ferra/vcc2026-data/artifacts/g001/go_slim_table.npz")

    def setUp(self):
        if not self.TABLE.exists():
            self.skipTest("go_slim_table.npz not built on this machine")
        from vcc2026.benchmark.descriptors import load_go_slim_table

        self.load = load_go_slim_table
        self.table = load_go_slim_table(self.TABLE)

    def test_an_alias_resolves_to_the_approved_gene(self):
        """TMEM104 is the panel's symbol; HGNC calls the gene SLC38A12."""
        import csv

        resolution = self.TABLE.parent / "go_slim_resolution.csv"
        rows = {r["symbol"]: r for r in
                csv.DictReader(resolution.open(encoding="utf-8"))}
        self.assertIn("TMEM104", rows)
        self.assertEqual(rows["TMEM104"]["how"], "alias->SLC38A12")
        self.assertEqual(int(rows["TMEM104"]["n_uniprot"]), 1,
                         "the alias must reach exactly one UniProt accession")
        self.assertGreater(int(rows["TMEM104"]["n_go_direct"]), 0,
                           "the GAF lookup must find annotations through the alias")

    def test_a_gene_without_slim_is_missing_not_all_zero(self):
        vector = self.table.vector("TMEM104")
        self.assertEqual(vector[-1], 1.0, "missing indicator must be set")
        self.assertEqual(float(vector[:-1].sum()), 0.0)
        # and a gene that does have annotation is the other way round
        annotated = self.table.vector("MYC")
        self.assertEqual(annotated[-1], 0.0)
        self.assertGreater(float(annotated[:-1].sum()), 0.0)

    def test_an_unknown_symbol_is_missing_not_silently_zero(self):
        vector = self.table.vector("NOT_A_GENE_SYMBOL")
        self.assertEqual(vector[-1], 1.0)
        self.assertEqual(float(vector[:-1].sum()), 0.0)

    def test_the_permutation_is_deterministic_and_actually_permutes(self):
        a = self.load(self.TABLE, permutation_seed=20260915)
        b = self.load(self.TABLE, permutation_seed=20260915)
        c = self.load(self.TABLE, permutation_seed=20260916)
        self.assertTrue(a.permuted)
        np.testing.assert_array_equal(a.vector("MYC"), b.vector("MYC"))
        moved = sum(
            1 for s in self.table.symbols[:500]
            if not np.array_equal(a.vector(s), self.table.vector(s))
        )
        self.assertGreater(moved, 100, "a permutation that moves almost nothing is not one")
        self.assertFalse(np.array_equal(a.vector("MYC"), c.vector("MYC")))

    def test_go_columns_are_declared_legal_for_an_unseen_target(self):
        from vcc2026.benchmark.descriptors import ControlProfile, fit_descriptor_bank

        axis = patch_axis(tiny_axis(6))
        observed = np.array([1, 1, 1, 1, 1, 0], dtype=bool)
        uni = GeneUniverse(observed=observed, per_source_n={"a": 5}, n_official=6)
        profile = ControlProfile(
            context="K562", source_id="k562_gwps", log1p_cpm=np.linspace(0, 2, 6),
            observed=observed, n_cells=100, library=1e6, provenance="test NTC",
        )
        bank = fit_descriptor_bank(
            universe=uni, profiles={"K562": profile}, train_contexts=("K562",),
            train_sigs=SignatureSet(), codes_by_target=None,
            include_context=True, include_response_codes=False, n_high_expr=3,
            go_slim=self.table, include_go_slim=True,
        )
        go_specs = [s for s in bank.specs if s.name.startswith("go_slim")]
        self.assertEqual(len(go_specs), self.table.n_terms + 1)
        for spec in go_specs:
            self.assertFalse(spec.derived_from_perturbative_response,
                             f"{spec.name} claims to come from a response")
            self.assertTrue(spec.allowed_in_unseen_target)
            self.assertFalse(spec.uses_query_ntc)
        # the columns are really there, and in the declared order
        X = bank.transform(["MYC"], "K562", allow_response_codes=False)
        self.assertEqual(X.shape[1], len(bank.names))
        first_go = next(i for i, n in enumerate(bank.names) if n.startswith("go_slim_GO"))
        np.testing.assert_array_equal(
            X[0, first_go:first_go + self.table.n_terms + 1], self.table.vector("MYC")
        )

    def test_the_pilot_config_keeps_the_permuted_control_and_the_decision_rule(self):
        import yaml

        cfg = yaml.safe_load(
            (REPO / "configs" / "benchmark_go_slim.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["protocols"], ["new_context_unseen_target"],
                         "mode B lives on the unseen-target protocol")
        variants = cfg["descriptor_variants"]
        self.assertTrue(variants["B3"]["permute_go_slim"])
        self.assertIsInstance(variants["B3"]["permutation_seed"], int)
        self.assertFalse(variants["B0"]["include_go_slim"])
        self.assertTrue(cfg["decision_rule"]["fixed_before_the_run"])
        self.assertIsNone(cfg["non_inferiority_margin"])
        self.assertFalse(cfg["zero_fill_missing"])
        # every comparison the rule needs is declared, not inferred later
        labels = {p["label"] for p in cfg["paired_comparisons"]}
        self.assertIn("go_slim_vs_basal", labels)
        self.assertIn("permuted_go_vs_real_go", labels)
        arms = {f"{a['model']}__{a['variant']}" for a in cfg["arms"]}
        for pair in cfg["paired_comparisons"]:
            self.assertIn(pair["a"], arms)
            self.assertIn(pair["b"], arms)
