"""Synthetic checks of covar.py (action 6 of R-REV): no real data is read.

Worlds (as the design map of 28/09 asks):
1. modules shared by the contexts but assigned to different targets: M1 high, M2 near 0, D > 0;
2. effects shared by the contexts without any module: M2 high, M1's ceiling at its null (W1 would drop it);
3. a universal noise structure (the same gene-gene noise covariance in every context): W5 must flag it (no
   margin over the non-targeting pseudo-effects), W4 must see one half differ from the cross-half matrix;
4. M3a in a module world: relation, in-line and effect routes above their nulls; leakage canary: rewriting the test
   targets' rows in every context leaves every mean, SD and beta unchanged; a row whose cis window holds x does not
   move beta(x, .);
plus the exact permutation nulls against Monte Carlo, the kappa fit, the cis mask, G* and the rule (`decide`).

    scripts/py.cmd reports/modelli/covariazione_2026-09-28/selftest_covar.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import covar as C  # noqa: E402

FAST = dict(seeds=(0,), n_gene_perm=20, n_target_perm=50)


def module_world(n_targets, G, n_mod, rng, *, amp=1.0, noise=0.3, assign=None):
    """y[t] = amp on the genes of the module assigned to t, plus Gaussian noise; se = noise."""
    mod = np.arange(G) % n_mod
    assign = rng.integers(0, n_mod, n_targets) if assign is None else assign
    y = amp * (mod[None, :] == assign[:, None]).astype(np.float32) * rng.normal(1.0, 0.2, (n_targets, 1))
    y = y + rng.normal(0, noise, (n_targets, G))
    return y.astype(np.float32), np.full((n_targets, G), noise, np.float32), assign


def side(name, raw, se, G, kappa=1.0):
    return C.Side(name, raw, se, np.full(G, kappa), 1.0, np.linspace(1, 8, G))


class TestNulls(unittest.TestCase):
    def test_mantel_exact_matches_monte_carlo(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(300, 60)).astype(np.float32)
        X[:, :20] += rng.normal(size=(300, 1)).astype(np.float32)
        Y = rng.normal(size=(300, 60)).astype(np.float32)
        Y[:, 10:30] += rng.normal(size=(300, 1)).astype(np.float32)
        A, B = C.corr_rows(X), C.corr_rows(Y)
        bins = C.rank_bins(np.linspace(0, 1, 60) + rng.normal(0, 0.3, 60), 5)
        mc, sd = C.mantel_null_mc(A, B, bins, 3000, np.random.default_rng(2))
        ex = C.mantel_null_exact(A, B, bins)
        self.assertLess(abs(mc - ex), 4 * sd / np.sqrt(3000) + 1e-4)

    def test_target_null_exact_matches_monte_carlo(self):
        rng = np.random.default_rng(3)
        Ua = C.unit_rows(rng.normal(size=(200, 40)).astype(np.float32) + 1.0)
        Ub = C.unit_rows(rng.normal(size=(200, 40)).astype(np.float32) + 1.0)
        strata = rng.integers(0, 4, 200)
        sc = C.StrataCross(Ua, Ub, strata)
        mc, sd = sc.mc(4000, np.random.default_rng(4))
        self.assertLess(abs(mc - sc.exact()), 4 * sd / np.sqrt(4000) + 1e-5)

    def test_mantel_identity_and_invalid_genes(self):
        rng = np.random.default_rng(5)
        X = rng.normal(size=(100, 30)).astype(np.float32)
        X[:, 5] = 0.0                          # no variance: NaN row/column, dropped
        A = C.corr_rows(X)
        self.assertTrue(np.isnan(A[5, 5]))
        self.assertAlmostEqual(C.mantel(A, A), 1.0, places=5)


class TestWorlds(unittest.TestCase):
    def test_world1_modules_reassigned(self):
        rng = np.random.default_rng(10)
        n, G = 500, 120
        ya, sa, _ = module_world(n, G, 6, rng)
        yb, sb, _ = module_world(n, G, 6, rng)            # independent assignment: same map, other targets
        mask = np.zeros((n, G), bool)
        nsa, nsb = C.n_significant(ya, sa, mask), C.n_significant(yb, sb, mask)
        rec = C.analyse_pair(side("a", ya, sa, G), side("b", yb, sb, G), mask, rng.random(n) < 0.3, nsa, nsb,
                             pair="w1", stratum="T", k_list=(0, 3), jack_k=(3,), **FAST)
        r = pd.DataFrame(rec["pairs"]).set_index("k")
        self.assertGreater(r.loc[0, "rho_cov"], 0.8)
        self.assertLess(abs(r.loc[0, "rho_eff"]), 0.15)
        self.assertGreater(r.loc[3, "D"], 0.3)
        self.assertTrue(np.isfinite(r.loc[3, "se_D"]) and r.loc[3, "se_D"] > 0)
        # the exact and Monte Carlo nulls agree to Monte Carlo error
        nl = pd.DataFrame(rec["nulls"])
        m1 = nl[nl["measure"] == "M1"].dropna(subset=["exact"])
        self.assertTrue((abs(m1["mc_mean"] - m1["exact"]) < 5 * m1["mc_sd"] / np.sqrt(20) + 1e-3).all())

    def test_world2_effects_without_modules(self):
        rng = np.random.default_rng(11)
        n, G = 400, 100
        eff = rng.normal(0, 1, (n, G)).astype(np.float32)
        ya = eff + rng.normal(0, 0.5, (n, G)).astype(np.float32)
        yb = eff + rng.normal(0, 0.5, (n, G)).astype(np.float32)
        se = np.full((n, G), 0.5, np.float32)
        mask = np.zeros((n, G), bool)
        rec = C.analyse_pair(side("a", ya, se, G), side("b", yb, se, G), mask, np.zeros(n, bool),
                             C.n_significant(ya, se, mask), C.n_significant(yb, se, mask), pair="w2", stratum="T",
                             k_list=(0,), jack_k=(), **FAST)
        r = rec["pairs"][0]
        self.assertGreater(r["rho_eff"], 0.8)
        ce = pd.DataFrame(rec["ceilings"])
        self.assertTrue((ce["ceiling_minus_null"] < C.W1_CEILING_MIN).all())

    def _noise_world(self, rng, n, G, signal):
        """Every context: the same block noise covariance (6 blocks), independent draws; optional module signal
        on a different block structure (5 modules)."""
        blocks = np.arange(G) % 6
        L = 0.9 * (blocks[:, None] == blocks[None, :]) + 0.1 * np.eye(G)
        chol = np.linalg.cholesky(L + 1e-6 * np.eye(G))

        def draw(nn, scale):
            e = (rng.normal(size=(nn, G)) @ chol.T) * scale
            if signal:
                return e
            return e

        mods = np.arange(G) // (G // 5)
        assign = rng.integers(0, 5, n)
        S = signal * (mods[None, :] == assign[:, None]).astype(np.float64) * rng.normal(1, 0.2, (n, 1))
        return draw, S

    def test_world3_universal_noise_w5_and_w4(self):
        rng = np.random.default_rng(12)
        n, G = 400, 60
        nomask = C.MaskCSR.from_lists([[]] * n, G)
        ss = lambda name, raw: C.SSide(name, raw, nomask if raw.shape[0] == n else
                                       C.MaskCSR.from_lists([[]] * raw.shape[0], G), np.linspace(1, 8, G))
        draw, S = self._noise_world(rng, n, G, signal=0.0)
        ref = (S + draw(n, 0.5)).astype(np.float32)
        other = (S + draw(n, 0.5)).astype(np.float32)
        ntc = draw(300, 0.5).astype(np.float32)
        strata = C.pair_strata(np.zeros(n), np.zeros(n), np.zeros(n, bool))
        w5 = C.analyse_w5(ss("k562", ref), ss("d", other), ss("ntc", ntc), strata, k_list=(0,), seeds=(0,))
        r = w5[0]
        self.assertGreater(r["Q_ref"], 0.3)             # the noise structure alone looks "conserved" ...
        self.assertFalse(r["diff"] - C.Z95 * r["se_diff"] > 0)   # ... and W5 does not let it pass
        # with a real shared module signal on top, W5 passes
        draw, S = self._noise_world(rng, n, G, signal=1.5)
        ref = (S + draw(n, 0.5)).astype(np.float32)
        other = (S + draw(n, 0.5)).astype(np.float32)
        w5 = C.analyse_w5(ss("k562", ref), ss("d", other), ss("ntc", draw(300, 0.5).astype(np.float32)), strata,
                          k_list=(0,), seeds=(0,))
        self.assertGreater(w5[0]["diff"] - C.Z95 * w5[0]["se_diff"], 0)
        # W4: two cell halves with independent noise; the cross-half matrix drops the shared noise structure
        half_a = (S + draw(n, 0.7)).astype(np.float32)
        half_b = (S + draw(n, 0.7)).astype(np.float32)
        w4 = C.analyse_w4(ss("va", half_a), ss("vb", half_b), ss("k562", ref), strata, k_list=(0,), seeds=(0,),
                          n_gene_perm=10)
        d = w4[0]["diff_one_half_minus_cross"]
        self.assertTrue(not np.isfinite(d) or abs(d) > C.W4_MAX_DIFF, d)

    def test_streamed_preparation_matches(self):
        rng = np.random.default_rng(14)
        n, G = 300, 50
        raw = rng.normal(size=(n, G)).astype(np.float32)
        raw[:, :10] += rng.normal(size=(n, 1)).astype(np.float32)
        raw[rng.random((n, G)) < 0.02] = np.nan
        lists = [[i % G] for i in range(n)]
        masks = C.MaskCSR.from_lists(lists, G)
        p = C.prepare(raw, masks.dense(), None, 3)
        st = C.prepare_stats(C.SSide("x", raw, masks, np.zeros(G)), 3, block=64)
        for k in (0, 3):
            a = C.project(p.u, p.V, k)
            b = C.u_rows(C.SSide("x", raw, masks, np.zeros(G)), st, np.arange(n), k)
            self.assertLess(float(np.abs(a - b).max()), 1e-4, k)

    def test_kappa_fit_recovers_miscalibration(self):
        rng = np.random.default_rng(13)
        n, G = 600, 80
        sig = rng.normal(0, 1, (n, G)) * rng.uniform(0.3, 1.5, (n, 1))
        se = rng.uniform(0.3, 0.8, (n, G))
        true_kappa = 1.5
        A = (sig + rng.normal(size=(n, G)) * se * np.sqrt(true_kappa)).astype(np.float32)
        B = (sig + rng.normal(size=(n, G)) * se * np.sqrt(true_kappa)).astype(np.float32)
        mask = np.zeros((n, G), bool)
        pa, pb = C.prepare(A, mask, se.astype(np.float32), 0), C.prepare(B, mask, se.astype(np.float32), 0)
        cos = np.einsum("ij,ij->i", pa.u, pb.u)
        w = np.ones(G)
        EA, EB = pa.zn2, pb.zn2
        NA, NB = pa.d2 @ w, pb.d2 @ w
        k, status = C.fit_kappa(cos, EA, NA, EB, NB)
        self.assertEqual(status, "ok")
        self.assertLess(abs(k - true_kappa), 0.25, k)


class TestM3a(unittest.TestCase):
    def _world(self, seed=20):
        rng = np.random.default_rng(seed)
        G, extra, n_mod = 150, 2250, 4
        ncol = G + extra
        mod = rng.integers(0, n_mod, ncol)
        tids = np.arange(ncol)                      # target i knocks down gene column i
        xpos = {int(t): int(t) for t in tids}
        data = {}
        for c in ("h", "s1", "s2"):
            amp = np.where(tids % 3 == 0, 2.0, 0.5).astype(np.float32)[:, None]   # a third respond
            y = -amp * (mod[None, :] == mod[tids][:, None]).astype(np.float32)
            y[np.arange(ncol), tids] -= 2.0            # the knocked-down gene itself
            y += rng.normal(0, 0.4, y.shape).astype(np.float32)
            se = np.full(y.shape, 0.4, np.float32)
            lists = [[int(t)] + ([int(t) + 1] if int(t) % 7 == 0 and t + 1 < ncol else []) for t in tids]
            masks = C.MaskCSR.from_lists(lists, ncol)
            dm = masks.dense(None, np.arange(G))
            data[c] = C.Ctx(c, tids.copy(), y.astype(np.float16), se.astype(np.float16), masks,
                            C.n_significant(y[:, :G], se[:, :G], dm), np.ones(ncol), 1.0)
        logc = {int(t): float(v) for t, v in zip(tids, rng.normal(3, 1, ncol))}
        ess = {int(t): bool(t % 5 == 0) for t in tids}
        return data, xpos, logc, ess, G, mod

    def test_routes_and_leakage_canary(self):
        data, xpos, logc, ess, G, mod = self._world()
        dbg1 = {}
        rec = C.m3a_context("h", data, ["s1", "s2"], G=G, xpos_of=xpos, logcpm_h_x=logc, essential_of=ess,
                            seeds=(0,), n_boot=200, debug=dbg1)
        m = pd.DataFrame(rec["m3a"]).set_index("route")
        for route in ("relation", "inline", "effect"):
            self.assertGreater(m.loc[route, "lo"], 0, route)
        self.assertGreater(rec["counts"]["eligible"], 20)
        test_ids = np.unique(pd.DataFrame(rec["m3a_targets"])["target_id"])
        # canary: overwrite the test targets' rows everywhere (n_sig kept, so the same test split)
        rng = np.random.default_rng(99)
        for c in data.values():
            rows = np.flatnonzero(np.isin(c.tids, test_ids))
            c.raw[rows] = rng.normal(0, 50, (rows.size, c.raw.shape[1])).astype(np.float16)
        # and a training row whose cis window holds x gets a wild value at x (masked, so beta must not move)
        cis_rows = [int(t) for t in data["s1"].tids if int(t) % 7 == 0 and int(t) + 1 in set(test_ids.tolist())
                    and int(t) not in set(test_ids.tolist())]
        for r in cis_rows:
            data["s1"].raw[r, r + 1] = 999.0
        dbg2 = {}
        rec2 = C.m3a_context("h", data, ["s1", "s2"], G=G, xpos_of=xpos, logcpm_h_x=logc, essential_of=ess,
                             seeds=(0,), n_boot=200, debug=dbg2)
        for c in ("h", "s1", "s2"):
            for key in ("mu", "sd", "beta"):
                a, b = dbg1[0][c][key], dbg2[0][c][key]
                self.assertTrue(np.array_equal(np.nan_to_num(a, nan=-7), np.nan_to_num(b, nan=-7)), (c, key))
        self.assertTrue(len(cis_rows) > 0)
        m2 = pd.DataFrame(rec2["m3a"]).set_index("route")
        self.assertEqual(m.loc["relation", "n_test"], m2.loc["relation", "n_test"])


class TestHelpers(unittest.TestCase):
    def test_gstar_selection(self):
        names = list(C.GSTAR_BASAL) + ["hipsci_fit"]
        basal = np.full((len(names), 6), 30.0)
        basal[0, 1] = 19.0          # below 20 in k562
        basal[9, 2] = np.nan        # unknown in C
        basal[10, 3] = 1.0          # low only in a row outside G*'s list: kept
        got = C.select_gstar(basal, names, np.array([0, 1, 2, 3, 4, 5]))
        self.assertEqual(got.tolist(), [0, 3, 4, 5])

    def test_coord_mask(self):
        coords = pd.DataFrame({"chrom": ["chr1", "chr1", "chr1", "chr2"], "tss": [1000, 5900, 7000, 1000]},
                              index=["T1", "G1", "G2", "G3"])
        m = C.coord_mask(["T1", "G3"], ["G1", "G2", "G3", "T1"], coords, 5000)
        d = m.dense()
        self.assertEqual(d[0].tolist(), [True, False, False, True])   # own gene and G1 at 4.9 kb; G2 at 6 kb out
        self.assertEqual(d[1].tolist(), [False, False, True, False])

    def test_pairs(self):
        self.assertEqual(len(C.p9_pairs()), 9)
        pa = C.part_a_pairs()
        self.assertEqual(sum(1 for s, _, _ in pa if s == "REP"), 11)
        hp = C.hipsci_pairs()
        self.assertEqual(sum(1 for s, _, _ in hp if s == "S0"), 5)
        self.assertEqual(sum(1 for s, _, _ in hp if s == "S3"), 100)

    def test_halves_and_blocks(self):
        rng = np.random.default_rng(0)
        strata = rng.integers(0, 7, 101)
        h1 = C.stratified_halves(strata, rng)
        self.assertLessEqual(abs(int(h1.sum()) - int((~h1).sum())), 1)
        b = C.make_blocks(101, rng)
        self.assertEqual(sorted(np.unique(b).tolist()), list(range(20)))


def _tables(D=0.3, se=0.05, rho=0.4, delta=0.05, lo=0.01, ceiling=0.2, sqrt_r=0.5):
    pairs, ceil, m3a, counts = [], [], [], []
    for a, b in C.p9_pairs():
        p = f"{a}|{b}"
        counts.append({"pair": p, "stratum": "P9", "n_P": 500})
        for s in C.SEEDS:
            for gs in ("gstar", "gsig"):
                pairs.append({"pair": p, "stratum": "P9", "a": a, "b": b, "gene_set": gs, "subset": "all", "k": 3,
                              "seed": s, "D": D, "se_D": se, "rho_cov": rho, "rho_eff": rho - D})
                for c in (a, b):
                    ceil.append({"pair": p, "stratum": "P9", "context": c, "gene_set": gs, "subset": "all", "k": 3,
                                 "seed": s, "ceiling_minus_null": ceiling, "mean_sqrt_r": sqrt_r})
    counts.append({"pair": "k562|k562ess", "stratum": "S1", "n_P": 500})
    for s in C.SEEDS:
        pairs.append({"pair": "k562|k562ess", "stratum": "S1", "a": "k562", "b": "k562ess", "gene_set": "gstar",
                      "subset": "all", "k": 3, "seed": s, "D": 0, "se_D": 0.1, "rho_cov": 0.9, "rho_eff": 0.9})
        for h in C.P9_CONTEXTS:
            for route in ("relation", "inline", "effect", "combined", "gain_combined_minus_effect"):
                m3a.append({"h": h, "seed": s, "route": route, "delta": delta, "lo": lo, "hi": delta + 0.05})
    s0 = pd.DataFrame([{"pair": "vA|vB", "k": 3, "seed": s, "n_targets": 500, "rho_cov": 0.95, "rho_eff": 0.95}
                       for s in C.SEEDS])
    w4 = pd.DataFrame([{"k": 3, "seed": s, "diff_one_half_minus_cross": 0.02} for s in C.SEEDS])
    w5 = pd.DataFrame([{"pair": f"k562|{c}", "k": 3, "seed": s, "diff": 0.1, "se_diff": 0.01}
                       for c in ("cd4_Rest", "orion_hct116", "kolf") for s in C.SEEDS])
    return pd.DataFrame(pairs), pd.DataFrame(ceil), pd.DataFrame(m3a), pd.DataFrame(counts), s0, w4, w5


class TestDecide(unittest.TestCase):
    def run_rule(self, kappa=1.0, **kw):
        p, c, m, n, s0, w4, w5 = _tables(**kw)
        return C.decide(p, c, m, kappa_pb=kappa, w4=w4, w5=w5, s0_pairs=s0, counts=n)

    def test_yes(self):
        v = self.run_rule()
        self.assertEqual((v["mappa"], v["uso"]), ("sì", "sì"))
        self.assertTrue(v["verdetto"].startswith("sì"))
        self.assertTrue(v["aggiunge_al_trasferimento"])

    def test_no_map(self):
        v = self.run_rule(D=-0.1)
        self.assertEqual(v["mappa"], "no")
        self.assertEqual(v["verdetto"], "no")

    def test_no_use(self):
        v = self.run_rule(lo=-0.01)
        self.assertEqual(v["uso"], "no")
        self.assertEqual(v["verdetto"], "no")

    def test_w1_inconclusive(self):
        v = self.run_rule(ceiling=0.01)
        self.assertEqual(v["verdetto"], "inconclusivo")

    def test_w3_pending_map(self):
        v = self.run_rule(kappa=3.0)
        self.assertEqual(v["mappa"], "inconclusiva")
        self.assertEqual(v["verdetto"], "inconclusivo")

    def test_w5_fail_is_no(self):
        p, c, m, n, s0, w4, w5 = _tables()
        w5["diff"] = 0.0
        v = C.decide(p, c, m, kappa_pb=1.0, w4=w4, w5=w5, s0_pairs=s0, counts=n)
        self.assertEqual(v["mappa"], "no")

    def test_w2_fail(self):
        p, c, m, n, s0, w4, w5 = _tables()
        s0["rho_cov"] = 0.1
        p.loc[p["stratum"] == "S1", "rho_cov"] = 0.1
        v = C.decide(p, c, m, kappa_pb=1.0, w4=w4, w5=w5, s0_pairs=s0, counts=n)
        self.assertEqual(v["verdetto"], "inconclusivo")

    def test_pending_part_b(self):
        p, c, m, n, *_ = _tables()
        v = C.decide(p, c, m, kappa_pb=None, w4=None, w5=None, s0_pairs=None, counts=n)
        self.assertEqual(sorted(v["pending"]), ["W2", "W3", "W4", "W5"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
