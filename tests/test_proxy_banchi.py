"""The proxies every bench since 25 September reads its rule on, pinned on synthetic data.

They live in a report folder, `reports/trasferimento/banco_varianti_2026-09-25/`, and other
benches import them by path (map in `reports/README.md`): a change to them would move every
Δ = 0.36 ΔPDS_gen - 0.27 ΔnMAE_gen at once, in silence. These tests pin what they compute.
A new version of a proxy belongs in a new report folder, with its own test.

    pds_proxy       mean over targets of 1 - rank/(n-1) of the true target, cosine, midrank,
                    log1p-style gene weights, panel genes excluded
    rank_pds        the same rank, unweighted
    fidelity_proxy  sign precision of the top-|prediction| genes, and k / max(n, n_conf)
    realise         the trial-01 profile step (clip at |log2| 6, composition closed on the
                    observed genes) plus the noise of a 400-cell pseudobulk
"""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "reports" / "trasferimento" / "banco_varianti_2026-09-25"
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(REPO / "src"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, BENCH / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyze = load("analyze")
noise_sim = load("noise_sim")
noise_sim2 = load("noise_sim2")


class PdsProxyTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.T = rng.standard_normal((12, 40))
        self.weight = np.ones(40)
        self.panel = np.array([0, 1])

    def test_a_perfect_prediction_ranks_every_target_first(self):
        per = analyze.pds_proxy(self.T.copy(), self.T, self.weight, self.panel)
        np.testing.assert_allclose(per, 1.0)

    def test_no_signal_is_a_tie_with_every_target_and_reads_one_half(self):
        per = analyze.pds_proxy(np.zeros_like(self.T), self.T, self.weight, self.panel)
        np.testing.assert_allclose(per, 0.5)

    def test_the_prediction_of_another_target_ranks_the_true_one_below_it(self):
        swapped = self.T[[1, 0] + list(range(2, 12))]
        per = analyze.pds_proxy(swapped, self.T, self.weight, self.panel)
        self.assertLess(per[0], 1.0)
        self.assertLess(per[1], 1.0)
        np.testing.assert_allclose(per[2:], 1.0)

    def test_panel_genes_do_not_count(self):
        P = np.zeros_like(self.T)
        P[:, self.panel] = self.T[:, self.panel]   # signal only where the panel sits
        per = analyze.pds_proxy(P, self.T, self.weight, self.panel)
        np.testing.assert_allclose(per, 0.5)

    def test_unmeasured_truth_is_read_as_zero_and_unweighted_rank_matches(self):
        T = self.T.copy()
        T[:, 5] = np.nan
        with np.errstate(invalid="ignore"):
            per = analyze.pds_proxy(self.T, T, self.weight, np.array([], dtype=int))
        np.testing.assert_allclose(per, noise_sim.rank_pds(self.T, np.nan_to_num(T)))


class FidelityProxyTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.T = rng.standard_normal((3, 300))
        self.Z = np.full_like(self.T, 5.0)          # every truth gene counts as confident
        self.gate = np.ones(300, dtype=bool)
        self.tcols = np.array([0, -1, 2])

    def test_same_signs_give_precision_one_and_opposite_signs_zero(self):
        right = analyze.fidelity_proxy(self.T, self.T, self.Z, self.gate, self.tcols)
        wrong = analyze.fidelity_proxy(-self.T, self.T, self.Z, self.gate, self.tcols)
        for n in analyze.TOP_N:
            np.testing.assert_allclose(right[f"prec_{n}"], 1.0)
            np.testing.assert_allclose(wrong[f"prec_{n}"], 0.0)

    def test_yield_divides_by_the_larger_of_the_calls_and_the_confident_genes(self):
        out = analyze.fidelity_proxy(self.T, self.T, self.Z, self.gate, self.tcols)
        conf = out["n_conf"]
        self.assertTrue(np.all(conf >= 298))        # 300 genes, the target column dropped
        np.testing.assert_allclose(out["yield_50"], 50 / conf)

    def test_genes_outside_the_expression_gate_and_the_target_gene_are_skipped(self):
        gate = self.gate.copy()
        gate[100:] = False
        P = self.T.copy()
        P[:, 0] = -P[:, 0]                           # the target gene of row 0, flipped
        out = analyze.fidelity_proxy(P, self.T, self.Z, gate, self.tcols)
        np.testing.assert_allclose(out["prec_50"][0], 1.0)
        self.assertTrue(np.all(out["n_conf"] <= 100))


class RealiseTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(2)
        self.basal = rng.uniform(1.0, 500.0, 60)
        self.observed = np.ones((4, 60), dtype=bool)
        self.observed[:, 50:] = False

    def test_no_effect_means_no_shift_and_zero_change(self):
        E = np.zeros((4, 60))
        noisy, c, real = noise_sim2.realise(E, self.basal, self.observed, np.random.default_rng(3))
        np.testing.assert_allclose(c, 0.0, atol=1e-12)
        np.testing.assert_allclose(real, 0.0, atol=1e-12)
        self.assertGreater(float(np.abs(noisy).max()), 0.0)   # the pseudobulk noise remains

    def test_composition_is_closed_on_the_observed_genes_and_the_rest_stays(self):
        E = np.random.default_rng(4).normal(0.0, 1.0, (4, 60))
        _, c, real = noise_sim2.realise(E, self.basal, self.observed, np.random.default_rng(5))
        before = (self.basal * self.observed).sum(axis=1)
        after = (self.basal * self.observed * np.exp(real)).sum(axis=1)
        np.testing.assert_allclose(after, before, rtol=1e-10)
        np.testing.assert_allclose(real[:, 50:], 0.0)

    def test_the_profile_step_is_the_one_stage_45_applies(self):
        """realise stands for `inference.predicted_profile`, which stage 45 uses: same numbers."""
        from vcc2026.inference import predicted_profile

        E = np.random.default_rng(7).normal(0.0, 3.0, (4, 60))   # some genes past the clip
        _, _, real = noise_sim2.realise(E, self.basal, self.observed, np.random.default_rng(8))
        for i in range(E.shape[0]):
            profile, _ = predicted_profile(self.basal, E[i] / np.log(2.0), self.observed[i])
            np.testing.assert_allclose(np.log(profile / self.basal), real[i], atol=1e-12)

    def test_the_generator_clips_log2_fold_changes_at_six(self):
        E = np.zeros((1, 60))
        E[0, 0] = 20.0                              # ln fold change far beyond 6 in log2
        one = np.ones((1, 60), dtype=bool)
        _, c, real = noise_sim2.realise(E, self.basal, one, np.random.default_rng(6))
        self.assertAlmostEqual(float((real[0, 0] - real[0, 1]) / np.log(2.0)), 6.0, places=9)


if __name__ == "__main__":
    unittest.main()
