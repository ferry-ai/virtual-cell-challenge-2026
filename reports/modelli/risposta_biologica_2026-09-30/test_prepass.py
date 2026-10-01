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
        # study s4 (context K2): ten controls only; study s5 is one experiment published as two files (s5a, s5b)
        # that both carry its 100 control cells
        write_shard(sh / "s4_a.h5ad", np.vstack([counts(rng, p, 10), counts(rng, q, 60)]), "s4", "K2", "L5",
                    ["NTC"] * 10 + ["G1"] * 60, [f"F{i}-1" for i in range(70)], "file://s4")
        x5 = counts(rng, p, 100)
        write_shard(sh / "s5a.h5ad", np.vstack([x5, counts(rng, q, 50)]), "s5a", "K3", "L9", ["NTC"] * 100 + ["G2"] * 50,
                    [f"E{i}-1" for i in range(100)] + [f"Ea{i}-1" for i in range(50)], "file://s5_train")
        write_shard(sh / "s5b.h5ad", np.vstack([x5, counts(rng, q, 50)]), "s5b", "K3", "L9", ["NTC"] * 100 + ["G1"] * 50,
                    [f"E{i}-1" for i in range(100)] + [f"Eb{i}-1" for i in range(50)], "file://s5_val")
        common = ["--shards", sh, "--axis", d / "axis.csv", "--holdout-context", "H", "--holdout-target-frac", "0.34",
                  "--pool-size", "256", "--input-genes", "16", "--eval-min-cells", "10", "--min-controls-per-key", "20",
                  "--same-experiment", "s5=s5a,s5b"]
        cls.pre = run("prepass", *common, "--out", d / "pre")
        cls.pre_w2 = run("prepass", *common, "--out", d / "pre_w2", "--workers", "2")
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
        import shutil
        shutil.copytree(sh, d / "elsewhere" / "mounted")             # another runtime: the shards moved
        cls.mv = run("train", "--prepass", pre, "--out", d / "mv", "--target-code", "identity", "--roles", "2",
                     "--stop-after-steps", "4", "--shard-roots", d / "elsewhere", *TRAIN_SMALL)
        # two arms on one batch stream, loader processes for training and evaluation (1/10, E-20261001-001)
        cls.ma = run("train", "--prepass", pre, "--out", d / "ma", "--arm", "i1=identity", "--arm", "i2=identity",
                     "--roles", "2", "--workers", "2", "--eval-partial", "1.0", *TRAIN_SMALL)   # every shard row by row
        # a floor on the responder probability (1/10: the identity arm of rlab-cellnet-r3 collapsed to pi = 0)
        cls.pf = run("train", "--prepass", pre, "--out", d / "pf", "--target-code", "identity", "--pi-floor", "0.05",
                     *TRAIN_SMALL)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, run_dir, name):
        return json.loads((self.d / run_dir / name).read_text(encoding="utf-8"))

    def ckpt(self, run_dir, step):
        import torch
        return torch.load(self.d / run_dir / "checkpoints" / f"ckpt_{step:07d}.pt", weights_only=False)

    def test_every_stage_finished(self):
        for name in ("pre", "pre_rep", "full", "r1", "r2", "r3", "w2", "w0", "tb", "mv", "ma", "pf"):
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

    def test_the_prepass_does_not_depend_on_its_processes(self):
        import pickle
        self.assertEqual(self.pre_w2.returncode, 0, self.pre_w2.stderr[-3000:])
        for name in ("qc.json", "splits.json"):
            self.assertEqual(self.read("pre", name), self.read("pre_w2", name), name)
        one, two = (pickle.loads((self.d / r / "prepass.pkl").read_bytes()) for r in ("pre", "pre_w2"))
        for f in ("pool_x", "pool_lib", "pool_sid", "pool_libc", "input_genes", "key_mask"):
            self.assertTrue(np.array_equal(one[f], two[f]), f)
        self.assertEqual(sorted(one["sums"]), sorted(two["sums"]))
        self.assertTrue(all(np.array_equal(one["sums"][k], two["sums"][k]) for k in one["sums"]))
        self.assertTrue(all(np.array_equal(one["ctrl_mean"][k], two["ctrl_mean"][k]) for k in one["ctrl_mean"]))
        self.assertEqual([g["cells"] for g in one["eval_groups"]], [g["cells"] for g in two["eval_groups"]])
        for s1, s2 in zip(one["shards"], two["shards"]):
            self.assertTrue(np.array_equal(s1["train_rows"], s2["train_rows"]))
            self.assertTrue(np.array_equal(s1["admitted"], s2["admitted"]))

    def test_a_key_with_too_few_controls_is_not_a_context(self):
        qc = self.read("pre", "qc.json")
        self.assertEqual(qc["controls_per_key"]["s4|K2"], 10)
        self.assertEqual(qc["rejected"].get("s4|K2|too_few_controls_in_key"), 70)

    def test_one_experiment_in_two_files_counts_its_cells_once(self):
        ident = self.read("pre", "qc.json")["identity"]
        self.assertEqual(ident["same_experiment"], {"s5a": "s5", "s5b": "s5"})
        self.assertEqual(ident["by_study"]["s5"].get("duplicate"), 100)      # the controls read from the second file
        self.assertEqual(self.read("pre", "qc.json")["rejected"].get("s5|K3|duplicate_cell"), 100)

    def test_phenotype_is_kept(self):
        guard = self.read("pre", "qc.json")["phenotype_guard"]
        self.assertGreater(guard["readmitted_by_key"].get("s1|K", 0), 0)
        self.assertIn(("s1|K", "G1"), {(r["key"], r["group"]) for r in guard["selective_groups"]})

    # ---- training machinery
    def test_resume_reaches_the_state_of_an_uninterrupted_run(self):
        import torch
        a, b = self.ckpt("r2", 10), self.ckpt("r3", 10)
        for k in a["models"]["main"]:
            self.assertTrue(torch.equal(a["models"]["main"][k], b["models"]["main"][k]), k)
        sa, sb = a["opts"]["main"]["state"], b["opts"]["main"]["state"]
        self.assertEqual(sorted(sa), sorted(sb))
        for k in sa:
            self.assertTrue(torch.equal(sa[k]["exp_avg"], sb[k]["exp_avg"]))
        self.assertTrue(np.array_equal(a["seen"], b["seen"]))
        self.assertEqual(a["draws"], b["draws"])
        self.assertEqual(a["n_drawn"], b["n_drawn"])
        self.assertEqual(a["batch_chain"], b["batch_chain"])                 # the same cells, in the same order
        self.assertEqual(self.read("r2", "config.json")["resumed_from"]["step"], 5)
        self.assertIsInstance(a["rng"]["torch"], torch.Tensor)
        self.assertEqual(a["rng"]["torch"].device.type, "cpu")

    def test_shards_found_on_another_runtime_and_hashed(self):
        rows = self.read("mv", "shards_resolved.json")
        self.assertTrue(all("elsewhere" in r["path"] and "elsewhere" not in r["prepass_path"] for r in rows))
        verify = self.read("mv", "verify.json")
        self.assertEqual(verify["differ"], [])
        self.assertEqual(verify["shards"], len(rows))
        pre = json.loads((self.d / "pre" / "prepass_done.json").read_text(encoding="utf-8"))
        import hashlib
        self.assertEqual(hashlib.sha256((self.d / "pre" / "prepass.pkl").read_bytes()).hexdigest(), pre["sha256"])

    def test_hash_check_catches_a_changed_shard(self):
        sys.path.insert(0, str(HERE))
        import train_cellnet as TC
        f = self.d / "hash_case.bin"
        f.write_bytes(b"x" * 1000)
        rec = [{"path": str(f), "bytes": 1000, "sha256": TC.sha(f)}]
        self.assertTrue(TC.HashCheck(rec, self.d).wait())
        f.write_bytes(b"y" + b"x" * 999)                                     # same size, other bytes
        check = TC.HashCheck(rec, self.d)
        self.assertFalse(check.wait())
        self.assertEqual(check.bad, [str(f)])

    def test_loader_processes_give_the_same_batches(self):
        import torch
        a, b = self.ckpt("w2", 8), self.ckpt("w0", 8)
        for k in a["models"]["main"]:
            self.assertTrue(torch.equal(a["models"]["main"][k], b["models"]["main"][k]), k)
        self.assertTrue(np.array_equal(a["seen"], b["seen"]))

    def test_arms_on_one_stream_train_as_alone(self):
        import torch
        cov = self.read("ma", "coverage.json")
        self.assertEqual(cov["arms"], ["i1", "i2"])
        last = cov["steps"]
        self.assertEqual(self.read("run", "coverage.json")["steps"], last)
        ma, alone = self.ckpt("ma", last), self.ckpt("run", last)
        self.assertEqual(ma["batch_chain"], alone["batch_chain"])            # the same batches
        for k in alone["models"]["main"]:
            for arm in ("i1", "i2"):
                self.assertTrue(torch.equal(ma["models"][arm][k], alone["models"]["main"][k]), (arm, k))
        ev = {arm: self.read("ma", f"{arm}/eval.json")["summary"] for arm in ("i1", "i2")}
        ref = self.read("run", "eval.json")["summary"]
        self.assertTrue(ev["i1"]["evaluation"]["complete"])
        self.assertEqual(ev["i1"]["evaluation"]["workers"], 2)              # shards read by loader processes
        for c in ("C", "T", "J"):
            for f in ("groups", "ll_gain_vs_no_effect", "cos_model"):
                for arm in ("i1", "i2"):
                    if isinstance(ref[c].get(f), float):
                        self.assertAlmostEqual(ev[arm][c][f], ref[c][f], places=9, msg=(arm, c, f))
                    else:
                        self.assertEqual(ev[arm][c].get(f), ref[c].get(f), (arm, c, f))
        self.assertTrue((self.d / "ma" / "i2" / "model.pt").is_file())
        priced = [json.loads(l) for l in (self.d / "ma" / "train_log.jsonl").read_text(encoding="utf-8").splitlines()
                  if '"evaluation priced"' in l][0]
        self.assertGreaterEqual(priced["probe_partial_reads"], 1)              # the evaluation read rows alone

    def test_pi_floor_reaches_the_model_and_the_evaluation(self):
        import torch
        self.assertEqual(self.read("pf", "config.json")["same_on_resume"]["pi_floor"], "0.05")
        self.assertEqual(self.read("run", "config.json")["same_on_resume"]["pi_floor"], "0.0")
        self.assertEqual(torch.load(self.d / "pf" / "model.pt", weights_only=False)["pi_floor"], 0.05)
        ev = self.read("pf", "eval.json")
        pis = [r["pi_mean"] for c in ("C", "T", "J") for r in ev[c] if "skipped" not in r]
        self.assertTrue(pis and all(0.05 - 1e-6 <= v <= 0.95 + 1e-6 for v in pis))

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
