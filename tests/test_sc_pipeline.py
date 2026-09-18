"""Tests for the single-cell pipeline of 2026-09-17 (stages 71-76).

Each test pins a way these stages could return a plausible wrong number:

* a streamed pass over a dense h5ad that mis-assigns rows to perturbations, or
  whose md5 is not the md5 of the file;
* a fast rank-sum test that drifts from the Mann-Whitney statistic with tie
  correction that the scorer's CPU backend computes;
* a generator that copies control cells, or emits non-integer counts;
* a cis prior that puts an effect on a gene far from the target.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.de_tools import ReferencePool, bh, fast_scorer_de  # noqa: E402
from vcc2026.generator import ControlModel, bulk_lognorm  # noqa: E402
from vcc2026.predictor_sc import CisModel, SourceEffects, assemble_log_fc  # noqa: E402
from vcc2026.sc_effects import eb_shrink, fraction_stats, log_effect  # noqa: E402
from vcc2026.sc_stream import GroupAccumulator, dense_layout, read_frame, stream_dense_rows  # noqa: E402


def write_old_style_h5ad(path: Path, x: np.ndarray, labels: list[str], genes: list[str]) -> None:
    """A dense, contiguous X with an anndata-0.7 style obs (codes + __categories)."""
    with h5py.File(path, "w") as f:
        f.create_dataset("X", data=x.astype("<f4"))
        obs = f.create_group("obs")
        cats = sorted(set(labels))
        obs.create_dataset("gene", data=np.array([cats.index(v) for v in labels], dtype=np.int16))
        obs.create_group("__categories").create_dataset("gene", data=np.array(cats, dtype="S"))
        obs.create_dataset("_index", data=np.array([f"cell{i}" for i in range(len(labels))], dtype="S"))
        obs.attrs["_index"] = "_index"
        obs.attrs["column-order"] = np.array(["gene"], dtype="S")
        obs.attrs["encoding-type"] = "dataframe"
        var = f.create_group("var")
        var.create_dataset("_index", data=np.array(genes, dtype="S"))
        var.attrs["_index"] = "_index"
        var.attrs["column-order"] = np.array([], dtype="S")
        var.attrs["encoding-type"] = "dataframe"


class StreamingTests(unittest.TestCase):
    def test_stream_and_accumulate_match_direct_reads(self):
        rng = np.random.default_rng(0)
        x = rng.poisson(1.5, size=(97, 13)).astype(np.float32)
        x[4] = 0  # an empty cell must not divide by zero
        labels = [f"g{i % 7}" for i in range(97)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dense.h5ad"
            write_old_style_h5ad(path, x, labels, [f"G{j}" for j in range(13)])
            obs = read_frame(h5py.File(path, "r")["obs"])
            self.assertEqual(list(obs["gene"].astype(str)), labels)
            layout = dense_layout(path)
            self.assertEqual((layout.n_obs, layout.n_vars), (97, 13))
            codes = np.array([int(v[1:]) for v in labels])
            acc = GroupAccumulator(7, 13)
            info: dict = {}
            seen = 0
            for row0, rows in stream_dense_rows(layout, block_bytes=13 * 4 * 10, result=info):
                self.assertEqual(row0, seen)
                acc.add(codes[row0:row0 + rows.shape[0]], rows)
                seen += rows.shape[0]
            self.assertEqual(seen, 97)
            self.assertEqual(info["md5"], hashlib.md5(path.read_bytes()).hexdigest())
            lib = x.sum(1, keepdims=True).astype(np.float64)
            frac = x / np.where(lib > 0, lib, 1.0)
            for c in range(7):
                m = codes == c
                np.testing.assert_allclose(acc.sums[c], x[m].sum(0))
                np.testing.assert_allclose(acc.frac_sums[c], frac[m].sum(0), rtol=1e-12)
                np.testing.assert_allclose(acc.frac_sq_sums[c], (frac[m] ** 2).sum(0), rtol=1e-12)
                np.testing.assert_array_equal(acc.detect[c], (x[m] > 0).sum(0))
                self.assertEqual(acc.n_cells[c], m.sum())

    def test_chunked_x_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chunked.h5ad"
            with h5py.File(path, "w") as f:
                f.create_dataset("X", data=np.zeros((10, 3), "<f4"), chunks=(5, 3), compression="gzip")
            with self.assertRaises(ValueError):
                dense_layout(path)


class FastDETests(unittest.TestCase):
    def test_rank_sum_matches_mann_whitney_with_ties(self):
        from scipy.stats import mannwhitneyu

        rng = np.random.default_rng(1)
        n_genes = 6
        ctrl = sp.csr_matrix(rng.poisson(3.0, size=(300, n_genes)).astype(np.float32))
        grp = sp.csr_matrix(rng.poisson(3.6, size=(40, n_genes)).astype(np.float32))
        genes = np.array([f"G{j}" for j in range(n_genes)])
        pool = ReferencePool(ctrl, genes, cpm_gate=-1.0)
        p, lfc = pool.test(grp)

        def logcpm(m):  # scanpy's arithmetic: x / (library / 1e6)
            d = m.toarray().astype(np.float64)
            return np.log1p(d / (d.sum(1, keepdims=True) / 1e6))

        lc, lg = logcpm(ctrl), logcpm(grp)
        for j in range(n_genes):
            ref = mannwhitneyu(lg[:, j], lc[:, j], alternative="two-sided", method="asymptotic",
                               use_continuity=False).pvalue
            self.assertAlmostEqual(np.log10(p[j]), np.log10(ref), places=10)
        cpm = lambda m: (m.toarray().astype(np.float64) / (m.toarray().astype(np.float64).sum(1, keepdims=True) / 1e6)).mean(0)  # noqa: E731
        np.testing.assert_allclose(lfc, np.log2((cpm(grp) + 1e-9) / (cpm(ctrl) + 1e-9)), rtol=1e-9, atol=1e-12)

    def test_gate_and_bh_are_per_target(self):
        rng = np.random.default_rng(2)
        ctrl = sp.csr_matrix(rng.poisson(0.5, size=(200, 8)).astype(np.float32))
        cells = sp.csr_matrix(rng.poisson(0.5, size=(60, 8)).astype(np.float32))
        pool = ReferencePool(ctrl, np.array([f"G{j}" for j in range(8)]))
        table = fast_scorer_de(cells, np.repeat(["a", "b"], 30), pool)
        self.assertEqual(table.height, 2 * pool.kept.size)
        for t in ("a", "b"):
            sub = table.filter(table["target"] == t)
            np.testing.assert_allclose(sub["p_adj"].to_numpy(), bh(sub["p_value"].to_numpy()))

    def test_bh(self):
        p = np.array([0.01, 0.04, 0.03, 0.5])
        # sorted p*n/rank = 0.04, 0.06, 0.0533, 0.5; the step-up minimum lifts rank 1 and 2 only
        np.testing.assert_allclose(bh(p), [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.5], rtol=1e-12)


class GeneratorTests(unittest.TestCase):
    def test_counts_are_new_integers_on_the_same_axis(self):
        rng = np.random.default_rng(3)
        base = rng.gamma(0.6, 1.0, size=(1, 400))
        lib = rng.integers(2000, 6000, size=(600, 1))
        ctrl = sp.csr_matrix(rng.poisson(base / base.sum() * lib).astype(np.float32))
        model = ControlModel(n_hvg=100, n_pcs=5, n_components=3, knn=10, state="kde", seed=0)
        model.fit(ctrl, log=lambda *_: None)
        out = model.sample(200, np.random.default_rng(4))
        self.assertEqual(out.shape, (200, 400))
        self.assertTrue(np.all(out.data == np.floor(out.data)) and np.all(out.data > 0))
        real_rows = {tuple(r) for r in ctrl.toarray().astype(int)}
        copies = sum(tuple(r) in real_rows for r in out.toarray().astype(int))
        self.assertEqual(copies, 0)
        # a knocked-down gene goes down, the others keep the control's pseudobulk
        fc = np.ones(400)
        top = int(np.argmax(base))
        fc[top] = 0.2
        down = model.sample(400, np.random.default_rng(5), fold_change=fc)
        self.assertLess(down[:, top].sum() / down.sum(), 0.5 * ctrl[:, top].sum() / ctrl.sum())
        self.assertLess(np.abs(bulk_lognorm(out) - bulk_lognorm(ctrl)).mean(), 0.2)


class PredictorTests(unittest.TestCase):
    def test_cis_prior_is_distance_limited_and_fill_mode_respects_measurements(self):
        coords = pd.DataFrame({
            "chrom": ["chr1"] * 5 + ["chr2"],
            "tss": [1000, 1400, 9000, 60000, 2200, 1500],
            "strand": [1, -1, 1, 1, 1, 1],
        }, index=["T", "NEAR", "MID", "FAR", "S2", "OTHERCHR"])
        genes = np.array(["NEAR", "MID", "FAR", "OTHERCHR", "T", "S2"])
        raw = np.zeros((2, 6))
        raw[0, 0] = -1.0   # target S2's gene NEAR (800 bp from S2) goes down; T is 1.2 kb away
        src = SourceEffects(genes, ["S2", "X"], raw.copy(), raw, np.ones((2, 6)), np.array([50, 50]),
                            np.full(6, 1e-3))
        cis = CisModel(edges=(0, 1000, 20000)).fit(src, coords)
        self.assertAlmostEqual(cis.by_bin[0], -1.0)
        vec = cis.vector("T", genes, coords)
        self.assertAlmostEqual(vec[0], -1.0)          # NEAR, 400 bp from T
        self.assertEqual(vec[2], 0.0)                 # FAR, 59 kb
        self.assertEqual(vec[3], 0.0)                 # other chromosome
        self.assertEqual(vec[4], 0.0)                 # the target itself
        measured = SourceEffects(genes, ["T"], np.array([[0.3, 0, 0, 0, -2.0, 0]]),
                                 np.zeros((1, 6)), np.ones((1, 6)), np.array([50]), np.full(6, 1e-3))
        fill = assemble_log_fc("T", genes, src=measured, a_transfer=1.0, cis=cis, coords=coords, a_cis=1.0)
        self.assertAlmostEqual(fill[0], 0.3)          # measured gene keeps its measurement
        added = assemble_log_fc("T", genes, src=measured, a_transfer=1.0, cis=cis, coords=coords,
                                a_cis=1.0, cis_mode="add")
        self.assertAlmostEqual(added[0], -0.7)

    def test_common_term_averages_other_targets_only(self):
        """The shared response is the mean over the source's targets MINUS the excluded ones.

        T1 and T2 share gene G0 going up four-fold; T3 is excluded and moves G1 alone. If the
        exclusion leaked, G1 would move; if the vector were misaligned, G0 would land elsewhere.
        """
        from vcc2026.predictor_sc import common_from_bulk

        genes = ["G0", "G1", "G2", "G3"]
        base = np.array([10.0, 10.0, 10.0, 10.0])
        rows = {"1_non-targeting_x_y": base, "2_non-targeting_x_y": base,
                "3_T1_P1_ENSG1": base * [4, 1, 1, 1], "4_T2_P1_ENSG2": base * [4, 1, 1, 1],
                "5_T3_P1_ENSG3": base * [1, 8, 1, 1]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bulk.h5ad"
            with h5py.File(path, "w") as f:
                f.create_dataset("X", data=np.vstack(list(rows.values())).astype("<f4"))
                obs = f.create_group("obs")
                obs.create_dataset("gene_transcript", data=np.array(list(rows), dtype="S"))
                obs.create_dataset("num_cells_filtered", data=np.array([5000, 5000, 4000, 4000, 4000], dtype=float))
                var = f.create_group("var")
                var.create_dataset("_index", data=np.array(genes, dtype="S"))
                var.create_dataset("gene_name", data=np.array(genes, dtype="S"))
                var.attrs["_index"] = "_index"
                var.attrs["column-order"] = np.array(["gene_name"], dtype="S")
                var.attrs["encoding-type"] = "dataframe"
            vec, info = common_from_bulk(path, np.array(["G1", "ZZ", "G0"]), exclude=["T3"])
            leaky, _ = common_from_bulk(path, np.array(["G1", "ZZ", "G0"]), exclude=[])
        self.assertEqual(info["n_targets"], 2)
        self.assertEqual(info["n_excluded"], 1)
        self.assertEqual(vec[1], 0.0)                                      # not measured by the source
        self.assertAlmostEqual(vec[2], np.log((40 / 70) / 0.25), places=2)  # G0: 4x in T1 and T2
        self.assertAlmostEqual(vec[0], np.log((10 / 70) / 0.25), places=2)  # G1: composition only
        self.assertGreater(leaky[0] - vec[0], 0.3)                         # T3 would have lifted G1

    def test_shuffle_control_never_keeps_a_target_and_is_reproducible(self):
        from vcc2026.predictor_sc import derangement

        items = sorted(f"T{i}" for i in range(300))
        m = derangement(items, 2027)
        self.assertEqual(sorted(m), items)
        self.assertEqual(sorted(m.values()), items)       # a permutation: every effect used once
        self.assertFalse(any(k == v for k, v in m.items()))
        self.assertEqual(m, derangement(items, 2027))       # both sources get the same partners
        self.assertNotEqual(m, derangement(items, 2028))
        self.assertEqual(derangement(["A", "B"], 1), {"A": "B", "B": "A"})
        with self.assertRaises(ValueError):
            derangement(["A"], 1)

    def test_eb_shrinkage_keeps_signal_and_damps_noise(self):
        rng = np.random.default_rng(6)
        ctrl = sp.csr_matrix(rng.poisson(5.0, size=(2000, 50)).astype(np.float32))
        lam = np.full(50, 5.0)
        lam[:5] = 20.0
        grp = sp.csr_matrix(rng.poisson(lam, size=(100, 50)).astype(np.float32))
        eff, se = log_effect(fraction_stats(grp), fraction_stats(ctrl))
        shrunk, tau2 = eb_shrink(eff, se, np.ones(50, bool))
        self.assertTrue(np.all(shrunk[:5] > 0.8))
        self.assertLess(np.abs(shrunk[5:]).mean(), np.abs(eff[5:]).mean())
        self.assertGreater(tau2, 0)


class BenchComponentTests(unittest.TestCase):
    def test_components_reproduce_the_scored_fidelity(self):
        """k / max(n_pred, n_conf) from `direction_components` IS the fidelity the scorer reports.

        The components rebuild cell_eval2's private PreparedDE outside `compute_metrics`; if that
        reconstruction drifted (another target resolution, another threshold), the per-target
        volume and precision read from it would describe a metric nobody scored.
        """
        from vcc2026.bench import Bench

        rng = np.random.default_rng(11)
        targets = ["T1", "T2", "T3"]
        genes = np.array(targets + [f"G{i}" for i in range(77)])
        base = rng.uniform(2.0, 12.0, size=genes.size)
        blocks, labels, truth_fc = [], [], {}
        for t in targets:
            fc = np.ones(genes.size)
            idx = rng.choice(np.arange(3, genes.size), size=20, replace=False)
            fc[idx[:10]], fc[idx[10:]] = 2.5, 0.4
            fc[targets.index(t)] = 0.15
            truth_fc[t] = fc
            blocks.append(rng.poisson(base * fc, size=(90, genes.size)))
            labels += [t] * 90
        blocks.append(rng.poisson(base, size=(400, genes.size)))
        labels += ["non-targeting"] * 400
        x = sp.csr_matrix(np.vstack(blocks).astype(np.float32))
        labels = np.array(labels)
        target_rows = {t: np.flatnonzero(labels == t) for t in targets}
        ctrl_rows = np.flatnonzero(labels == "non-targeting")

        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(x, target_rows, ctrl_rows, genes, Path(tmp), seed=3)
            pred, pred_labels = [], []
            for t in targets:
                fc = truth_fc[t].copy()
                flip = rng.choice(np.flatnonzero(fc != 1.0), size=6, replace=False)
                fc[flip] = 1.0 / fc[flip]             # some wrong signs, so k < n_pred
                pred.append(rng.poisson(base * fc, size=(bench.n_pred(t), genes.size)))
                pred_labels += [t] * bench.n_pred(t)
            res = bench.score("arm_x", sp.csr_matrix(np.vstack(pred).astype(np.float32)), np.array(pred_labels))

            comp = pd.read_csv(Path(tmp) / "components_arm_x.csv").set_index("target")
            per = pd.read_csv(Path(tmp) / "per_pert_arm_x.csv")
        fid = per[per.metric == "de_wilcoxon_direction_fidelity_yield_raw"].set_index("perturbation")["value"]
        self.assertEqual(sorted(comp.index), targets)
        self.assertTrue((comp.n_pred > 0).all() and (comp.n_conf > 0).all())
        self.assertTrue((comp.k < comp.n_pred).any())
        for t in targets:
            expect = comp.loc[t, "k"] / max(comp.loc[t, "n_pred"], comp.loc[t, "n_conf"])
            self.assertAlmostEqual(float(fid[t]), float(expect), places=12)
        self.assertIn("components", res)
        self.assertAlmostEqual(res["components"]["precision_pooled"], comp.k.sum() / comp.n_pred.sum())


if __name__ == "__main__":
    unittest.main()
