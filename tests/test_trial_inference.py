"""Tests for the trial pipeline: leakage, context identity, count generation.

Same rule as `test_pipeline_contracts.py` -- every test here corresponds to a
way this stage could produce a confident wrong number instead of an error:

* a parameter selected with help from the targets it is reported on;
* a gene with no evidence drifting away from zero because renormalisation had to
  put the compositional slack somewhere;
* context A's cells shipped under label B, which the official validator cannot
  see and which the FAQ says looks like a weak model rather than a bug;
* counts that are not counts.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.genes import GeneAxis  # noqa: E402
from vcc2026.inference import (  # noqa: E402
    BasalProfile,
    compositional_shift,
    count_generation_diagnostics,
    nearest_basal_context,
    predicted_profile,
    profile_similarity,
    read_basal_profile,
    read_csr_rows,
)
from vcc2026.resources import peak_rss_bytes, require, snapshot  # noqa: E402
from vcc2026.sampling import resample_library_sizes, sample_counts  # noqa: E402
from vcc2026.signatures import Signature, SignatureSet  # noqa: E402
from vcc2026.submission import SubmissionWriter, indptr_dtype  # noqa: E402
from vcc2026.trials import load_trial, trial_ids  # noqa: E402

def patch_axis(axis: GeneAxis):
    import vcc2026.genes as genes
    import vcc2026.models as models
    import vcc2026.signatures as signatures

    if hasattr(genes.official_axis, "cache_clear"):
        genes.official_axis.cache_clear()
    stub = lambda path=None: axis  # noqa: E731
    for mod in (genes, signatures, models):
        mod.official_axis = stub
    return axis


def write_csr_h5ad(path: Path, matrix: sp.csr_matrix, genes, context: str) -> None:
    """A minimal control-shaped h5ad, enough for the readers under test."""
    matrix = matrix.tocsr()
    with h5py.File(path, "w") as f:
        x = f.create_group("X")
        x.attrs["encoding-type"] = "csr_matrix"
        x.attrs["shape"] = np.array(matrix.shape, dtype=np.int64)
        x.create_dataset("data", data=matrix.data.astype(np.float32))
        x.create_dataset("indices", data=matrix.indices.astype(np.int32))
        x.create_dataset("indptr", data=matrix.indptr.astype(np.int32))
        obs = f.create_group("obs")
        ctx = obs.create_group("context")
        ctx.create_dataset(
            "categories",
            data=np.array([context], dtype=object),
            dtype=h5py.special_dtype(vlen=str),
        )
        ctx.create_dataset(
            "codes", data=np.zeros(matrix.shape[0], dtype=np.int8)
        )
        var = f.create_group("var")
        idx = var.create_group("_index")
        idx.create_dataset(
            "values",
            data=np.array(list(genes), dtype=object),
            dtype=h5py.special_dtype(vlen=str),
        )


class TestCompositionalHandling(unittest.TestCase):
    """The unmeasured genes must not move."""

    def setUp(self):
        self.basal = np.array([100.0, 200.0, 50.0, 400.0, 250.0])
        self.observed = np.array([True, True, False, False, True])

    def test_unobserved_genes_realise_exactly_zero_log2fc(self):
        delta = np.array([1.0, 1.5, 9.9, -9.9, 0.5])
        profile, detail = predicted_profile(self.basal, delta, self.observed)
        # Composition share of an unobserved gene must be unchanged.
        share_before = self.basal / self.basal.sum()
        share_after = profile / profile.sum()
        realised = np.log2(share_after / share_before)
        np.testing.assert_allclose(realised[~self.observed], 0.0, atol=1e-12)
        self.assertEqual(detail["realised_log2fc_on_unobserved"], 0.0)

    def test_total_mass_is_preserved(self):
        delta = np.array([2.0, -1.0, 0.0, 0.0, 0.75])
        profile, detail = predicted_profile(self.basal, delta, self.observed)
        self.assertAlmostEqual(profile.sum(), self.basal.sum(), places=8)
        self.assertAlmostEqual(detail["mass_ratio_pred_over_basal"], 1.0, places=10)

    def test_zero_delta_reproduces_the_basal_profile_exactly(self):
        profile, detail = predicted_profile(
            self.basal, np.zeros(5), self.observed
        )
        np.testing.assert_allclose(profile, self.basal, rtol=0, atol=1e-12)
        self.assertEqual(detail["compositional_shift_log2"], 0.0)

    def test_unsupported_target_with_no_observed_gene_is_a_pass_through(self):
        profile, detail = predicted_profile(
            self.basal, np.full(5, 3.0), np.zeros(5, dtype=bool)
        )
        np.testing.assert_allclose(profile, self.basal)
        self.assertEqual(detail["compositional_shift_log2"], 0.0)

    def test_shift_is_closed_form_and_matches_a_numeric_solve(self):
        delta = np.array([1.0, -0.5, 0.0, 0.0, 0.25])
        c = compositional_shift(self.basal, delta, self.observed)

        def residual(x):
            moved = np.where(self.observed, self.basal * np.exp2(delta + x),
                             self.basal)
            return moved.sum() - self.basal.sum()

        self.assertAlmostEqual(residual(c), 0.0, places=6)
        self.assertGreater(residual(c + 0.1), 0.0)
        self.assertLess(residual(c - 0.1), 0.0)

    def test_extreme_delta_is_clipped_and_the_clip_is_reported(self):
        delta = np.array([50.0, 0.0, 0.0, 0.0, 0.0])
        profile, detail = predicted_profile(
            self.basal, delta, self.observed, clip_log2=6.0
        )
        self.assertEqual(detail["n_genes_clipped"], 1)
        self.assertTrue(np.all(np.isfinite(profile)))
        self.assertAlmostEqual(profile.sum(), self.basal.sum(), places=6)

    def test_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            predicted_profile(self.basal, np.zeros(4), self.observed)


class TestCountGeneration(unittest.TestCase):
    """Counts must be counts, and the generator's artefacts must be visible."""

    def setUp(self):
        rng = np.random.default_rng(0)
        self.n_genes = 300
        weights = rng.gamma(0.3, 1.0, self.n_genes)
        self.basal = weights / weights.sum() * 1e6
        self.libs = rng.integers(4000, 6000, 200)
        self.rng = np.random.default_rng(7)

    def _sample(self, profile, **kw):
        return sample_counts(
            profile, self.libs, self.rng,
            max_stored_per_cell=13194, max_counts_per_cell=1_000_000, **kw
        )

    def test_sampled_counts_satisfy_the_submission_rules(self):
        block = self._sample(self.basal)
        self.assertEqual(block.shape, (self.libs.size, self.n_genes))
        self.assertTrue(np.all(block.data >= 0))
        self.assertTrue(np.all(block.data == np.floor(block.data)))
        self.assertTrue(np.all(np.isfinite(block.data)))
        self.assertEqual(int((block.data == 0).sum()), 0)
        self.assertLessEqual(float(np.asarray(block.sum(axis=1)).max()), 1_000_000)

    def test_library_sizes_are_respected_within_poisson_noise(self):
        block = self._sample(self.basal)
        totals = np.asarray(block.sum(axis=1)).ravel()
        self.assertLess(
            abs(totals.mean() - self.libs.mean()) / self.libs.mean(), 0.02
        )

    def test_zero_effect_still_produces_a_measurable_sparsity_artefact(self):
        # Sampling from a pooled mean is not sampling a cell: with no predicted
        # effect at all the generated cells detect MORE genes than real ones,
        # because pooling averages away the cell-to-cell variation that puts
        # zeros in a real cell. Real cells are stood in for by overdispersed
        # draws, which is what makes them sparser than their own mean.
        real = self._sample(self.basal, overdispersion=2.0)
        basal_ref = BasalProfile(
            context="A",
            profile=np.asarray(real.sum(axis=0)).ravel().astype(float),
            library_sizes=np.asarray(real.sum(axis=1)).ravel().astype(np.int64),
            n_cells=real.shape[0],
            nnz_per_cell=np.asarray(real.getnnz(axis=1)),
        )
        generated = self._sample(basal_ref.profile)
        diag = count_generation_diagnostics(generated, basal_ref)
        self.assertIsNotNone(diag["nnz_ratio_generated_over_real"])
        self.assertGreater(diag["nnz_ratio_generated_over_real"], 1.0)
        self.assertIn("median_nnz_real_controls", diag)

    def test_overdispersion_widens_the_spread_it_claims_to(self):
        plain = self._sample(self.basal)
        over = self._sample(self.basal, overdispersion=0.5)
        def cv_of_a_gene(block, col):
            column = np.asarray(block[:, col].todense()).ravel()
            return column.std() / max(column.mean(), 1e-9)
        busiest = int(np.argmax(self.basal))
        self.assertGreater(
            cv_of_a_gene(over, busiest), cv_of_a_gene(plain, busiest)
        )

    def test_resampled_library_sizes_come_from_the_real_distribution(self):
        drawn = resample_library_sizes(self.libs, 500, np.random.default_rng(1))
        self.assertTrue(set(drawn.tolist()) <= set(self.libs.tolist()))


class TestSubmissionWriterOffsets(unittest.TestCase):
    """CSR offsets must not wrap silently on a full-size submission."""

    def test_int32_is_used_while_it_can_represent_the_count(self):
        self.assertEqual(indptr_dtype(0), np.int32)
        self.assertEqual(indptr_dtype(2_087_786_800), np.int32)
        self.assertEqual(indptr_dtype(np.iinfo(np.int32).max), np.int32)

    def test_int64_is_used_once_the_count_exceeds_int32(self):
        # A submission at ~6,000 stored values per cell sits under 3% below the
        # int32 ceiling, so a slightly denser one crosses it. astype(int32) would
        # wrap to negative offsets and still write a file that opens.
        self.assertEqual(indptr_dtype(np.iinfo(np.int32).max + 1), np.int64)
        self.assertEqual(indptr_dtype(2_165_930_900), np.int64)

    def test_the_offset_that_would_wrap_is_representable_in_the_chosen_width(self):
        for nnz in (2_147_483_647, 2_147_483_648, 4_750_000_000):
            dtype = indptr_dtype(nnz)
            self.assertEqual(
                int(np.array([nnz], dtype=dtype)[0]), nnz,
                f"{nnz} is not representable in {dtype}",
            )

    def test_a_written_file_round_trips_with_correct_offsets(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "pred.h5ad"
        genes = [f"G{i}" for i in range(5)]
        block = sp.csr_matrix(np.array([[1.0, 0, 2, 0, 3], [0, 4, 0, 0, 0]]))
        with SubmissionWriter(path, genes) as writer:
            writer.add(block, target_gene="AAA", context="A")
            writer.add(block, target_gene="BBB", context="B")
        with h5py.File(path, "r") as f:
            indptr = f["X/indptr"][:]
            self.assertEqual(int(indptr[-1]), 8)
            self.assertTrue(np.all(np.diff(indptr) >= 0))
            self.assertEqual(list(f["X"].attrs["shape"]), [4, 5])

    def test_a_block_with_a_fractional_count_is_refused(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "bad.h5ad"
        bad = sp.csr_matrix(np.array([[1.5, 0.0]]))
        with self.assertRaises(ValueError):
            with SubmissionWriter(path, ["G0", "G1"]) as writer:
                writer.add(bad, target_gene="AAA", context="A")


class TestContextPreservation(unittest.TestCase):
    """A swapped context label has to be detectable; prep cannot see it."""

    def setUp(self):
        rng = np.random.default_rng(3)
        n = 400
        base = rng.gamma(0.4, 1.0, n)
        self.profiles = {
            "A": base * rng.uniform(0.5, 2.0, n),
            "B": base * rng.uniform(0.5, 2.0, n),
            "C": base * rng.uniform(0.5, 2.0, n),
        }

    def test_correct_label_is_nearest_its_own_basal(self):
        for ctx, prof in self.profiles.items():
            best, scores = nearest_basal_context(prof * 3.0, self.profiles)
            self.assertEqual(best, ctx, f"{ctx} matched {best}: {scores}")

    def test_a_swap_is_detected(self):
        # Ship B's profile under label A: the check must not agree with A.
        best, _ = nearest_basal_context(self.profiles["B"], self.profiles)
        self.assertNotEqual(best, "A")
        self.assertEqual(best, "B")

    def test_similarity_is_depth_invariant(self):
        a = self.profiles["A"]
        self.assertAlmostEqual(
            profile_similarity(a, a * 1000.0), 1.0, places=6
        )

    def test_empty_profile_gives_nan_not_a_false_match(self):
        self.assertTrue(
            np.isnan(profile_similarity(np.zeros(400), self.profiles["A"]))
        )


class TestBasalReaderAndRowReader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        rng = np.random.default_rng(11)
        self.dense = rng.poisson(0.7, size=(40, 12)).astype(np.float32)
        self.matrix = sp.csr_matrix(self.dense)
        self.genes = [f"G{i}" for i in range(12)]
        self.path = self.dir / "ctx.h5ad"
        write_csr_h5ad(self.path, self.matrix, self.genes, "A")

    def tearDown(self):
        self.tmp.cleanup()

    def test_basal_profile_matches_a_dense_computation(self):
        prof = read_basal_profile(self.path, block_rows=7)
        np.testing.assert_allclose(prof.profile, self.dense.sum(axis=0))
        np.testing.assert_array_equal(
            prof.library_sizes, self.dense.sum(axis=1).astype(np.int64)
        )
        np.testing.assert_array_equal(
            prof.nnz_per_cell, (self.dense > 0).sum(axis=1)
        )
        self.assertEqual(prof.context, "A")

    def test_reader_refuses_a_file_with_several_contexts(self):
        # A control file must describe one context; two would mean the basal
        # state is a mixture and every downstream profile would be wrong.
        path = self.dir / "mixed.h5ad"
        write_csr_h5ad(path, self.matrix, self.genes, "A")
        with h5py.File(path, "a") as f:
            del f["obs/context/categories"]
            del f["obs/context/codes"]
            f["obs/context"].create_dataset(
                "categories", data=np.array(["A", "B"], dtype=object),
                dtype=h5py.special_dtype(vlen=str),
            )
            f["obs/context"].create_dataset(
                "codes", data=np.arange(40, dtype=np.int8) % 2
            )
        with self.assertRaises(ValueError):
            read_basal_profile(path)

    def test_row_reader_preserves_order_and_duplicates(self):
        rows = [5, 2, 5, 39, 0, 2]
        block = read_csr_rows(self.path, rows, 12)
        np.testing.assert_allclose(
            np.asarray(block.todense()), self.dense[rows]
        )

    def test_row_reader_handles_an_empty_request(self):
        block = read_csr_rows(self.path, [], 12)
        self.assertEqual(block.shape, (0, 12))


class TestSignatureSubsetLoading(unittest.TestCase):
    """Loading only the targets needed must not change their values."""

    def setUp(self):
        self.axis = patch_axis(GeneAxis(symbols=tuple(f"G{i}" for i in range(6))))
        self.tmp = tempfile.TemporaryDirectory()
        rng = np.random.default_rng(5)
        self.set = SignatureSet()
        for name in ("AAA", "BBB", "CCC"):
            for guide in ("g1", "g2"):
                self.set.add(
                    Signature(
                        source="src", context="K562", target=name,
                        delta=rng.normal(size=6), se=np.full(6, 0.2),
                        observed=np.ones(6, dtype=bool),
                        n_cells=50, n_control_cells=100, guide_id=guide,
                    )
                )
        self.path = Path(self.tmp.name) / "s.npz"
        self.set.write_npz(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_subset_equals_the_matching_rows_of_the_full_load(self):
        full = SignatureSet.read_npz(self.path)
        subset = SignatureSet.read_npz(self.path, targets={"BBB"})
        self.assertEqual(len(subset), 2)
        self.assertEqual(set(subset.targets), {"BBB"})
        expected = [s for s in full if s.target == "BBB"]
        for got, want in zip(subset, expected):
            np.testing.assert_allclose(got.delta, want.delta)
            np.testing.assert_allclose(got.se, want.se)
            self.assertEqual(got.guide_id, want.guide_id)

    def test_unknown_target_yields_an_empty_set_not_an_error(self):
        self.assertEqual(len(SignatureSet.read_npz(self.path, targets={"ZZZ"})), 0)

    def test_collapse_keeps_every_guide_of_a_target_on_one_row(self):
        collapsed = SignatureSet.read_npz(self.path).collapse_guides()
        self.assertEqual(len(collapsed), 3)
        for sig in collapsed:
            self.assertEqual(sig.meta["n_guides"], 2)
            self.assertIsNone(sig.guide_id)


class TestTrialConfig(unittest.TestCase):
    def test_both_trials_are_defined(self):
        self.assertIn("trial-00-controls", trial_ids())
        self.assertIn("trial-01-transfer", trial_ids())

    def test_defaults_merge_under_each_trial(self):
        trial = load_trial("trial-01-transfer")
        self.assertEqual(trial["cells_per_pert"], 400)
        self.assertEqual(trial["contexts"], ["A", "B", "C"])
        self.assertTrue(trial["trains"])

    def test_control_trial_declares_it_is_not_the_official_zero(self):
        trial = load_trial("trial-00-controls")
        self.assertFalse(trial["trains"])
        self.assertTrue(
            any("score-zero" in s or "official 0" in s for s in trial["not_this"]),
            "the control trial must say it is not the official baseline",
        )

    def test_unknown_trial_names_the_known_ones(self):
        with self.assertRaises(KeyError) as ctx:
            load_trial("trial-99-nope")
        self.assertIn("trial-00-controls", str(ctx.exception))


class TestResourceMeasurement(unittest.TestCase):
    def test_snapshot_reports_a_real_filesystem(self):
        snap = snapshot(REPO)
        self.assertGreater(snap.disk_total_bytes, 0)
        self.assertGreaterEqual(snap.disk_free_bytes, 0)
        self.assertIn("disk_free_gib", snap.as_dict())

    def test_peak_rss_is_a_positive_number_or_explicitly_unknown(self):
        peak = peak_rss_bytes()
        if peak is not None:
            self.assertGreater(peak, 1_000_000)

    def test_require_refuses_an_impossible_disk_request(self):
        with self.assertRaises(RuntimeError) as ctx:
            require(disk_bytes=10**15, path=REPO)
        self.assertIn("free", str(ctx.exception))

    def test_require_allows_a_trivial_request(self):
        require(disk_bytes=1024, path=REPO, reserve_bytes=0)


class TestGeneratedArtifactsDeclareTheyAreNotScores(unittest.TestCase):
    """A local artifact must never read as a leaderboard result."""

    def test_trials_config_separates_local_metrics_from_vcc_scores(self):
        text = (REPO / "configs" / "trials.yaml").read_text(encoding="utf-8")
        self.assertIn("not VCC scores", text)


if __name__ == "__main__":
    unittest.main()
