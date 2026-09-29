"""Trial-01's generator in the K562 bench (stage 73), with the semantics of stage 45.

Each test pins a way the bench could score a generator that is not the one the submissions use,
or score the right generator under the wrong name:

* T1 `inference.trial01_cells` drifts from stage 45's per-block sequence (read_effects, then
  predicted_profile, resample_library_sizes, sample_counts on one stream): compared bit for bit
  with the file stage 45's own `generate` writes, Poisson and per-gene dispersion;
* T2 with every gene observed and no clip, the profile stops being basal x exp(lfc), stage 75's g0;
* T3 the g0d arm is not reproducible, is Poisson in disguise, or ignores its per-gene dispersion;
* T4 an unknown generator prefix is scored as ControlModel, or seeds are named ambiguously;
* T5 `bench.load_effects` drops an observed pair whose value is 0, which production keeps;
* T6 stage 73's main does not run g0/g0d arms per generator seed on a stage-71 folder;
* T6b without the new arms and flags, stage 73 no longer reproduces what it scored before this
  change (commit 5652822), the promise that b002 stays reproducible.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.bench import load_effects  # noqa: E402
from vcc2026.inference import BasalProfile, predicted_profile, trial01_cells  # noqa: E402
from vcc2026.sampling import sample_counts  # noqa: E402

BEFORE = "5652822"      # the last commit before `g0:` entered stage 73


def load_stage(number_name: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, REPO / "scripts" / f"{number_name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module            # a dataclass looks its module up while it is defined
    spec.loader.exec_module(module)
    return module


class Axis:
    """What stage 45's `generate` and `read_effects` read of `genes.official_axis()`."""

    def __init__(self, symbols):
        self.symbols = list(symbols)

    def __len__(self):
        return len(self.symbols)


def synthetic_effects(path: Path, targets, genes, rng) -> None:
    """A stage-100-shaped npz: ln lfc float32, an observed mask with observed zeros and one
    unobserved nonzero, a gene order other than the axis, a gene off the axis, extremes past the clip."""
    order = list(rng.permutation(genes)) + ["OFF_AXIS"]
    lfc = rng.normal(0.0, 0.6, size=(len(targets), len(order))).astype(np.float32)
    observed = rng.random(lfc.shape) < 0.7
    lfc[~observed] = 0.0
    observed[:, :3] = True
    lfc[:, :3] = 0.0                               # observed pairs whose value is 0
    lfc[0, 5], observed[0, 5] = -6.0, True         # |log2| > 6: clipped
    lfc[1, 6], observed[1, 6] = 0.4, False         # a value the mask says not to apply
    np.savez_compressed(path, targets=np.array(targets), genes=np.array(order), lfc=lfc, observed=observed)


def synthetic_basal(n_genes: int, rng, context: str = "A") -> BasalProfile:
    lib = rng.integers(3000, 9000, size=250).astype(np.int64)
    profile = rng.gamma(0.6, 40.0, size=n_genes) * 250
    profile[:2] = 0.0                              # genes the controls never saw
    return BasalProfile(context=context, profile=profile, library_sizes=lib, n_cells=lib.size,
                        nnz_per_cell=rng.integers(20, n_genes, size=lib.size).astype(np.int32))


def read_blocks(path: Path, n_blocks: int, n: int, n_genes: int) -> list[sp.csr_matrix]:
    with h5py.File(path, "r") as f:
        whole = sp.csr_matrix((f["X/data"][:], f["X/indices"][:], f["X/indptr"][:]), shape=(n_blocks * n, n_genes))
    return [whole[i * n:(i + 1) * n] for i in range(n_blocks)]


def normalised(block: sp.csr_matrix) -> sp.csr_matrix:
    """What `SubmissionWriter.add` stores of a block."""
    block = block.tocsr().copy()
    block.eliminate_zeros()
    block.sort_indices()
    return block


class TestTrial01CellsMatchesStage45(unittest.TestCase):
    """T1: the bench's generator is stage 45's, bit for bit."""

    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage("45_generate_prediction", "stage45_for_bench")

    def run_both(self, gene_phi: dict):
        rng = np.random.default_rng(7)
        genes = [f"G{i:03d}" for i in range(60)]
        targets = ["T1", "T2", "T3", "T4"]
        axis = Axis(genes)
        basal = synthetic_basal(len(genes), rng)
        ch = SimpleNamespace(pert_col="target_gene", context_col="context",
                             max_stored_per_cell=13_194, max_counts_per_cell=1_000_000)
        n = 37
        with tempfile.TemporaryDirectory() as d:
            npz = Path(d) / "effects_A.npz"
            synthetic_effects(npz, targets, genes, rng)
            with contextlib.redirect_stdout(io.StringIO()):
                predictions = self.stage.read_effects({"A": npz}, targets, axis, 1.0)
                self.stage.generate(Path(d) / "prediction.h5ad", axis, ch, ("A",), targets, {"A": basal},
                                    predictions, gene_phi, None, n, np.random.default_rng(20260912))
            written = read_blocks(Path(d) / "prediction.h5ad", len(targets), n, len(genes))
            bench_side = load_effects([f"x={npz}"], genes, with_observed=True)["x"]
        stream = np.random.default_rng(20260912)
        ours = [trial01_cells(basal.profile, *bench_side[t], basal.library_sizes, n, stream,
                              max_stored_per_cell=ch.max_stored_per_cell, max_counts_per_cell=ch.max_counts_per_cell,
                              overdispersion=gene_phi.get("A"))[0] for t in targets]
        return written, ours

    def assert_identical(self, written, ours):
        for w, o in zip(written, ours):
            o = normalised(o)
            np.testing.assert_array_equal(w.indptr, o.indptr)
            np.testing.assert_array_equal(w.indices, o.indices)
            np.testing.assert_array_equal(w.data, o.data.astype(np.float32))

    def test_poisson_blocks_are_the_bits_stage_45_writes(self):
        written, ours = self.run_both({})
        self.assertGreater(sum(b.nnz for b in written), 0)
        self.assert_identical(written, ours)

    def test_per_gene_dispersion_blocks_are_the_bits_stage_45_writes(self):
        phi = np.linspace(0.0, 1.5, 60)
        phi[::4] = 0.0
        written, ours = self.run_both({"A": phi})
        self.assert_identical(written, ours)

    def test_the_inline_sequence_of_stage_45(self):
        """The same, against stage 45's lines 224-232 written out: ln to log2, profile, libraries, counts."""
        rng = np.random.default_rng(3)
        basal = synthetic_basal(40, rng)
        lfc = rng.normal(0, 1.0, 40).astype(np.float32)
        observed = rng.random(40) < 0.6
        a, b = np.random.default_rng(11), np.random.default_rng(11)
        delta = 1.0 * lfc / np.log(2.0)
        profile, detail = predicted_profile(basal.profile, delta, observed)
        libs = np.asarray(a.choice(basal.library_sizes, size=25, replace=True)).astype(np.int64)
        want = sample_counts(profile, libs, a, max_stored_per_cell=13_194, max_counts_per_cell=1_000_000)
        got, got_detail = trial01_cells(basal.profile, lfc, observed, basal.library_sizes, 25, b,
                                        max_stored_per_cell=13_194, max_counts_per_cell=1_000_000)
        self.assertEqual((want != got).nnz, 0)
        self.assertEqual(detail, got_detail)
        self.assertEqual(a.integers(1 << 30), b.integers(1 << 30))    # the stream advanced the same way


class TestProfileWithoutMaskOrClip(unittest.TestCase):
    """T2: every gene observed and |ln| < 3 -> basal x exp(lfc) up to a scalar, which is stage 75's g0."""

    def test_the_profile_is_basal_times_exp_lfc(self):
        rng = np.random.default_rng(5)
        basal = rng.gamma(0.8, 30.0, size=200) + 0.5
        lfc = rng.uniform(-2.9, 2.9, size=200)
        profile, detail = predicted_profile(basal, lfc / np.log(2.0), np.ones(200, dtype=bool))
        want = basal * np.exp(lfc)
        np.testing.assert_allclose(profile / profile.sum(), want / want.sum(), rtol=1e-12, atol=0)
        self.assertEqual(detail["n_genes_clipped"], 0)

    def test_generated_cells_follow_it(self):
        rng = np.random.default_rng(6)
        basal = rng.gamma(2.0, 30.0, size=30) + 5.0
        lfc = rng.uniform(-1.0, 1.0, size=30)
        block, _ = trial01_cells(basal, lfc, np.ones(30, dtype=bool), np.full(10, 20_000), 3000,
                                 np.random.default_rng(1), max_stored_per_cell=30, max_counts_per_cell=1_000_000)
        freq = np.asarray(block.sum(axis=0)).ravel() / block.sum()
        want = basal * np.exp(lfc)
        np.testing.assert_allclose(freq, want / want.sum(), rtol=0.03)


class TestPerGeneDispersion(unittest.TestCase):
    """T3: g0d is reproducible, is not Poisson, and follows its per-gene dispersion."""

    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage("73_bench_k562_panel", "stage73_for_bench")

    def test_the_dispersion_fitted_on_controls_widens_what_it_should(self):
        rng = np.random.default_rng(9)
        n_cells, n_genes = 1500, 12
        libs = rng.integers(8000, 12000, size=n_cells)
        p = np.full(n_genes, 1.0 / n_genes)
        mu = libs[:, None] * p[None, :] / 100.0           # about 8 counts per gene and cell
        phi_true = np.array([0.0] * 4 + [0.5] * 4 + [2.0] * 4)
        lam = np.where(phi_true > 0, rng.gamma(1.0 / np.maximum(phi_true, 1e-9), mu * phi_true), mu)
        ctrl = sp.csr_matrix(rng.poisson(lam).astype(np.float32))
        basal = self.stage.control_basal(ctrl)
        np.testing.assert_array_equal(basal, np.asarray(ctrl.sum(axis=0), dtype=np.float64).ravel())
        lib_pool = np.asarray(ctrl.sum(axis=1)).ravel()
        phi = self.stage.control_dispersion(ctrl, basal, lib_pool, 2026)
        self.assertTrue(np.all(phi[:4] < 0.1), phi)
        self.assertTrue(np.all(phi[8:] > phi[4:8].max()), phi)

        lfc, observed = np.zeros(n_genes), np.ones(n_genes, dtype=bool)
        kw = dict(max_stored_per_cell=n_genes, max_counts_per_cell=1_000_000)
        one = trial01_cells(basal, lfc, observed, lib_pool, 800, np.random.default_rng(1), overdispersion=phi, **kw)[0]
        two = trial01_cells(basal, lfc, observed, lib_pool, 800, np.random.default_rng(1), overdispersion=phi, **kw)[0]
        poisson = trial01_cells(basal, lfc, observed, lib_pool, 800, np.random.default_rng(1), **kw)[0]
        self.assertEqual((one != two).nnz, 0)
        self.assertGreater((one != poisson).nnz, 0)
        dense = one.toarray()
        ratio = dense.var(axis=0) / dense.mean(axis=0)
        self.assertLess(ratio[:4].max(), ratio[8:].min())
        self.assertGreater(ratio[8:].min(), 3.0)


class TestArmNames(unittest.TestCase):
    """T4: prefixes and the per-seed names."""

    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage("73_bench_k562_panel", "stage73_for_bench")

    def test_prefixes(self):
        parse = self.stage.parse_arm
        self.assertEqual(parse("g0:t22_a1.0"), ("g0", ["t22_a1.0"]))
        self.assertEqual(parse("g0d:t22_a1.0+cis_a1.0"), ("g0d", ["t22_a1.0", "cis_a1.0"]))
        self.assertEqual(parse("oracle_a1.0+shared_a1.0"), (None, ["oracle_a1.0", "shared_a1.0"]))
        self.assertEqual(parse("null_g0"), (None, ["null_g0"]))
        for bad in ("g1:t22_a1.0", "g0:", "G0:t22_a1.0", ":t22_a1.0"):
            with self.subTest(arm=bad), self.assertRaises(SystemExit):
                parse(bad)

    def test_seed_names(self):
        self.assertEqual(self.stage.arm_key("g0:t22_a1.0", None), "g0:t22_a1.0")
        self.assertEqual(self.stage.arm_key("g0:t22_a1.0", 3), "g0:t22_a1.0@s3")


class TestLoadEffectsObserved(unittest.TestCase):
    """T5: the observed mask travels with the values, observed zeros included."""

    def test_observed_zero_is_kept_and_default_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            with_mask, without = Path(d) / "a.npz", Path(d) / "b.npz"
            lfc = np.array([[0.0, 0.5, 0.0, -0.2], [0.3, 0.0, 0.0, 0.0]], dtype=np.float32)
            obs = np.array([[True, True, False, True], [True, False, True, False]])
            np.savez(with_mask, targets=np.array(["T1", "T2"]), genes=np.array(["A", "B", "C", "D"]), lfc=lfc,
                     observed=obs)
            np.savez(without, targets=np.array(["T1", "T2"]), genes=np.array(["A", "B", "C", "D"]), lfc=lfc)
            genes = ["D", "A", "Z", "B"]                  # another order, and a gene the file lacks
            plain = load_effects([f"x={with_mask}"], genes)["x"]
            np.testing.assert_array_equal(plain["T1"], np.array([-0.2, 0.0, 0.0, 0.5], dtype=np.float32))
            self.assertEqual(plain["T1"].dtype, np.float64)
            both = load_effects([f"x={with_mask}"], genes, with_observed=True)["x"]
            np.testing.assert_array_equal(both["T1"][0], plain["T1"])
            np.testing.assert_array_equal(both["T1"][1], [True, True, False, True])
            np.testing.assert_array_equal(both["T2"][1], [False, True, False, False])   # A observed at 0.3
            fallback = load_effects([f"x={without}"], genes, with_observed=True)["x"]
            np.testing.assert_array_equal(fallback["T1"][1], [True, False, False, True])


def write_stage71_folder(folder: Path, rng) -> list[str]:
    """Two cells_part*.h5ad files, groups.csv and var.csv shaped like stage 71's output (x002)."""
    import anndata as ad

    targets = ["T1", "T2", "T3"]
    genes = targets + [f"G{i:02d}" for i in range(47)]
    base = rng.uniform(1.0, 9.0, size=len(genes))
    rows, gene_col, groups = [], [], []
    for t in targets:
        fc = np.ones(len(genes))
        fc[genes.index(t)] = 0.2
        fc[rng.choice(np.arange(3, len(genes)), size=6, replace=False)] = 2.5
        rows.append(rng.poisson(base * fc, size=(44, len(genes))))
        gene_col += [t] * 44
        groups.append({"group": f"1_{t}_P1_ENSG0", "gene": t, "is_ntc": False, "in_panel": True})
    rows.append(rng.poisson(base, size=(64, len(genes))))
    gene_col += ["non-targeting"] * 64
    groups.append({"group": "9_non-targeting", "gene": "non-targeting", "is_ntc": True, "in_panel": False})
    x = np.vstack(rows).astype(np.float32)
    gene_col = np.array(gene_col)
    group_of = {g["gene"]: g["group"] for g in groups}
    order = rng.permutation(x.shape[0])
    var = pd.DataFrame({"gene_name": genes}, index=[f"ENSG{i:05d}" for i in range(len(genes))])
    for part, idx in enumerate(np.array_split(order, 2)):
        obs = pd.DataFrame({"gene_transcript": [group_of[g] for g in gene_col[idx]], "gene": gene_col[idx]},
                           index=[f"c{i}" for i in idx])
        ad.AnnData(X=sp.csr_matrix(x[idx]), obs=obs, var=var).write_h5ad(folder / f"cells_part{part:03d}.h5ad")
    pd.DataFrame(groups).to_csv(folder / "groups.csv", index=False)
    var.to_csv(folder / "var.csv")
    return genes


def run_stage73(module, argv: list[str]) -> None:
    with mock.patch.object(sys, "argv", ["73_bench_k562_panel.py", *argv]), contextlib.redirect_stdout(io.StringIO()):
        module.main()


class TestStage73Smoke(unittest.TestCase):
    """T6 and T6b: stage 73 end to end on a synthetic stage-71 folder, with the real scorer."""

    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage("73_bench_k562_panel", "stage73_for_bench")

    def test_g0_arms_are_scored_once_per_generator_seed(self):
        import json

        rng = np.random.default_rng(21)
        with tempfile.TemporaryDirectory() as d:
            k562, out = Path(d) / "x002", Path(d) / "out"
            k562.mkdir()
            genes = write_stage71_folder(k562, rng)
            npz = Path(d) / "x.npz"
            lfc = np.zeros((3, len(genes)), dtype=np.float32)
            for i in range(3):
                lfc[i, i] = -1.5
            np.savez(npz, targets=np.array(["T1", "T2", "T3"]), genes=np.array(genes), lfc=lfc,
                     observed=lfc != 0)
            run_stage73(self.stage, ["--k562", str(k562), "--out", str(out), "--control-cells", "30",
                                     "--min-cells", "10", "--seed", "2026", "--gen-seeds", "1", "2",
                                     "--effects", f"x={npz}", "--arms", "g0:x_a1.0", "g0d:x_a1.0"])
            bench = json.loads((out / "bench.json").read_text(encoding="utf-8"))
        want = {"replicate", "baseline", "g0:x_a1.0@s1", "g0:x_a1.0@s2", "g0d:x_a1.0@s1", "g0d:x_a1.0@s2"}
        self.assertEqual(set(bench["results"]), want)
        self.assertIsNone(bench["model"])                        # no ControlModel arm, no fit
        self.assertEqual(bench["generators"]["gen_seeds"], [1, 2])
        self.assertIn("g0d", bench["generators"])
        self.assertEqual(bench["targets"], ["T1", "T2", "T3"])

    def test_without_the_new_flags_the_old_stage_is_reproduced(self):
        try:
            old = subprocess.run(["git", "-C", str(REPO), "show", f"{BEFORE}:scripts/73_bench_k562_panel.py"],
                                 capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            raise unittest.SkipTest(f"git or commit {BEFORE} is not available")
        with tempfile.TemporaryDirectory() as d:
            k562 = Path(d) / "x002"
            k562.mkdir()
            write_stage71_folder(k562, np.random.default_rng(22))
            (Path(d) / "old73.py").write_text(old, encoding="utf-8")
            spec = importlib.util.spec_from_file_location("stage73_before", Path(d) / "old73.py")
            before = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(before)
            argv = ["--control-cells", "30", "--min-cells", "10", "--seed", "2026", "--arms", "null_g0", "null_new"]
            run_stage73(before, ["--k562", str(k562), "--out", str(Path(d) / "old"), *argv])
            run_stage73(self.stage, ["--k562", str(k562), "--out", str(Path(d) / "new"), *argv])
            for name in ("replicate", "null_g0", "null_new"):
                with self.subTest(arm=name):     # the scorer's row order varies from call to call; values may not
                    frames = [pd.read_csv(Path(d) / side / f"per_pert_{name}.csv", dtype={"value": str})
                              .sort_values(["perturbation", "metric"]).reset_index(drop=True) for side in ("old", "new")]
                    self.assertGreater(len(frames[0]), 0)
                    pd.testing.assert_frame_equal(*frames)


if __name__ == "__main__":
    unittest.main()
