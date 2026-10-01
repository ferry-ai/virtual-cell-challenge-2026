"""Acceptance tests of the R-LEAD step A corrections (audit of 1/10, reports/analisi/lead_audit_2026-10-01/).

Each test exercises the corrected version in this folder; the counterexamples of the audit keep proving the earlier
behaviour in their own folder and are not changed. Where an option keeps the earlier behaviour for comparison
(--split-rule legacy, --loss-norm batch, --mixture clamp, --pool-min-per-library 0, --eval-selection largest), the
test shows both sides.

1. splits: a symbol's decision depends on the symbol alone; adding sources, symbols, aliases or replicates leaves the
   old decisions unchanged; a frozen manifest is kept; prepass end to end: old T/J groups keep their class;
2. classes after QC: a symbol whose only training source is excluded (too few controls) is J, not C;
3. loss weights: replay of the epoch sampler; with the global normaliser every active study has the share 1/S,
   with the per-batch one single-study batches cancel the weights; a study without cells does not shrink the others;
4. control pool: per library, a uniform sample independent of shard order and partition, only controls, every
   library with enough controls keeps its own pool, measured fallback;
5. mixture: from the gate's logit the gradient reopens a gate below the clamp when the response explains the cell
   better; finite at any logit; equal to the earlier formula inside the clamp;
6. generic arm: the target-blind row is trained by perturbed cells; end to end the arm trains and is evaluated;
7. evaluation groups: stratified selection represents every key.

    python -m unittest test_rlead_fixes -v          (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import json
import pickle
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cell_data as CD  # noqa: E402
import cellnet as CN  # noqa: E402
import test_prepass as TP  # noqa: E402

GENES = TP.GENES
TRAIN_SMALL = TP.TRAIN_SMALL


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)], capture_output=True,
                          text=True)


def state_of(pre: Path):
    with (pre / "prepass.pkl").open("rb") as fh:
        return pickle.load(fh)


def write_axis(d: Path) -> Path:
    axis = d / "axis.csv"
    axis.write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
    return axis


def manifest(d: Path, decisions: dict, salt="rlead-2026-10-01", frac=0.5) -> Path:
    p = d / "frozen_split.json"
    p.write_text(json.dumps({"split": {"salt": salt, "frac": frac, "decisions": decisions}}), encoding="utf-8")
    return p


class Splits(unittest.TestCase):
    def labels(self, n, contexts=("A", "B", "H")):
        rng = np.random.default_rng(3)
        return {f"S{i:04d}": {(f"st{c}", c) for c in contexts if rng.random() < 0.7} or {("stA", "A")}
                for i in range(n)}

    def test_old_decisions_do_not_move_when_the_corpus_grows(self):
        where = self.labels(400)
        hidden, trainable, dec, _ = CD.stable_splits(where, "H", 0.2, "salt")
        grown = {k: set(v) for k, v in where.items()}
        for i in range(400, 700):                                   # new symbols
            grown[f"S{i:04d}"] = {("stC", "C")}
        for s in list(grown)[:100]:                                 # the same symbols in a new study (replicates)
            grown[s].add(("stD", "D"))
        hidden2, trainable2, dec2, origin2 = CD.stable_splits(grown, "H", 0.2, "salt")
        self.assertEqual(hidden2 & set(trainable), hidden)
        self.assertTrue(all(dec2[s] == dec[s] for s in where))     # held-out-only symbols too, for when they move
        self.assertEqual(hidden2, {s for s in trainable2 if dec2[s]})
        self.assertEqual(Counter(origin2.values()), Counter({"hash": 700}))
        self.assertAlmostEqual(len(hidden2) / len(trainable2), 0.2, delta=0.05)
        # the earlier rule on the same growth: old symbols change decision (the defect, REVISIONE §2.1)
        old, _ = CD.splits(where, "H", 0.2, 20260930)
        old2, _ = CD.splits(grown, "H", 0.2, 20260930)
        self.assertNotEqual({s for s in old2 if s in where}, old)

    def test_frozen_manifest_wins_and_is_read_with_its_own_rule(self):
        where = self.labels(50)
        _, _, dec, _ = CD.stable_splits(where, "H", 0.2, "salt")
        flipped = {s: not v for s, v in list(dec.items())[:10]}
        frozen = {"salt": "salt", "frac": 0.2, "decisions": flipped}
        _, _, dec2, origin = CD.stable_splits(where, "H", 0.2, "salt", frozen)
        self.assertTrue(all(dec2[s] == v for s, v in flipped.items()))
        self.assertEqual(Counter(origin.values()), Counter({"frozen": 10, "hash": 40}))
        with self.assertRaises(ValueError):
            CD.stable_splits(where, "H", 0.2, "another salt", frozen)

    def test_prepass_keeps_old_groups_when_a_source_is_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            axis = write_axis(d)
            rng = np.random.default_rng(5)
            p = np.ones(len(GENES)) / len(GENES)
            sh = d / "shards"
            sh.mkdir()
            syms = [f"G{i}" for i in range(1, 25)]
            for study, ctx in [("a", "A"), ("b", "B"), ("h", "H")]:
                labels = ["NTC"] * 60 + [s for s in syms for _ in range(12)]
                TP.write_shard(sh / f"{study}.h5ad", TP.counts(rng, p, len(labels)), study, ctx, "L1", labels,
                               [f"{study}{i}" for i in range(len(labels))], f"synthetic:{study}")
            common = ["--axis", axis, "--holdout-context", "H", "--holdout-target-frac", "0.3", "--input-genes", "8",
                      "--eval-min-cells", "10", "--min-controls-per-key", "20", "--pool-size", "64"]
            r1 = run("prepass", "--shards", sh, *common, "--out", d / "pre1")
            self.assertEqual(r1.returncode, 0, r1.stderr[-3000:])
            new = ["G25", "G26", "G27", "G28", "G1", "G2"]           # new symbols and two old ones in a new study
            labels = ["NTC"] * 60 + [s for s in new for _ in range(12)]
            TP.write_shard(sh / "c.h5ad", TP.counts(rng, p, len(labels)), "c", "C", "L1", labels,
                           [f"c{i}" for i in range(len(labels))], "synthetic:c")
            r2 = run("prepass", "--shards", sh, *common, "--split-manifest", d / "pre1" / "splits.json",
                     "--out", d / "pre2")
            self.assertEqual(r2.returncode, 0, r2.stderr[-3000:])
            s1, s2 = state_of(d / "pre1"), state_of(d / "pre2")
            self.assertEqual({s for s in s2["hidden"] if s in s1["symbols"]}, set(s1["hidden"]))
            g1 = {(g["class"], g["key"], g["symbol"]) for g in s1["eval_groups"]}
            g2 = {(g["class"], g["key"], g["symbol"]) for g in s2["eval_groups"]}
            self.assertTrue(g1 <= g2, sorted(g1 - g2))
            sp = json.loads((d / "pre2" / "splits.json").read_text(encoding="utf-8"))["split"]
            self.assertEqual(sp["origin"].get("frozen"), len(s1["symbols"]))


class ClassesAfterQC(unittest.TestCase):
    def test_target_of_an_excluded_source_is_J(self):
        """The audit's counterexample (reproduce_findings.py): G2 is perturbed in training only in a study with two
        controls, which the prepass excludes; its held-out cells must be J."""
        for rule in ("stable", "legacy"):
            with tempfile.TemporaryDirectory() as tmp:
                d = Path(tmp)
                axis = write_axis(d)
                sh = d / "shards"
                sh.mkdir()
                rng = np.random.default_rng(28)
                for study, context, nc, target in [("valid", "K", 40, "G1"), ("excluded", "Z", 2, "G2"),
                                                   ("held", "H", 40, "G2")]:
                    labels = ["NTC"] * nc + [target] * 40
                    TP.write_shard(sh / f"{study}.h5ad", rng.poisson(30, (len(labels), len(GENES))), study, context,
                                   "L", labels, [f"{study}_{i}" for i in range(len(labels))], f"synthetic:{study}")
                r = run("prepass", "--shards", sh, "--axis", axis, "--holdout-context", "H", "--holdout-target-frac",
                        0, "--min-controls-per-key", 20, "--eval-min-cells", 10, "--input-genes", 8,
                        "--split-rule", rule, "--out", d / "pre")
                self.assertEqual(r.returncode, 0, r.stderr[-3000:])
                st = state_of(d / "pre")
                group = next(g for g in st["eval_groups"] if g["symbol"] == "G2")
                self.assertEqual(group["class"], "J", rule)
                sp = json.loads((d / "pre" / "splits.json").read_text(encoding="utf-8"))["split"]["after_qc"]
                self.assertIn("G2", sp["lost_by_admission"])
                self.assertEqual(sp["cells_reclassified"].get("C->J"), 40)


class LossWeights(unittest.TestCase):
    def replay(self, norm, buffer):
        """Coefficient with which the cells of each study enter the objective, summed over one epoch of batches of
        the epoch sampler (the quantity replayed by the audit, sampler_r1)."""
        sizes = {"big": [4000, 4000, 4000], "mid": [3000], "small": [500, 500]}
        shards, study_of = [], {}
        for st, ns in sizes.items():
            for j, n in enumerate(ns):
                sid = f"{st}{j}"
                shards.append((sid, np.arange(n)))
                study_of[sid] = st
        w = CD.study_weights({st: sum(ns) for st, ns in sizes.items()})
        smp = CD.EpochSampler(shards, buffer=buffer, seed=0)
        coef, B = Counter(), 64
        total = sum(sum(ns) for ns in sizes.values())
        for _ in range(total // B):
            cells = smp.batch(B)
            ws = np.array([w[study_of[s]] for s, _ in cells])
            den = ws.sum() if norm == "batch" else float(len(cells))
            for (s, _), wi in zip(cells, ws):
                coef[study_of[s]] += wi / den
        tot = sum(coef.values())
        return {k: v / tot for k, v in coef.items()}

    def test_global_normaliser_gives_each_study_its_share(self):
        for buffer in (1, 2):
            share = self.replay("global", buffer)
            for st, v in share.items():
                self.assertAlmostEqual(v, 1 / 3, delta=0.02, msg=f"buffer {buffer}: {share}")

    def test_per_batch_normaliser_cancels_weights_in_single_study_batches(self):
        share = self.replay("batch", 1)                      # one shard loaded: every batch has one study
        self.assertGreater(share["big"], 0.5, share)         # its share is its share of the cells, 12000 / 17000

    def test_a_study_without_cells_does_not_shrink_the_others(self):
        w = CD.study_weights({"a": 100, "b": 0, "c": 300})
        self.assertEqual(set(w), {"a", "c"})
        self.assertAlmostEqual((100 * w["a"] + 300 * w["c"]) / 400, 1.0)
        self.assertAlmostEqual(100 * w["a"], 300 * w["c"])


class ControlPool(unittest.TestCase):
    def test_allocation(self):
        alloc, size = CD.allocate_pool({"L1": 1000, "L2": 30, "L3": 200}, 300, 64)
        self.assertEqual(alloc["L2"], 30)
        self.assertGreaterEqual(min(alloc["L1"], alloc["L3"]), 64)
        self.assertEqual(sum(alloc.values()), 300)
        self.assertEqual(size, 300)
        many = {f"L{i:02d}": 100 for i in range(56)}               # HepG2-like: 56 libraries
        alloc, size = CD.allocate_pool(many, 2048, 64)
        self.assertEqual(size, 56 * 64)
        self.assertTrue(all(v == 64 for v in alloc.values()))

    def corpus(self, d: Path, split: bool, shuffle_names: bool):
        sh = d / "shards"
        sh.mkdir()
        rng = np.random.default_rng(9)
        p = np.ones(len(GENES)) / len(GENES)
        libs = [f"L{i}" for i in range(6)]
        n_ctrl = [150, 120, 100, 90, 40, 20]
        cells = []                                                 # (library, label, barcode)
        for lib, n in zip(libs, n_ctrl):
            cells += [(lib, "NTC", f"{lib}_c{i}") for i in range(n)]
            cells += [(lib, "G1", f"{lib}_p{i}") for i in range(30)]
        x = TP.counts(rng, p, len(cells))
        x[[i for i, c in enumerate(cells) if c[1] == "G1"], GENES.index("G1")] = 5000   # marks perturbed cells
        parts = [range(len(cells))] if not split else [range(0, len(cells), 2), range(1, len(cells), 2)]
        for j, rows in enumerate(parts):
            rows = list(rows)
            for lib in libs:                                       # one shard per (part, library): write_shard has one
                sel = [r for r in rows if cells[r][0] == lib]
                name = f"{'z' if shuffle_names else 'a'}{j}_{lib}.h5ad" if j == 0 else f"m{j}_{lib}.h5ad"
                TP.write_shard(sh / name, x[sel], "h", "H", lib, [cells[r][1] for r in sel],
                               [cells[r][2] for r in sel], "synthetic:h")
        rng2 = np.random.default_rng(10)
        labels = ["NTC"] * 80 + ["G1"] * 40
        TP.write_shard(sh / "t.h5ad", TP.counts(rng2, p, len(labels)), "t", "K", "LT", labels,
                       [f"t{i}" for i in range(len(labels))], "synthetic:t")
        return sh

    def pool_cells(self, pre: Path):
        st = state_of(pre)
        k = st["key_names"].index("h|H")
        n = int((st["pool_sid"][k] >= 0).sum())
        rows = st["pool_x"][k, :n].astype(np.float32)
        libs = [st["library_names"][c] for c in st["pool_libc"][k, :n]]
        return sorted(zip(libs, map(lambda r: r.tobytes(), rows))), Counter(libs), st

    def test_pool_is_independent_of_shard_order_and_partition(self):
        args = ["--holdout-context", "H", "--holdout-target-frac", 0, "--min-controls-per-key", 20,
                "--eval-min-cells", 10, "--input-genes", 40, "--pool-size", 128, "--pool-min-per-library", 16]
        out = {}
        for name, split, shuffle in [("one", False, False), ("two", True, False), ("order", True, True)]:
            with tempfile.TemporaryDirectory() as tmp:
                d = Path(tmp)
                axis = write_axis(d)
                sh = self.corpus(d, split, shuffle)
                r = run("prepass", "--shards", sh, "--axis", axis, *args, "--out", d / "pre")
                self.assertEqual(r.returncode, 0, r.stderr[-3000:])
                out[name] = self.pool_cells(d / "pre")
                rep = json.loads((d / "pre" / "controls.json").read_text(encoding="utf-8"))
        self.assertEqual(out["one"][0], out["two"][0])
        self.assertEqual(out["one"][0], out["order"][0])
        kept = out["one"][1]
        # 6 x 16 rows guaranteed, 32 more in proportion to the controls beyond 16 (largest remainder): L5 keeps 16
        self.assertEqual(dict(kept), {"L0": 26, "L1": 24, "L2": 22, "L3": 22, "L4": 18, "L5": 16})
        by = rep["by_key"]["h|H"]
        self.assertEqual(by["perturbed_share_with_own_library_pool"], 1.0)
        self.assertEqual(by["controls_in_pool"], 128)

    def test_pool_holds_only_controls_and_the_earlier_reservoir_loses_libraries(self):
        args = ["--holdout-context", "H", "--holdout-target-frac", 0, "--min-controls-per-key", 20,
                "--eval-min-cells", 10, "--input-genes", 40, "--pool-size", 128]
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            axis = write_axis(d)
            sh = self.corpus(d, False, False)
            r_new = run("prepass", "--shards", sh, "--axis", axis, *args, "--pool-min-per-library", 64,
                        "--out", d / "new")
            r_old = run("prepass", "--shards", sh, "--axis", axis, *args, "--pool-min-per-library", 0,
                        "--out", d / "old")
            for r in (r_new, r_old):
                self.assertEqual(r.returncode, 0, r.stderr[-3000:])
            new = json.loads((d / "new" / "controls.json").read_text(encoding="utf-8"))["by_key"]["h|H"]
            old = json.loads((d / "old" / "controls.json").read_text(encoding="utf-8"))["by_key"]["h|H"]
            self.assertEqual(new["perturbed_share_with_own_library_pool"],
                             new["perturbed_share_with_own_library_before_cap"])
            self.assertLess(old["perturbed_share_with_own_library_pool"],
                            new["perturbed_share_with_own_library_pool"])
            st = state_of(d / "new")
            ctrl_rows = {(s["name"], int(r)) for s in st["shards"] for r in np.flatnonzero(s["control"])}
            self.assertGreater(len(ctrl_rows), 0)
            k = st["key_names"].index("h|H")
            n = int((st["pool_sid"][k] >= 0).sum())
            self.assertEqual(n, new["controls_in_pool"])
            # no perturbed cell in the pool: perturbed cells carry 5000 counts of G1, controls about 30 in total
            col = int(np.flatnonzero(st["input_genes"] == st["genes"].index("G1"))[0])
            self.assertLess(float(st["pool_x"][k, :n, col].max()), 1000)


class Mixture(unittest.TestCase):
    def grad(self, logit_value, floor, clamp):
        import torch
        z = torch.tensor([logit_value], dtype=torch.float64, requires_grad=True)
        ll1, ll0 = torch.tensor([-1.0], dtype=torch.float64), torch.tensor([-2.0], dtype=torch.float64)
        pi = floor + (1 - 2 * floor) * torch.sigmoid(z)
        if clamp:
            lp, lq = torch.log(pi.clamp_min(1e-6)), torch.log((1 - pi).clamp_min(1e-6))
        else:
            lp, lq = CN.gate_logs(z, floor)
        loss = -CN.mixture(ll1, ll0, lp, lq).sum()
        loss.backward()
        return float(z.grad), float(loss.detach())

    def test_gradient_reopens_a_gate_below_the_clamp(self):
        z = float(np.log(1e-8 / (1 - 1e-8)))                     # pi = 1e-8, the response explains the cell better
        g_clamp, _ = self.grad(z, 0.0, True)
        g_logit, _ = self.grad(z, 0.0, False)
        self.assertGreater(g_clamp, 0)                           # the earlier formula still closes the gate
        self.assertLess(g_logit, 0)                              # descent raises the logit
        self.assertAlmostEqual(g_logit, -1.71828e-8, delta=1e-12)  # the audit's value, AGGIORNAMENTO_R3

    def test_finite_everywhere_and_equal_inside_the_clamp(self):
        for floor in (0.0, 0.05):
            for z in (-1000.0, -50.0, 0.0, 50.0, 1000.0):
                g, l = self.grad(z, floor, False)
                self.assertTrue(np.isfinite(g) and np.isfinite(l), (floor, z))
            for z in (-5.0, 0.3, 4.0):
                g1, l1 = self.grad(z, floor, False)
                g2, l2 = self.grad(z, floor, True)
                self.assertAlmostEqual(l1, l2, places=10)
                self.assertAlmostEqual(g1, g2, places=10)


class GenericArm(unittest.TestCase):
    def test_target_blind_row_learns_from_perturbed_cells(self):
        import torch
        torch.manual_seed(0)
        n_sym = 3
        m = CN.build_model(12, n_sym, 1, 1, np.arange(6), dim=6, rank=3, target_code="generic")
        with torch.no_grad():
            m.delta_out.weight.normal_(0, 0.1)
        x = torch.poisson(torch.full((4, 12), 4.0))
        z, beta = m.context(x[:, :6].reshape(1, 4, 6), torch.ones(1, 4, 6, dtype=torch.bool), x.sum(-1).reshape(1, 4))
        z, beta = z.expand(4, -1), beta.expand(4, -1)
        tgt = torch.full((4,), n_sym)
        delta, pi, lp, lq = m(z, beta, tgt, torch.full((4,), -1), torch.zeros(4, dtype=torch.long), return_logs=True)
        mask, theta = torch.ones(4, 12, dtype=torch.bool), torch.exp(m.log_theta[0])
        ll0 = CN.cell_loglik(x, x.sum(-1), beta, mask, theta)
        ll1 = CN.cell_loglik(x, x.sum(-1), beta + delta, mask, theta)
        (-CN.mixture(ll1, ll0, lp, lq).mean()).backward()
        self.assertGreater(float(m.target_emb.weight.grad[n_sym].abs().max()), 0)
        self.assertEqual(float(m.target_emb.weight.grad[:n_sym].abs().max()), 0)

    def test_generic_and_identity_arms_train_on_one_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            axis = write_axis(d)
            sh = d / "shards"
            sh.mkdir()
            rng = np.random.default_rng(4)
            p = np.ones(len(GENES)) / len(GENES)
            q = p.copy(); q[3] *= 5; q /= q.sum()
            for study, ctx in [("a", "A"), ("b", "B"), ("h", "H")]:
                labels = ["NTC"] * 80 + ["G1"] * 40 + ["G2"] * 40 + ["G3"] * 40
                x = np.vstack([TP.counts(rng, p, 80), TP.counts(rng, q, 120)])
                TP.write_shard(sh / f"{study}.h5ad", x, study, ctx, "L1", labels,
                               [f"{study}{i}" for i in range(len(labels))], f"synthetic:{study}")
            r = run("prepass", "--shards", sh, "--axis", axis, "--holdout-context", "H", "--holdout-target-frac", 0,
                    "--input-genes", 8, "--eval-min-cells", 10, "--min-controls-per-key", 20, "--out", d / "pre")
            self.assertEqual(r.returncode, 0, r.stderr[-3000:])
            r = run("train", "--prepass", d / "pre", "--out", d / "run", "--arm", "g=generic", "--arm", "i=identity",
                    *TRAIN_SMALL)
            self.assertEqual(r.returncode, 0, r.stderr[-3000:])
            cfg = json.loads((d / "run" / "config.json").read_text(encoding="utf-8"))
            self.assertEqual((cfg["loss_norm"], cfg["mixture"]), ("global", "logits"))
            self.assertIn("training_fallback_share", cfg["control_fallback"])
            for arm in ("g", "i"):
                self.assertTrue((d / "run" / arm / "eval.json").is_file(), arm)


class EvaluationGroups(unittest.TestCase):
    def test_stratified_selection_represents_every_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            axis = write_axis(d)
            sh = d / "shards"
            sh.mkdir()
            rng = np.random.default_rng(6)
            p = np.ones(len(GENES)) / len(GENES)
            spec = {"a": ("A", {"G1": 100, "G2": 90, "G3": 80, "G5": 50}), "b": ("B", {"G4": 30, "G5": 50}),
                    "h": ("H", {"G5": 40, "G6": 40})}
            for study, (ctx, n) in spec.items():
                labels = ["NTC"] * 60 + [s for s, k in n.items() for _ in range(k)]
                TP.write_shard(sh / f"{study}.h5ad", TP.counts(rng, p, len(labels)), study, ctx, "L1", labels,
                               [f"{study}{i}" for i in range(len(labels))], f"synthetic:{study}")
            frozen = manifest(d, {"G1": True, "G2": True, "G3": True, "G4": True, "G5": False, "G6": False})
            common = ["--shards", sh, "--axis", axis, "--holdout-context", "H", "--holdout-target-frac", 0.5,
                      "--split-manifest", frozen, "--input-genes", 8, "--eval-min-cells", 10,
                      "--min-controls-per-key", 20, "--eval-max-groups", 2]
            r1 = run("prepass", *common, "--eval-selection", "stratified", "--out", d / "strat")
            r2 = run("prepass", *common, "--eval-selection", "largest", "--out", d / "large")
            for r in (r1, r2):
                self.assertEqual(r.returncode, 0, r.stderr[-3000:])
            keys = lambda pre: {g["key"] for g in state_of(pre)["eval_groups"] if g["class"] == "T"}  # noqa: E731
            self.assertEqual(keys(d / "strat"), {"a|A", "b|B"})
            self.assertEqual(keys(d / "large"), {"a|A"})
            table = json.loads((d / "strat" / "splits.json").read_text(encoding="utf-8"))["evaluation_selection"]
            self.assertEqual(table["by_class_and_key"]["T"]["b|B"]["groups_selected"], 1)


if __name__ == "__main__":
    unittest.main()
