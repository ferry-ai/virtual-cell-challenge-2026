"""Tests for `vcc2026.multisource`.

Each test pins a way a multi-source transfer could return plausible wrong numbers:

* a donor's knockdown compared with another donor's controls (donor effects leak in);
* an unmeasured (target, gene) pair counted as a vote for zero;
* centring that subtracts one source's common response from another;
* a sign-purity proxy that reads the truth's ranking instead of the prediction's;
* a top-k sign agreement that ranks by the truth, counts undefined genes, or keeps the
  target gene the scorer drops;
* a shrinkage recomputed from a missing SE, which silently turns a source into zeros.
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


if __name__ == "__main__":
    unittest.main()
