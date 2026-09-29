"""Tests for `vcc2026.multisource`.

Each test pins a way a multi-source transfer could return plausible wrong numbers:

* a donor's knockdown compared with another donor's controls (donor effects leak in);
* a gene with no count in either group read as the ratio of the two totals (the constant
  pseudocount), which made the CD4 Y-chromosome genes look induced by every knockdown;
* a donor dropped for lack of evidence by a rule that looks at the target's own count, which
  selects on the outcome;
* an unmeasured (target, gene) pair counted as a vote for zero;
* centring that subtracts one source's common response from another;
* a sign-purity proxy that reads the truth's ranking instead of the prediction's;
* a top-k sign agreement that ranks by the truth, counts undefined genes, or keeps the
  target gene the scorer drops;
* a shrinkage recomputed from a missing SE, which silently turns a source into zeros;
* a panel file read by column position, which takes a context label for a target;
* a cache built for another panel, which stage 100 turned into a near-empty prediction without an
  error (dress rehearsal of 22 October, defect D4), and a recipe whose contexts are not the bundle's;
* a frozen common response that is not the one ``gamma`` subtracts.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.multisource import (  # noqa: E402
    AxisTable, _purity_depth, eb_components, eb_pool, effects_from_pseudobulk, mix, topk_sign_agreement,
)


def _rows(rng, base, n_cells, scale=1.0):
    lam = base * n_cells * 2000 * scale          # ~2,000 UMI per cell
    return rng.poisson(lam).astype(float)


class PseudobulkEffectTests(unittest.TestCase):
    def test_donor_baselines_cancel_and_the_knockdown_is_found(self):
        rng = np.random.default_rng(0)
        g = 400
        base = rng.gamma(2.0, 1.0, size=g)
        base[7] = 0.01 * base.sum()                 # a well-measured knockdown gene
        base /= base.sum()
        donor_shift = {"d1": np.exp(rng.normal(0, 0.8, g)), "d2": np.exp(rng.normal(0, 0.8, g))}
        rows, meta = [], []
        for d, shift in donor_shift.items():
            prof = base * shift
            prof /= prof.sum()
            for _ in range(20):                     # controls, 20 rows of 100 cells
                rows.append(_rows(rng, prof, 100)); meta.append(("non-targeting", d, 100))
            kd = prof.copy(); kd[7] *= 0.25; kd /= kd.sum()
            for _ in range(2):                      # target rows, only in its own donor mix
                rows.append(_rows(rng, kd, 300)); meta.append(("T1", d, 300))
        obs = pd.DataFrame(meta, columns=["target", "donor", "n_cells"]).assign(condition="Rest")
        src = effects_from_pseudobulk(sp.csr_matrix(np.vstack(rows)), obs, [f"g{i}" for i in range(g)],
                                      targets=["T1", "missing"], condition="Rest")
        self.assertEqual(src.targets, ["T1"])
        self.assertAlmostEqual(float(src.raw[0, 7]), np.log(0.25), delta=0.15)
        others = np.delete(src.raw[0], 7)
        self.assertLess(float(np.median(np.abs(others))), 0.1)   # large donor shifts must cancel

    @staticmethod
    def _groups(counts):
        """Rows (target, donor, gene-0 count, total) -> a two-gene pseudobulk; gene 1 takes the rest."""
        X = np.array([[s, total - s] for _, _, s, total in counts], dtype=float)
        obs = pd.DataFrame([(t, d, 50.0 if t != "non-targeting" else 500.0) for t, d, _, _ in counts],
                           columns=["target", "donor", "n_cells"]).assign(condition="Rest")
        return sp.csr_matrix(X), obs

    def _raw(self, counts, scale="constant", **kw):
        X, obs = self._groups(counts)
        src = effects_from_pseudobulk(X, obs, ["g0", "g1"], targets=["T1"], condition="Rest", pseudo_scale=scale, **kw)
        return float(src.raw[0, 0])

    def test_a_donor_without_evidence_is_dropped_gene_by_gene(self):
        counts = [("T1", "d1", 20, 20_000), ("non-targeting", "d1", 200, 200_000),
                  ("T1", "d2", 0, 20_000), ("non-targeting", "d2", 0, 200_000)]
        self.assertGreater(self._raw(counts), 1.0)
        self.assertLess(abs(self._raw(counts, min_expected=1.0)), 0.05)     # d1 alone: no change
        lone = [("T1", "d1", 0, 30_000), ("non-targeting", "d1", 20, 20_000_000)]   # 0.03 counts expected
        self.assertTrue(np.isnan(self._raw(lone, min_expected=1.0)))         # unmeasured, not a zero

    def test_dropping_looks_at_the_controls_not_at_the_target_count(self):
        # 0.1 counts expected and 2 seen: keeping it because a count showed up selects on the
        # outcome, and every such donor reads as induced. It must be dropped like a zero.
        lucky = [("T1", "d1", 2, 30_000), ("non-targeting", "d1", 67, 20_000_000)]
        self.assertGreater(self._raw(lucky), 2.0)
        self.assertTrue(np.isnan(self._raw(lucky, min_expected=1.0)))

    def test_dropping_changes_nothing_where_every_donor_has_evidence(self):
        counts = [("T1", "d1", 7, 20_000), ("non-targeting", "d1", 300, 200_000),
                  ("T1", "d2", 2, 25_000), ("non-targeting", "d2", 90, 180_000)]
        X, obs = self._groups(counts)
        a = effects_from_pseudobulk(X, obs, ["g0", "g1"], targets=["T1"], condition="Rest")
        b = effects_from_pseudobulk(X, obs, ["g0", "g1"], targets=["T1"], condition="Rest", min_expected=1.0)
        np.testing.assert_array_equal(a.raw, b.raw)
        np.testing.assert_array_equal(a.se, b.se)
        np.testing.assert_array_equal(a.shrunk, b.shrunk)

    def test_a_gene_absent_in_one_donor_reads_as_induced_unless_the_pseudocount_is_scaled(self):
        # d1 expresses gene 0 at the same fraction in both groups; d2 (a female donor for a Y gene)
        # has no count in either. The controls' total is ten times the target's, as in the CD4 rows.
        counts = [("T1", "d1", 20, 20_000), ("non-targeting", "d1", 200, 200_000),
                  ("T1", "d2", 0, 20_000), ("non-targeting", "d2", 0, 200_000)]
        self.assertGreater(self._raw(counts, "constant"), 1.0)            # (ln 10) / 2 from d2 alone
        self.assertLess(abs(self._raw(counts, "library")), 0.05)

    def test_a_zero_count_the_controls_barely_predict_reads_near_zero(self):
        # An Orion-like pool: the controls' total is ~700 times the target's, and they predict
        # 0.03 counts in the target group. A zero is then no evidence either way.
        counts = [("T1", "d1", 0, 30_000), ("non-targeting", "d1", 20, 20_000_000)]
        self.assertGreater(self._raw(counts, "constant"), 2.0)            # ln(16): read as induced
        self.assertLess(abs(self._raw(counts, "library")), 0.1)            # a pseudocount at the geometric
        #                                                                    mean of the totals gave -2.0

    def test_a_scaled_pseudocount_reads_a_lost_gene_as_lost(self):
        counts = [("T1", "d1", 0, 20_000), ("non-targeting", "d1", 1, 200_000)]
        self.assertGreater(self._raw(counts, "constant"), 0.0)            # ln(3.3): no counts, yet induced
        self.assertLess(self._raw(counts, "library"), 0.0)

    def test_equal_totals_give_the_same_effects_in_both_modes(self):
        counts = [("T1", "d1", 7, 50_000), ("non-targeting", "d1", 30, 50_000),
                  ("T1", "d2", 0, 40_000), ("non-targeting", "d2", 3, 40_000)]
        X, obs = self._groups(counts)
        a = effects_from_pseudobulk(X, obs, ["g0", "g1"], targets=["T1"], condition="Rest")
        b = effects_from_pseudobulk(X, obs, ["g0", "g1"], targets=["T1"], condition="Rest", pseudo_scale="library")
        np.testing.assert_array_equal(a.raw, b.raw)
        np.testing.assert_array_equal(a.se, b.se)
        with self.assertRaises(ValueError):
            effects_from_pseudobulk(X, obs, ["g0", "g1"], targets=["T1"], condition="Rest", pseudo_scale="cpm")


class MixTests(unittest.TestCase):
    def _table(self, name, targets, rows, n):
        rows = np.asarray(rows, dtype=np.float32)
        return AxisTable(name, targets, rows, rows, np.ones_like(rows), np.asarray(n, dtype=float))

    def test_unmeasured_pairs_do_not_vote_zero(self):
        a = self._table("a", ["T"], [[1.0, np.nan, 2.0]], [1e6])
        b = self._table("b", ["T"], [[3.0, 5.0, np.nan]], [1e6])
        eff, w = mix([a, b], ["T"], gamma=0.0)
        np.testing.assert_allclose(eff[0], [2.0, 5.0, 2.0], rtol=1e-4)
        c = self._table("c", ["U"], [[1.0, 1.0, 1.0]], [10])
        eff, w = mix([c], ["T"])
        self.assertTrue((w == 0).all() and (eff == 0).all())

    def test_centring_uses_each_source_own_common_response(self):
        a = self._table("a", ["T", "U"], [[2.0, 0.0], [0.0, 0.0]], [1e9, 1e9])   # common a = [1, 0]
        b = self._table("b", ["T", "U"], [[0.0, 4.0], [0.0, 0.0]], [1e9, 1e9])   # common b = [0, 2]
        eff, _ = mix([a, b], ["T"], gamma=1.0)
        np.testing.assert_allclose(eff[0], [0.5, 1.0], rtol=1e-6)

    def test_reliability_weights_follow_cells(self):
        a = self._table("a", ["T"], [[1.0]], [100])     # reliability 0.5
        b = self._table("b", ["T"], [[4.0]], [300])     # reliability 0.75
        eff, _ = mix([a, b], ["T"], reliability_scale=100.0)
        self.assertAlmostEqual(float(eff[0, 0]), (0.5 * 1 + 0.75 * 4) / 1.25, places=5)


class ShrinkAndShareTests(unittest.TestCase):
    def test_z_shrink_keeps_strong_effects_and_kills_weak_ones(self):
        from vcc2026.multisource import z_shrink
        eff = np.array([-2.46, 0.3, 0.3, 0.0])
        se = np.array([0.2, 0.3, 0.05, 0.1])
        out = z_shrink(eff, se, k=4.0)
        self.assertGreater(abs(out[0]), 0.95 * 2.46)          # z = 12: kept (a single-normal prior crushed it)
        self.assertAlmostEqual(out[1], 0.3 * 1 / 5, places=6)  # z = 1: one fifth
        self.assertAlmostEqual(out[2], 0.3 * 36 / 40, places=6)  # z = 6: nine tenths kept
        self.assertEqual(out[3], 0.0)

    def test_shared_signal_recovers_a_known_split(self):
        from vcc2026.multisource import shared_signal
        rng = np.random.default_rng(3)
        T, G = 60, 500
        s = rng.normal(0, 1.0, (T, G))
        a_rows = s + rng.normal(0, 1.0, (T, G))                # V_a = 1
        b_rows = s + rng.normal(0, 2.0, (T, G))                # V_b = 4
        tg = [f"T{i}" for i in range(T)]
        mk = lambda n, r: AxisTable(n, tg, r.astype(np.float32), r.astype(np.float32),
                                    np.ones_like(r, dtype=np.float32), np.full(T, 1e6))
        out = shared_signal(mk("a", a_rows), mk("b", b_rows), tg)
        self.assertAlmostEqual(out["weight_a"], 0.8, delta=0.03)   # V_b / (V_a + V_b)
        # best amplitude: V_s / (V_s + w^2 V_a + (1-w)^2 V_b) = 1 / (1 + 0.64 + 0.16)
        self.assertAlmostEqual(out["amplitude"], 1 / 1.8, delta=0.03)


class PurityTests(unittest.TestCase):
    def test_depth_is_the_deepest_prefix_at_the_floor(self):
        pred = np.array([1, 1, -1, 1, 1, 1, 1, 1, 1, 1, -1, -1])
        obs = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(_purity_depth(pred, obs, 0.9), 10)        # 9/10 at depth 10
        self.assertEqual(_purity_depth(-obs, obs, 0.9), 0)


class TopKSignTests(unittest.TestCase):
    def test_ranks_by_the_prediction_and_skips_what_the_scorer_skips(self):
        pred = np.array([5.0, -4.0, 3.0, np.nan, 2.0, 0.0, -1.0])
        truth = np.array([1.0, 1.0, 1.0, 1.0, np.nan, 1.0, -9.0])
        # gene 0 is the target and is excluded; 3 (pred NaN), 4 (truth NaN) and 5 (pred 0) do not count
        got = topk_sign_agreement(pred, truth, (1, 2, 10), exclude=[0])
        # by |pred|: gene 1 (-4 vs +1, wrong), gene 2 (+3 vs +1, right), gene 6 (-1 vs -9, right)
        self.assertEqual(got[1], (0, 1))
        self.assertEqual(got[2], (1, 2))
        self.assertEqual(got[10], (2, 3))

    def test_a_mask_restricts_before_ranking(self):
        pred = np.array([3.0, 2.0, 1.0])
        truth = np.array([-1.0, 1.0, 1.0])
        keep = np.array([False, True, True])
        self.assertEqual(topk_sign_agreement(pred, truth, (1,), keep=keep)[1], (1, 1))


class EmpiricalBayesTests(unittest.TestCase):
    """`eb_components` and `eb_pool`: shared response, line deviation and noise by moments."""

    def test_moments_recover_the_simulated_variances(self):
        rng = np.random.default_rng(0)
        T, G, sigma2, tau2, se = 4000, 3, 0.04, 0.01, 0.1
        theta = rng.normal(0, np.sqrt(sigma2), (T, G))
        ys = [theta + rng.normal(0, np.sqrt(tau2), (T, G)) + rng.normal(0, se, (T, G)) for _ in range(3)]
        ses = [np.full((T, G), se) for _ in range(3)]
        s2, t2 = eb_components(ys, ses, [1.0, 1.0, 1.0], np.arange(G, dtype=float), bin_weight=1e-9, n_bins=1)
        np.testing.assert_allclose(s2, sigma2, rtol=0.1)
        np.testing.assert_allclose(t2, tau2, rtol=0.3)

    def test_blending_weight_counts_targets_not_observations(self):
        ys = [np.array([[1.0], [1.0]]), np.array([[1.0], [1.0]]), np.array([[1.0], [1.0]])]
        ses = [np.zeros((2, 1))] * 3
        # two targets, one gene, one bin: the bin median is the gene itself, so the blend is exact whatever n
        s2, _ = eb_components(ys, ses, [1.0] * 3, np.array([1.0]), bin_weight=2.0, n_bins=1)
        np.testing.assert_allclose(s2, [1.0])

    def test_posterior_mean_matches_the_formula_and_is_zero_without_shared_variance(self):
        ys = [np.array([[1.0, 1.0]]), np.array([[3.0, 3.0]])]
        ses = [np.array([[0.5, 0.5]]), np.array([[1.0, 1.0]])]
        sigma2, tau2 = np.array([1.0, 0.0]), np.array([0.25, 0.25])
        got = eb_pool(ys, ses, [1.0, 1.0], sigma2, tau2)
        p1, p2 = 1 / (0.25 + 0.25), 1 / (0.25 + 1.0)
        self.assertAlmostEqual(float(got[0, 0]), (p1 * 1 + p2 * 3) / (1 + p1 + p2), places=6)
        self.assertEqual(float(got[0, 1]), 0.0)
        # an unmeasured pair contributes nothing; a source's SE factor lowers its weight
        got2 = eb_pool([np.array([[np.nan, 1.0]]), np.array([[2.0, 1.0]])], ses, [1.0, 4.0], sigma2, tau2)
        p4 = 1 / (0.25 + 4.0 * 1.0)                                   # tau2 + k SE^2 of the second source
        self.assertAlmostEqual(float(got2[0, 0]), p4 * 2 / (1 + p4), places=6)


class Stage100EffectTests(unittest.TestCase):
    """Stage 100's `load_table`: the effect a recipe names is the one `mix` averages."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import json
        import tempfile
        spec = importlib.util.spec_from_file_location("stage100", REPO / "scripts" / "100_build_context_effects.py")
        cls.stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.stage)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cache = Path(cls.tmp.name)
        cls.raw = np.array([[-2.46, 0.3, 0.3, np.nan]], dtype=np.float32)
        cls.se = np.array([[0.2, 0.3, 0.05, np.nan]], dtype=np.float32)
        cls.shrunk = np.array([[-1.0, 0.1, 0.2, np.nan]], dtype=np.float32)   # any array: read as is
        np.savez_compressed(cls.cache / "src.npz", targets=np.array(["T1"]), shrunk=cls.shrunk, raw=cls.raw,
                            se=cls.se, n_cells=np.array([100]), meta=json.dumps({}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_raw_and_shrunk_are_read_as_stored(self):
        np.testing.assert_array_equal(self.stage.load_table(self.cache, "src", "raw").shrunk, self.raw)
        np.testing.assert_array_equal(self.stage.load_table(self.cache, "src", "shrunk").shrunk, self.shrunk)

    def test_zshrink_recomputes_from_raw_and_se_and_keeps_unmeasured_nan(self):
        from vcc2026.multisource import z_shrink
        got = self.stage.load_table(self.cache, "src", "zshrink", 64.0).shrunk
        want = z_shrink(self.raw, self.se, k=64.0)
        np.testing.assert_allclose(got[0, :3], want[0, :3], rtol=1e-6)
        self.assertAlmostEqual(float(got[0, 1]), 0.3 * 1 / 65, places=6)   # z = 1
        self.assertTrue(np.isnan(got[0, 3]))                              # never becomes a vote for zero

    def test_zshrink_without_a_positive_k_is_refused(self):
        for k in (None, 0, -4):
            with self.assertRaises(ValueError):
                self.stage.load_table(self.cache, "src", "zshrink", k)

    def _save(self, name, raw, se, meta, targets=("T1",)):
        import json
        np.savez_compressed(self.cache / f"{name}.npz", targets=np.array(list(targets)), shrunk=raw, raw=raw,
                            se=se, n_cells=np.full(len(targets), 100), meta=json.dumps(meta))

    def test_a_source_without_se_is_refused_not_turned_into_zero_votes(self):
        # the 24-25 September defect: NaN SE gave z = 0, an effect of 0, and a vote for zero in `mix`
        self._save("nose", np.array([[1.0, -0.5]], dtype=np.float32), np.full((1, 2), np.nan, np.float32), {})
        with self.assertRaises(ValueError):
            self.stage.load_table(self.cache, "nose", "zshrink", 16.0)

    def test_a_mixture_without_se_is_rebuilt_from_its_shrunk_parts(self):
        from vcc2026.multisource import mix, z_shrink
        a_raw, a_se = np.array([[2.0, 0.2]], np.float32), np.array([[0.25, 0.2]], np.float32)
        b_raw, b_se = np.array([[1.0, -0.4]], np.float32), np.array([[0.5, 0.1]], np.float32)
        self._save("partA", a_raw, a_se, {})
        self._save("partB", b_raw, b_se, {})
        self._save("mixAB", (a_raw + b_raw) / 2, np.full((1, 2), np.nan, np.float32), {"from": ["partA", "partB"]})
        got = self.stage.load_table(self.cache, "mixAB", "zshrink", 4.0)
        want = (z_shrink(a_raw, a_se, 4.0) + z_shrink(b_raw, b_se, 4.0)) / 2    # equal cells: equal reliability
        np.testing.assert_allclose(got.shrunk, want, rtol=1e-5)
        parts = [self.stage.load_table(self.cache, n, "raw") for n in ("partA", "partB")]
        raw_mix, _ = mix(parts, ["T1"], gamma=0.0)
        np.testing.assert_allclose(got.raw, raw_mix, rtol=1e-6)


class Stage100GeneShareTests(unittest.TestCase):
    """Stage 100's gene_share block: a share per gene of the axis, then the reference's detectable count."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("stage100", REPO / "scripts" / "100_build_context_effects.py")
        cls.stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.stage)

    def _csv(self, tmp, rows):
        import pandas as pd
        path = Path(tmp) / "share.csv"
        pd.DataFrame(rows, columns=["gene", "share"]).to_csv(path, index=False)
        return path

    def test_every_gene_needs_a_share_in_the_unit_interval(self):
        import tempfile
        axis = np.array(["G1", "G2", "G3"])
        with tempfile.TemporaryDirectory() as tmp:
            ok = self._csv(tmp, [("G3", 0.0), ("G1", 1.0), ("G2", 0.25), ("EXTRA", 0.5)])
            np.testing.assert_array_equal(self.stage.load_gene_share(ok, axis), [1.0, 0.25, 0.0])
            for rows in ([("G1", 1.0), ("G2", 0.5)],                     # G3 missing
                         [("G1", 1.0), ("G2", 1.5), ("G3", 0.0)],        # above 1
                         [("G1", 1.0), ("G1", 0.5), ("G2", 0.1), ("G3", 0.0)]):   # a gene twice
                with self.assertRaises(ValueError):
                    self.stage.load_gene_share(self._csv(tmp, rows), axis)

    def test_without_a_reference_it_only_multiplies(self):
        eff = np.array([[1.0, -2.0, 0.5], [0.0, 3.0, -1.0]])
        out, scale = self.stage.apply_gene_share(eff, np.array([1.0, 0.5, 0.0]))
        np.testing.assert_allclose(out, [[1.0, -1.0, 0.0], [0.0, 1.5, 0.0]])
        self.assertEqual(scale, 1.0)
        same, _ = self.stage.apply_gene_share(eff, np.ones(3))
        np.testing.assert_array_equal(same, eff)

    def test_the_scale_matches_the_reference_detectable_count(self):
        from vcc2026.transfer_model import detectable_threshold
        rng = np.random.default_rng(0)
        cpm = np.full(200, 50.0)
        thr = detectable_threshold(cpm)
        eff = rng.normal(0, 0.1, size=(30, 200))
        reference = rng.normal(0, 0.3, size=(30, 200))
        share = np.where(np.arange(200) < 100, 1.0, 0.2)
        out, scale = self.stage.apply_gene_share(eff, share, reference, np.zeros((30, 200)), cpm)
        count = lambda E: np.median((np.abs(E) > thr[None, :]).sum(axis=1))   # noqa: E731
        self.assertGreater(scale, 1.0)
        self.assertLessEqual(abs(count(out) - count(reference)), 1.0)
        np.testing.assert_allclose(out, eff * share[None, :] * scale)


class Stage100ExpressionGateTests(unittest.TestCase):
    """Stage 100's expression_gate block: genes the context barely expresses get no effect, the rest is untouched."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("stage100", REPO / "scripts" / "100_build_context_effects.py")
        cls.stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.stage)

    def test_genes_below_the_threshold_or_without_cpm_are_zeroed_for_every_target(self):
        eff = np.array([[1.0, -2.0, 0.5, 3.0], [0.25, 3.0, -1.0, -4.0]], dtype=np.float32)
        cpm = np.array([10.0, 4.99, np.nan, 5.0])
        out, info = self.stage.apply_expression_gate(eff, cpm, 5.0)
        np.testing.assert_array_equal(out, [[1.0, 0.0, 0.0, 3.0], [0.25, 0.0, 0.0, -4.0]])
        self.assertEqual(out.dtype, eff.dtype)
        self.assertEqual((info["genes_gated"], info["genes_without_cpm"]), (2, 1))
        self.assertAlmostEqual(info["energy_share_gated"], (4.0 + 0.25 + 9.0 + 1.0) / float(np.sum(eff.astype(float) ** 2)))

    def test_the_input_is_not_modified_and_nothing_expressed_changes(self):
        rng = np.random.default_rng(1)
        eff = rng.normal(size=(5, 50))
        keep = eff.copy()
        out, info = self.stage.apply_expression_gate(eff, np.full(50, 100.0), 5.0)
        np.testing.assert_array_equal(eff, keep)
        np.testing.assert_array_equal(out, eff)
        self.assertEqual(info["genes_gated"], 0)
        self.assertEqual(info["energy_share_gated"], 0.0)

    def test_a_cpm_vector_of_the_wrong_length_is_refused(self):
        with self.assertRaises(ValueError):
            self.stage.apply_expression_gate(np.zeros((2, 3)), np.ones(4), 5.0)


class Stage100CisTests(unittest.TestCase):
    """Stage 100's cis head: a prior no panel target informs, added only near each target."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("stage100", REPO / "scripts" / "100_build_context_effects.py")
        cls.stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.stage)
        import pandas as pd
        cls.coords = pd.DataFrame({"chrom": ["chr1", "chr1", "chr1", "chr1", "chr2"],
                                   "tss": [10_000, 10_300, 13_000, 30_000, 10_100]},
                                  index=pd.Index(["T1", "N1", "N2", "F1", "OTHER"], name="symbol"))
        cls.axis = np.array(["T1", "N1", "N2", "F1", "OTHER"])
        cls.pairs = pd.DataFrame({"target": ["T1", "P1", "P2", "P3", "P4"], "gene": ["x", "a", "b", "c", "d"],
                                  "dist": [100, 200, 400, 1500, 3000], "log2fc": [-10.0, -1.0, -1.0, -0.5, -0.25]})

    def test_the_prior_never_sees_a_panel_target(self):
        model = self.stage.cis_prior(self.pairs, ["T1"])
        self.assertAlmostEqual(float(model.by_bin[0]), -np.log(2.0))       # median of -1, -1 log2; not -10
        self.assertEqual(int(model.n_by_bin[0]), 2)

    def test_only_neighbours_within_the_distance_move_and_become_observed(self):
        model = self.stage.cis_prior(self.pairs, ["T1"])
        eff = np.zeros((1, 5))
        observed = np.array([[True, False, False, False, False]])
        counts = self.stage.add_cis(eff, observed, ["T1"], self.axis, model, self.coords, 5000, 2.0)
        self.assertEqual(counts, {"pairs": 2, "targets_with_a_neighbour": 1})
        self.assertAlmostEqual(eff[0, 1], 2.0 * float(model.prior(np.array([300]))[0]))
        self.assertAlmostEqual(eff[0, 2], 2.0 * -0.25 * np.log(2.0))       # 3 kb: the 2-5 kb bin
        self.assertEqual(eff[0, 0], 0.0)                                   # the target's own gene
        self.assertEqual(eff[0, 3], 0.0)                                   # 20 kb away
        self.assertEqual(eff[0, 4], 0.0)                                   # another chromosome
        np.testing.assert_array_equal(observed[0], [True, True, True, False, False])

    def test_association_is_the_centred_mean_of_scored_partners_never_the_target(self):
        import gzip
        import tempfile
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            eff = np.array([[1.0, 0.0, 2.0], [3.0, 0.0, 0.0], [5.0, 5.0, 5.0], [9.0, 9.0, np.nan]], np.float32)
            np.savez_compressed(root / "k562_00.npz", targets=np.array(["P1", "P2", "X", "T"]), shrunk=eff,
                                raw=eff, se=np.ones_like(eff), n_cells=np.full(4, 100), meta="{}")
            pd.DataFrame({"target": ["P1", "P2", "X", "T"], "chunk": "k562_00.npz"}).to_csv(root / "index.csv", index=False)
            (root / "info").write_text("#string_protein_id\tpreferred_name\n"
                                       + "".join(f"9606.E{n}\t{n}\n" for n in ("T", "P1", "P2", "X")), encoding="utf-8")
            links = ("protein1 protein2 combined_score\n9606.ET 9606.EP1 800\n9606.ET 9606.EP2 900\n"
                     "9606.ET 9606.EX 500\n9606.ET 9606.ET 999\n")
            (root / "links").write_bytes(gzip.compress(links.encode()))    # gzip without the extension
            out, counts = self.stage.partner_effects(["T", "P1"], root, root / "links", root / "info", 700,
                                                     np.array(["P1", "P2", "G3"]))
        centre = np.nan_to_num(eff).mean(axis=0)
        # X is under 700 and T is not its own partner; each partner's own gene is left out of its mean
        want = np.array([eff[1, 0], eff[0, 1], (eff[0, 2] + eff[1, 2]) / 2]) - centre
        np.testing.assert_allclose(out["T"], want, rtol=1e-6)
        self.assertNotIn("P1", out)                         # P1 has no link of its own in this file
        self.assertEqual(counts["targets_with_partners"], 1)

    def test_a_distance_outside_the_model_is_refused(self):
        model = self.stage.cis_prior(self.pairs, ["T1"])
        for d in (0, model.edges[-1] + 1):
            with self.assertRaises(ValueError):
                self.stage.add_cis(np.zeros((1, 5)), np.zeros((1, 5), bool), ["T1"], self.axis, model,
                                   self.coords, d, 1.0)


class PanelFileTests(unittest.TestCase):
    """`vcc2026.panel`: the panel's targets by column name, and a hash of the list rather than of the file."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self, name, text):
        path = self.root / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def test_a_bare_list_a_counts_file_and_a_per_context_file_give_the_same_targets(self):
        from vcc2026.panel import read_panel
        want = ["TP53", "ACLY", "MYC"]
        files = [self._file("bare.csv", "target_gene\nTP53\nACLY\nMYC\n"),
                 self._file("crlf.csv", "target_gene\r\nTP53\r\nACLY\r\nMYC\r\n"),
                 self._file("counts.csv", "target_gene,n_cells\nTP53,400\nACLY,400\nMYC,400\n"),
                 # context first, each target once per context: the column order that position reading got wrong
                 self._file("ctx.csv", "context,target_gene\nD,TP53\nD,ACLY\nE,TP53\nD,MYC\nE,MYC\nE,ACLY\n")]
        for path in files:
            with self.subTest(path=path.name):
                self.assertEqual(read_panel(path), want)

    def test_a_single_column_under_another_header_is_a_bare_list_and_blanks_are_skipped(self):
        from vcc2026.panel import read_panel
        self.assertEqual(read_panel(self._file("g.csv", "gene\nNA\n TP53 \n\"\"\nMYC\n")), ["NA", "TP53", "MYC"])

    def test_a_wrong_column_the_control_label_and_an_empty_panel_are_refused(self):
        from vcc2026.panel import read_panel
        for name, text in (("cols.csv", "context,gene\nD,TP53\n"),
                           ("ntc.csv", "target_gene,n_cells\nTP53,400\nnon-targeting,1000\n"),
                           ("empty.csv", "target_gene\n")):
            with self.subTest(name=name), self.assertRaises(ValueError):
                read_panel(self._file(name, text))

    def test_the_hash_names_the_targets_and_their_order_not_the_file(self):
        import hashlib
        from vcc2026.panel import panel_sha256, read_panel
        a = read_panel(self._file("a.csv", "target_gene\r\nTP53\r\nMYC\r\n"))
        b = read_panel(self._file("b.csv", "context,target_gene,n_cells\nD,TP53,400\nD,MYC,400\nE,TP53,400\n"))
        self.assertEqual(panel_sha256(a), panel_sha256(b))
        self.assertEqual(panel_sha256(a), hashlib.sha256(b"TP53\nMYC").hexdigest())
        self.assertNotEqual(panel_sha256(a), panel_sha256(["MYC", "TP53"]))


class Stage100CacheCheckTests(unittest.TestCase):
    """Stage 100 run end to end on synthetic caches: the panel, the contexts, the cache's targets, ``common``.

    The official axis is replaced by five genes and the data root by a temporary folder."""

    AXIS = ("G1", "G2", "G3", "G4", "G5")
    PANEL = ["T1", "T2", "T3", "T4"]

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("stage100", REPO / "scripts" / "100_build_context_effects.py")
        cls.stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.stage)

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.targets = self.root / "pert_counts.csv"
        self.targets.write_text("target_gene\n" + "\n".join(self.PANEL) + "\n", encoding="utf-8")
        rng = np.random.default_rng(7)
        self.own = self._cache("own", {"s1": ["T1", "T2", "T3"], "s2": ["T2", "T4", "X9"]}, rng)
        self.foreign = self._cache("foreign", {"s1": ["X1", "X2", "T1"], "s2": ["X3", "X4"]}, rng)
        self.recipe = {"name": "syn", "effect": "shrunk", "gamma": 1.0, "reliability_scale": 100,
                       "allow_missing_targets": True,
                       "contexts": {c: {"amplitude": 1.5, "weights": {"s1": 1.0, "s2": 2.0}} for c in ("A", "B")}}

    def tearDown(self):
        self.tmp.cleanup()

    def _cache(self, name, tables, rng):
        import json
        cache = self.root / name
        cache.mkdir()
        for src, targets in tables.items():
            eff = rng.normal(0, 1, size=(len(targets), len(self.AXIS))).astype(np.float32)
            eff[0, 4] = np.nan                                   # an unmeasured pair
            np.savez_compressed(cache / f"{src}.npz", targets=np.array(targets), shrunk=eff, raw=eff,
                                se=np.ones_like(eff), n_cells=np.arange(50, 50 + 50 * len(targets), 50),
                                meta=json.dumps({}))
        return cache

    def _run(self, recipe, cache, out, *extra, targets=None):
        import contextlib
        import io
        import json
        from types import SimpleNamespace
        from unittest import mock
        path = self.root / f"recipe_{out}.json"
        path.write_text(json.dumps(recipe), encoding="utf-8")
        argv = ["100", "--recipe", str(path), "--cache", str(cache), "--targets-csv", str(targets or self.targets),
                "--out", str(self.root / out), *extra]
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(self.stage, "official_axis", lambda: SimpleNamespace(symbols=self.AXIS)), \
                mock.patch.object(self.stage, "DATA_ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            self.stage.main()
        return json.loads((self.root / out / "manifest.json").read_text(encoding="utf-8"))

    def _lfc(self, out, ctx="A"):
        with np.load(self.root / out / f"effects_{ctx}.npz") as z:
            return z["targets"].astype(str).tolist(), z["lfc"], z["observed"]

    def _expected(self, cache, common=None):
        tables = [self.stage.load_table(cache, n) for n in ("s1", "s2")]
        eff, w = mix(tables, self.PANEL, weights={"s1": 1.0, "s2": 2.0}, gamma=1.0, reliability_scale=100.0,
                     common=common)
        return (eff * 1.5).astype(np.float32), w > 0, tables

    def _manifest_of_cache(self, cache, panel):
        import json
        from vcc2026.panel import panel_sha256
        (cache / "manifest.json").write_text(json.dumps({"targets_sha256": panel_sha256(panel)}), encoding="utf-8")

    def test_an_old_cache_without_manifest_still_builds_and_says_it_was_not_verified(self):
        import hashlib
        from vcc2026.panel import panel_sha256
        m = self._run(self.recipe, self.own, "old")
        targets, lfc, observed = self._lfc("old")
        want, want_obs, _ = self._expected(self.own)
        self.assertEqual(targets, self.PANEL)
        np.testing.assert_array_equal(lfc, want)
        np.testing.assert_array_equal(observed, want_obs)
        check = m["cache_check"]
        self.assertFalse(check["cache_manifest"])
        self.assertFalse(check["targets_verified"])
        self.assertEqual(check["why_not_verified"], "the cache has no manifest.json")
        self.assertEqual((check["targets_covered"], check["coverage"]), (4, 1.0))
        self.assertEqual(check["targets_covered_by_table"], {"s1": 3, "s2": 2})
        self.assertEqual(m["targets"], {"path": str(self.targets), "n": 4, "panel_sha256": panel_sha256(self.PANEL),
                                        "file_sha256": hashlib.sha256(self.targets.read_bytes()).hexdigest()})
        self.assertEqual(m["cache_npz_sha256"], {f"{n}.npz": hashlib.sha256((self.own / f"{n}.npz").read_bytes()).hexdigest()
                                                 for n in ("s1", "s2")})
        self.assertEqual(m["common"], {"mode": "panel"})
        self.assertIsNone(m["contexts_checked"])
        for key in ("argv", "started_utc", "finished_utc", "peak_rss_bytes", "cache", "written_utc"):
            self.assertIn(key, m)
        self.assertLessEqual(m["started_utc"], m["finished_utc"])

    def test_a_foreign_cache_is_refused_and_writes_nothing(self):
        with self.assertRaises(SystemExit) as caught:
            self._run(self.recipe, self.foreign, "refused")
        self.assertIn("1 of the 4 panel targets", str(caught.exception))
        self.assertFalse((self.root / "refused").exists())

    def test_allow_foreign_cache_builds_and_records_the_lifted_refusal(self):
        m = self._run({**self.recipe, "allow_foreign_cache": True}, self.foreign, "allowed")
        self.assertEqual(m["cache_check"]["coverage"], 0.25)
        self.assertTrue(m["cache_check"]["allow_foreign_cache"])
        self.assertEqual(len(m["cache_check"]["refusals_lifted"]), 1)
        with self.assertRaises(SystemExit):
            self._run({**self.recipe, "allow_foreign_cache": "yes"}, self.foreign, "not_a_bool")

    def test_a_cache_manifest_with_the_panel_hash_verifies_its_targets(self):
        self._manifest_of_cache(self.own, self.PANEL)
        m = self._run(self.recipe, self.own, "verified")
        self.assertTrue(m["cache_check"]["targets_verified"])
        self.assertTrue(m["cache_check"]["cache_manifest"])
        np.testing.assert_array_equal(self._lfc("verified")[1], self._expected(self.own)[0])

    def test_a_cache_manifest_with_another_panel_hash_is_refused_even_with_full_coverage(self):
        self._manifest_of_cache(self.own, ["T1", "T2", "T3", "T4", "T5"])
        with self.assertRaises(SystemExit) as caught:
            self._run(self.recipe, self.own, "mismatch")
        self.assertIn("built for other targets", str(caught.exception))

    def test_a_verified_cache_is_not_held_to_the_floor_but_must_cover_a_target(self):
        self._manifest_of_cache(self.foreign, self.PANEL)            # 1 of 4: under the floor, but verified
        self.assertEqual(self._run(self.recipe, self.foreign, "low")["cache_check"]["targets_covered"], 1)
        none = self._cache("none", {"s1": ["X1"], "s2": ["X2"]}, np.random.default_rng(1))
        self._manifest_of_cache(none, self.PANEL)
        with self.assertRaises(SystemExit):
            self._run(self.recipe, none, "empty")

    def test_a_cache_manifest_without_the_panel_hash_is_held_to_the_floor_like_no_manifest(self):
        import json
        for cache in (self.own, self.foreign):
            (cache / "manifest.json").write_text(json.dumps({"stage": "older"}), encoding="utf-8")
        check = self._run(self.recipe, self.own, "no_key")["cache_check"]
        self.assertTrue(check["cache_manifest"])
        self.assertFalse(check["targets_verified"])
        self.assertEqual(check["why_not_verified"], "the cache's manifest.json has no targets_sha256")
        with self.assertRaises(SystemExit) as caught:
            self._run(self.recipe, self.foreign, "no_key_foreign")
        self.assertIn("has no targets_sha256", str(caught.exception))
        self.assertFalse((self.root / "no_key_foreign").exists())

    def test_the_contexts_must_be_the_recipe_keys(self):
        self.assertEqual(self._run(self.recipe, self.own, "ab_comma", "--contexts", "B,A")["contexts_checked"], ["B", "A"])
        self.assertEqual(self._run(self.recipe, self.own, "ab_space", "--contexts", "A", "B")["contexts_checked"],
                         ["A", "B"])
        for given in (["D,E,F"], ["A"], ["A,B,C"], ["A,A,B"]):
            with self.subTest(given=given), self.assertRaises(SystemExit):
                self._run(self.recipe, self.own, "bad", "--contexts", *given)
        self.assertFalse((self.root / "bad").exists())

    def test_the_panel_is_read_by_column_name(self):
        per_context = self.root / "per_context.csv"
        per_context.write_text("context,target_gene\nA,T1\nA,T2\nB,T1\nA,T3\nB,T4\nA,T4\n", encoding="utf-8")
        self._run(self.recipe, self.own, "by_name", targets=per_context)
        targets, lfc, _ = self._lfc("by_name")
        self.assertEqual(targets, self.PANEL)
        np.testing.assert_array_equal(lfc, self._expected(self.own)[0])

    def test_common_panel_is_the_default_and_a_frozen_file_is_honoured(self):
        self._run(self.recipe, self.own, "default")
        self._run({**self.recipe, "common": "panel"}, self.own, "panel")
        np.testing.assert_array_equal(self._lfc("panel")[1], self._lfc("default")[1])
        _, _, tables = self._expected(self.own)
        own = {t.name: t.common() for t in tables}
        np.savez(self.root / "own_common.npz", genes=np.array(self.AXIS), **own)
        m = self._run({**self.recipe, "common": "own_common.npz"}, self.own, "frozen_own")
        np.testing.assert_array_equal(self._lfc("frozen_own")[1], self._lfc("default")[1])   # same vectors, same bits
        self.assertEqual(m["common"]["mode"], "frozen")
        other = {"s1": np.full(5, 0.3), "s2": np.linspace(-1, 1, 5)}
        np.savez(self.root / "other_common.npz", **other, extra=np.zeros(5))
        m = self._run({**self.recipe, "common": "other_common.npz"}, self.own, "frozen_other")
        want = self._expected(self.own, common=other)[0]
        np.testing.assert_array_equal(self._lfc("frozen_other")[1], want)
        self.assertFalse(np.array_equal(want, self._lfc("default")[1]))
        self.assertEqual(m["common"]["unused_keys"], ["extra"])
        self.assertEqual(m["common"]["path"], "other_common.npz")

    def test_a_frozen_common_file_must_give_every_source_a_finite_vector_on_the_axis(self):
        good = np.zeros(5)
        for name, arrays in (("missing", {"s1": good}),
                             ("short", {"s1": good, "s2": np.zeros(4)}),
                             ("nan", {"s1": good, "s2": np.array([0, 0, np.nan, 0, 0])}),
                             ("axis", {"s1": good, "s2": good, "genes": np.array(["G1", "G2", "G3", "G4", "GX"])})):
            np.savez(self.root / f"{name}.npz", **arrays)
            with self.subTest(name=name), self.assertRaises(SystemExit):
                self._run({**self.recipe, "common": f"{name}.npz"}, self.own, f"common_{name}")
        with self.assertRaises(SystemExit):
            self._run({**self.recipe, "common": 1.0}, self.own, "common_number")

    def test_the_eb_pooling_subtracts_the_frozen_common_too(self):
        import pandas as pd
        _, _, tables = self._expected(self.own)
        basal = pd.DataFrame({"s1": np.full(5, 50.0), "s2": np.full(5, 80.0)})
        base, n, _ = self.stage.eb_effects(self.own, tables, self.PANEL, 1.0, {}, basal)
        same, n2, _ = self.stage.eb_effects(self.own, tables, self.PANEL, 1.0, {}, basal,
                                            {t.name: t.common() for t in tables})
        np.testing.assert_array_equal(same, base)
        np.testing.assert_array_equal(n2, n)
        moved, _, _ = self.stage.eb_effects(self.own, tables, self.PANEL, 1.0, {}, basal,
                                            {"s1": np.full(5, 0.5), "s2": np.full(5, -0.5)})
        self.assertFalse(np.allclose(moved, base))


if __name__ == "__main__":
    unittest.main()
