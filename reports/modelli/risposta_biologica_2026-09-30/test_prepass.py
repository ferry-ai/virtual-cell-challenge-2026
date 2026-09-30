"""End to end on synthetic contract shards, through both stages of train_cellnet.py.

The four rules kept open on 30/09 (duplicates and collisions, combined perturbations, phenotype conservation in QC,
control masks), as the prepass applies them, and the training machinery asked for before the Kaggle run (checkpoints,
resume, loader processes, time budget), each with a known answer:
- study s1 (context K): 50 cells ingested twice (same keys, same counts), 30 keys reused by other cells of the same
  source file (collisions), 20 keys read again from another source file with other counts (other versions), a
  knockdown G1 with a third of the counts, a combination G3_G4;
- study s2 holds 40 cells with the counts of 40 cells of s1 under its own keys: kept and reported; left out only when
  a republication is declared;
- the held-out context H has two shards of one key, the second without genes G31-G36 and with two native features on G7;
- training stopped at step 5 and resumed to step 10 ends in the same state as a run straight to step 10; two loader
  processes give the same batches as one process playing both roles; a budget of half a minute stops training in time.

    python -m unittest test_prepass -v          (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
GENES = [f"G{i}" for i in range(1, 37)] + ["MT-CO1", "MT-ND1", "MT-ND2", "MT-CO2"]
TRAIN_SMALL = ["--epochs", "1", "--batch", "32", "--ctrl-k", "8", "--buffer-shards", "2", "--dim", "8", "--rank", "4",
               "--device", "cpu", "--measure-from", "2", "--measure-steps", "3", "--log-every", "5",
               "--reserve-export-minutes", "0.05", "--eval-reserve-seconds", "5"]


def counts(rng, p, n, scale=1.0):
    lib = np.maximum(1, np.exp(rng.normal(8, 0.3, n)) * scale).astype(int)
    return np.stack([rng.multinomial(L, p) for L in lib])


def write_shard(path, x, study, context, library, targets, barcodes, source, native=None):
    import anndata as ad
    import pandas as pd
    n = x.shape[0]
    native = GENES if native is None else native
    targets = np.asarray(targets, dtype=object)
    control = np.where(targets == "NTC", "NTC", np.where(targets == "UNASSIGNED", "UNASSIGNED", "none"))
    obs = pd.DataFrame({"study": study, "context": context, "library": library, "target": targets,
                        "control_kind": control, "modality": "CRISPRi", "barcode": barcodes,
                        "cell_key": [f"{study}|{library}|{b}" for b in barcodes]}, index=[f"c{i}" for i in range(n)])
    official = np.array([GENES.index(g) if g in GENES else -1 for g in native], dtype=np.int64)
    var = pd.DataFrame({"symbol": native, "official_index": official, "measured": np.ones(len(native), bool)},
                       index=[f"f{i}" for i in range(len(native))])
    ad.AnnData(X=sp.csr_matrix(x.astype(np.int32)), obs=obs, var=var,
               uns={"source": {"locator": source, "release": "test"}}).write_h5ad(path)


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)], capture_output=True, text=True)


class Stages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(11)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q /= q.sum()                        # a transcriptional response on G6
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        # study s1, context K: controls 0-299, G1 300-419, G2 420-539, G3_G4 540-599, unassigned 600-619
        x_a = np.vstack([counts(rng, p, 300), counts(rng, q, 120, 0.35), counts(rng, q, 120), counts(rng, q, 60),
                         counts(rng, p, 20)])
        t_a = ["NTC"] * 300 + ["G1"] * 120 + ["G2_guide1"] * 120 + ["G3_G4"] * 60 + ["UNASSIGNED"] * 20
        bc_a = [f"A{i}-1" for i in range(len(t_a))]
        write_shard(sh / "s1_a.h5ad", x_a, "s1", "K", "L1", t_a, bc_a, "file://s1_v1")
        dup_rows, col_rows = list(range(420, 470)), list(range(0, 30))
        x_b = np.vstack([x_a[dup_rows], counts(rng, p, 30), counts(rng, q, 60)])
        t_b = [t_a[i] for i in dup_rows] + ["NTC"] * 30 + ["G4"] * 60
        bc_b = [bc_a[i] for i in dup_rows] + [bc_a[i] for i in col_rows] + [f"B{i}-1" for i in range(60)]
        write_shard(sh / "s1_b.h5ad", x_b, "s1", "K", "L1", t_b, bc_b, "file://s1_v1")
        ver_rows = list(range(510, 530))                             # the same keys, other counts, another file
        write_shard(sh / "s1_c.h5ad", counts(rng, q, 20), "s1", "K", "L1", [t_a[i] for i in ver_rows],
                    [bc_a[i] for i in ver_rows], "file://s1_v2")
        rep_rows = list(range(470, 510))                             # study s2: 40 cells with the counts of s1 cells
        x_c = np.vstack([x_a[rep_rows], counts(rng, p, 200), counts(rng, q, 80)])
        t_c = ["G2"] * 40 + ["NTC"] * 200 + ["G2"] * 80
        write_shard(sh / "s2_a.h5ad", x_c, "s2", "K", "L7", t_c, [f"R{i}-1" for i in range(len(t_c))], "file://s2")
        x_h = np.vstack([counts(rng, p, 150), counts(rng, q, 60), counts(rng, q, 60), counts(rng, q, 60),
                         counts(rng, q, 40)])
        t_h = ["NTC"] * 150 + ["G1"] * 60 + ["G2"] * 60 + ["G3"] * 60 + ["G3+G1"] * 40
        write_shard(sh / "s3_a.h5ad", x_h, "s3", "H", "L3", t_h, [f"H{i}-1" for i in range(len(t_h))], "file://s3")
        keep = [g for g in GENES if g not in {f"G{i}" for i in range(31, 37)}]
        x_k = np.vstack([counts(rng, p, 100), counts(rng, q, 60)])
        x_k = np.hstack([x_k[:, [GENES.index(g) for g in keep]], x_k[:, [GENES.index("G7")]]])
        write_shard(sh / "s3_b.h5ad", x_k, "s3", "H", "L4", ["NTC"] * 100 + ["G4"] * 60,
                    [f"K{i}-1" for i in range(160)], "file://s3", native=keep + ["G7"])
        common = ["--shards", sh, "--axis", d / "axis.csv", "--holdout-context", "H", "--holdout-target-frac", "0.34",
                  "--pool-size", "256", "--input-genes", "16", "--eval-min-cells", "10"]
        cls.pre = run("prepass", *common, "--out", d / "pre")
        (d / "rep.json").write_text(json.dumps({"s2": "s1"}), encoding="utf-8")
        cls.pre_rep = run("prepass", *common, "--out", d / "pre_rep", "--republications", d / "rep.json")
        pre = d / "pre"
        cls.full = run("train", "--prepass", pre, "--out", d / "run", "--target-code", "identity", "--roles", "2",
                       *TRAIN_SMALL)
        cls.r1 = run("train", "--prepass", pre, "--out", d / "r1", "--target-code", "identity", "--roles", "2",
                     "--stop-after-steps", "5", *TRAIN_SMALL)
        cls.r2 = run("train", "--prepass", pre, "--out", d / "r2", "--target-code", "identity", "--roles", "2",
                     "--resume", d / "r1", "--stop-after-steps", "10", *TRAIN_SMALL)
        cls.r3 = run("train", "--prepass", pre, "--out", d / "r3", "--target-code", "identity", "--roles", "2",
                     "--stop-after-steps", "10", *TRAIN_SMALL)
        cls.w2 = run("train", "--prepass", pre, "--out", d / "w2", "--target-code", "identity", "--roles", "2",
                     "--workers", "2", "--stop-after-steps", "8", *TRAIN_SMALL)
        cls.w0 = run("train", "--prepass", pre, "--out", d / "w0", "--target-code", "identity", "--roles", "2",
                     "--stop-after-steps", "8", *TRAIN_SMALL)
        budget = [a if a != "1" else "1000" for a in TRAIN_SMALL]  # epochs: far more than the budget allows
        cls.tb = run("train", "--prepass", pre, "--out", d / "tb", "--target-code", "identity", "--budget-minutes",
                     "0.5", *budget)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, run_dir, name):
        return json.loads((self.d / run_dir / name).read_text(encoding="utf-8"))

    def ckpt(self, run_dir, step):
        import torch
        return torch.load(self.d / run_dir / "checkpoints" / f"ckpt_{step:07d}.pt", weights_only=False)

    def test_every_stage_finished(self):
        for name in ("pre", "pre_rep", "full", "r1", "r2", "r3", "w2", "w0", "tb"):
            proc = getattr(self, name)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr[-3000:]}")
        self.assertTrue((self.d / "run" / "eval.json").is_file())

    # ---- the four rules
    def test_duplicates_collisions_versions(self):
        ident = self.read("pre", "qc.json")["identity"]
        self.assertEqual(ident["by_study"]["s1"].get("duplicate"), 50)
        self.assertEqual(ident["by_study"]["s1"].get("collision"), 30)
        self.assertEqual(ident["by_study"]["s1"].get("version"), 20)
        self.assertEqual(ident["by_study"]["s2"].get("new"), 320)             # nothing dropped on counts alone
        self.assertEqual(ident["content_matches_across_keys"], [{"studies": ["s1", "s2"], "cells": 40}])
        rejected = self.read("pre", "qc.json")["rejected"]
        self.assertEqual(rejected.get("s1|K|duplicate_cell"), 50)
        self.assertEqual(rejected.get("s1|K|other_version_of_cell"), 20)

    def test_declared_republication_is_left_out_whole(self):
        qc = self.read("pre_rep", "qc.json")
        self.assertEqual(qc["identity"]["declared_republications"], {"s2": "s1"})
        self.assertEqual(qc["rejected"].get("s2|K|republication_of:s1"), 320)

    def test_feature_collision_masks_the_gene(self):
        feats = self.read("pre", "qc.json")["features"]["shards_with_collisions"]
        self.assertEqual([(Path(f["shard"]).name, f["examples"]) for f in feats], [("s3_b.h5ad", ["G7"])])

    def test_key_mask_is_the_intersection_of_its_shards(self):
        m = self.read("pre", "qc.json")["masks"]["by_key"]["s3|H"]
        self.assertEqual(m["genes_in_some_shard_only"], 7)          # G31-G36 and G7
        ev = self.read("run", "eval.json")
        rows = [r for c in ("C", "J") for r in ev[c] if r["key"] == "s3|H" and "skipped" not in r]
        self.assertTrue(rows)
        self.assertTrue(all(r["genes_compared"] <= len(GENES) - 7 for r in rows))

    def test_combinations_are_classed_and_never_drawn(self):
        splits = self.read("pre", "splits.json")
        labels = splits["labels"]
        self.assertEqual(labels["cells_by_kind_and_study"]["s1"]["combined"], 60)
        self.assertEqual(labels["combined_labels"]["s1"][0]["value"], "G3+G4")
        classes = splits["cells_by_class"]
        self.assertEqual(sum(v for k, v in classes.items() if k.startswith("combined:")), 100)
        self.assertEqual(classes.get("combined:J"), 40)             # G3 was never perturbed alone in training
        self.assertNotIn("G3", splits["hidden_symbols"])
        self.assertEqual(splits["trainable_symbols"], 3)            # G1, G2, G4 perturbed alone in K
        cov = self.read("run", "coverage.json")
        self.assertTrue(cov["leakage_check"]["passed"])

    def test_phenotype_is_kept(self):
        guard = self.read("pre", "qc.json")["phenotype_guard"]
        self.assertGreater(guard["readmitted_by_key"].get("s1|K", 0), 0)
        self.assertIn(("s1|K", "G1"), {(r["key"], r["group"]) for r in guard["selective_groups"]})

    # ---- training machinery
    def test_resume_reaches_the_state_of_an_uninterrupted_run(self):
        import torch
        a, b = self.ckpt("r2", 10), self.ckpt("r3", 10)
        for k in a["model"]:
            self.assertTrue(torch.equal(a["model"][k], b["model"][k]), k)
        sa, sb = a["opt"]["state"], b["opt"]["state"]
        self.assertEqual(sorted(sa), sorted(sb))
        for k in sa:
            self.assertTrue(torch.equal(sa[k]["exp_avg"], sb[k]["exp_avg"]))
        self.assertTrue(np.array_equal(a["seen"], b["seen"]))
        self.assertEqual(a["draws"], b["draws"])
        self.assertEqual(a["n_drawn"], b["n_drawn"])
        self.assertEqual(self.read("r2", "config.json")["resumed_from"]["step"], 5)

    def test_loader_processes_give_the_same_batches(self):
        import torch
        a, b = self.ckpt("w2", 8), self.ckpt("w0", 8)
        for k in a["model"]:
            self.assertTrue(torch.equal(a["model"][k], b["model"][k]), k)
        self.assertTrue(np.array_equal(a["seen"], b["seen"]))

    def test_coverage_counts_consumed_cells(self):
        cov = self.read("run", "coverage.json")
        self.assertEqual(cov["stop"], "epochs done")
        self.assertEqual(cov["distinct_cells_seen"], cov["admitted_training_cells"])
        self.assertTrue(all(k["distinct_drawn"] == k["admitted_offered"] for k in cov["by_key"]))

    def test_time_budget_leaves_room_for_evaluation(self):
        cov, done, plan = self.read("tb", "coverage.json"), self.read("tb", "done.json"), self.read("tb", "plan.json")
        self.assertEqual(cov["stop"], "time budget")
        self.assertGreater(plan["steps_per_second"], 0)
        self.assertLessEqual(done["wall_seconds"], 30 + 15)
        self.assertTrue(self.read("tb", "eval.json")["summary"]["evaluation"]["complete"])


if __name__ == "__main__":
    unittest.main()
