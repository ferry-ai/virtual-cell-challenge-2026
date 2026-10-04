"""Version 4 of train_cellnet.py end to end, on synthetic contract shards with known answers.

Corpus: line group LINE (contexts La, Lb) held out whole; kept groups K (study sk, three shards, many cells), Q (study
sq) and a small group S (study ss, one shard of 60 perturbed cells and its controls), the shape of the H1 defect.
G4 is in the hidden hash fold.
- balanced batches: every complete window of the exposure receipt holds each of the three kept groups at 1/3 of the
  loss within the tolerance, the small group from the first window; every cell weighs 1;
- the compact twins: a run through --fast-roots consumes the same batches (hash chain) and ends with the same parameters
  as the run on the h5ad shards; a twin that does not match the manifest, or a manifest whose source is another file,
  is refused;
- resume: stopped at step 6 and resumed to the end, the same chain, windows and parameters as a run straight through;
- two loader processes give the same batches as one process playing both roles;
- the training budget no longer depends on a priced evaluation, and the evaluation reports its own budget;
- version 3's epoch sampler on the same corpus, stopped early, fails the exposure rule (the defect the sampler fixes).

    python -m unittest test_train_v4 -v           (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fixtures import GENES, counts, key_in_fold, make_twins, write_shard  # noqa: E402

TRAIN = ["--batch", "32", "--ctrl-k", "16", "--dim", "8", "--rank", "4", "--device", "cpu", "--measure-from", "2",
         "--measure-steps", "3", "--log-every", "5", "--reserve-export-minutes", "0.05", "--gate-mode", "off",
         "--delta-bound", "6", "--roles", "2", "--share-window", "10", "--time-every", "4", "--unit-buffer", "2",
         "--train-budget-minutes", "20", "--eval-budget-minutes", "10"]


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)], capture_output=True,
                          text=True)


def params(run_dir):
    import torch
    ck = sorted((run_dir / "checkpoints").glob("ckpt_*.pt"))[-1]
    return torch.load(ck, map_location="cpu", weights_only=False)


class TrainV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(7)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        for i in range(3):                                  # K: three shards of a large study
            n_c = 120
            x = np.vstack([counts(rng, p, n_c), counts(rng, q, 90), counts(rng, q, 90), counts(rng, q, 80)])
            t = ["NTC"] * n_c + ["G1"] * 90 + ["G2"] * 90 + ["G3"] * 80
            write_shard(sh / f"sk_{i}.h5ad", x, "sk", "K", f"K{i}", t, [f"K{i}_{j}-1" for j in range(len(t))],
                        "file://sk")
        write_shard(sh / "sq.h5ad", np.vstack([counts(rng, p, 100), counts(rng, q, 60), counts(rng, q, 60)]), "sq", "Q",
                    "Q1", ["NTC"] * 100 + ["G1"] * 60 + ["G4"] * 60, [f"Q{i}-1" for i in range(220)], "file://sq")
        write_shard(sh / "ss.h5ad", np.vstack([counts(rng, p, 40), counts(rng, q, 30), counts(rng, q, 30)]), "ss", "S",
                    "S1", ["NTC"] * 40 + ["G2"] * 30 + ["G3"] * 30, [f"S{i}-1" for i in range(100)], "file://ss")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 100), counts(rng, q, 40), counts(rng, q, 40),
                                               counts(rng, q, 30)]), "sa", "La", "A1",
                    ["NTC"] * 100 + ["G1"] * 40 + ["G2"] * 40 + ["G4"] * 30, [f"A{i}-1" for i in range(210)],
                    "file://sa")
        write_shard(sh / "sb.h5ad", np.vstack([counts(rng, p, 80), counts(rng, q, 30), counts(rng, q, 30)]), "sb", "Lb",
                    "B1", ["NTC"] * 80 + ["G2"] * 30 + ["G3"] * 30, [f"B{i}-1" for i in range(140)], "file://sb")
        keys = {s: key_in_fold(s, 0, want=(s == "G4")) for s in ("G1", "G2", "G3", "G4")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE", "Lb": "LINE"}}), encoding="utf-8")
        cls.pre = run("prepass", "--shards", sh, "--axis", d / "axis.csv", "--line-groups", d / "groups.json",
                      "--holdout-group", "LINE", "--hidden-fold", "0", "--target-keys", d / "keys.json",
                      "--pool-size", "48", "--ctrl-k", "16", "--input-genes", "16", "--eval-min-cells", "10",
                      "--min-controls-per-key", "20", "--out", d / "pre")
        assert cls.pre.returncode == 0, cls.pre.stderr[-3000:]
        cls.manifest = make_twins(sh, d / "twins")
        arms = ["--arm", "a=identity", "--arm", "m=identity/mean"]
        common = ["--prepass", d / "pre", *arms, "--epochs", "1", *TRAIN]
        cls.h5 = run("train", "--out", d / "h5", *common)
        cls.fast = run("train", "--out", d / "fast", "--fast-roots", d / "twins", *common)
        cls.part = run("train", "--out", d / "part", "--fast-roots", d / "twins", "--stop-after-steps", "6",
                       "--checkpoint-minutes", "0", *common)
        cls.resumed = run("train", "--out", d / "resumed", "--fast-roots", d / "twins", "--resume", d / "part", *common)
        cls.workers = run("train", "--out", d / "workers", "--fast-roots", d / "twins", "--workers", "2", *common)
        cls.epoch = run("train", "--out", d / "epoch", "--fast-roots", d / "twins", "--sampler", "epoch",
                        "--buffer-shards", "1", "--prepass", d / "pre", *arms, "--epochs", "0.25", *TRAIN)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, *parts):
        return json.loads(self.d.joinpath(*parts).read_text(encoding="utf-8"))

    def test_runs_finished(self):
        for name in ("h5", "fast", "part", "resumed", "workers"):
            proc = getattr(self, name)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr[-3000:]}")
        cfg = self.read("fast", "config.json")
        self.assertEqual(cfg["code_version"], 5)      # this folder's copy: version 5 with its options off is version 4
        self.assertEqual(cfg["sampler"]["kind"], "balanced")
        self.assertIn("compact twins", cfg["reads"])
        self.assertIn("weighs 1", cfg["loss"]["rule"])

    def test_exposure_receipt(self):
        exp = self.read("fast", "exposure.json")
        self.assertTrue(exp["passed"], exp)
        self.assertEqual(exp["groups"], ["K", "Q", "S"])
        self.assertGreaterEqual(exp["complete_windows"], 3)
        for w in exp["all_windows"]:
            if not w["partial"]:
                self.assertFalse(w["units_not_drawn"])
                for v in w["by_group"].values():
                    self.assertLess(abs(v - 1 / 3), 0.02)
        cov = self.read("fast", "coverage.json")
        self.assertTrue(cov["exposure"]["passed"])
        self.assertGreater(cov["units"]["S::ss"]["draws_per_cell"], cov["units"]["K::sk"]["draws_per_cell"])
        tg = cov["targets"]                      # amendment §10: contexts and targets reached, reported
        self.assertEqual(sorted(tg["by_key"]), ["sk|K", "sq|Q", "ss|S"])
        self.assertTrue(all(0 < v["targets_seen"] <= v["targets_offered"] for v in tg["by_key"].values()))
        self.assertIn("guides", tg["not_certified"])
        t = cov["timing"]
        self.assertGreater(t["compute_steps_timed"], 0)
        self.assertGreater(t["loader"]["batches"], 0)
        for k in ("sample_seconds", "read_decode_seconds", "assemble_seconds"):
            self.assertIn(k, t["loader_seconds_per_batch"])

    def test_twins_read_like_the_shards(self):
        a, b = params(self.d / "h5"), params(self.d / "fast")
        self.assertEqual(a["batch_chain"], b["batch_chain"])
        for arm in a["models"]:
            for k, v in a["models"][arm].items():
                np.testing.assert_allclose(v.numpy(), b["models"][arm][k].numpy(), rtol=1e-5, atol=1e-6)
        res = self.read("fast", "shards_resolved.json")
        self.assertTrue(all(r["path"].endswith(".fcsr.npz") and r["twin_sha256"] for r in res))
        self.assertEqual(self.read("fast", "verify.json")["differ"], [])

    def test_bad_twins_refused(self):
        bad = self.d / "twins_bad"
        shutil.copytree(self.d / "twins", bad)
        m = json.loads((bad / "fast_manifest.json").read_text(encoding="utf-8"))
        m["shards"][0]["source_sha256"] = "0" * 64                         # the twin of another file
        (bad / "fast_manifest.json").write_text(json.dumps(m), encoding="utf-8")
        proc = run("train", "--out", self.d / "bad_run", "--fast-roots", bad, "--prepass", self.d / "pre",
                   "--arm", "a=identity", "--epochs", "1", *TRAIN)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("without a valid twin", proc.stderr[-2000:])
        removed = self.read("fast", "config.json")["args"]
        self.assertEqual(removed["budget_minutes"], "None")
        old = run("train", "--out", self.d / "old_flag", "--prepass", self.d / "pre", "--arm", "a=identity",
                  "--budget-minutes", "10", *TRAIN)
        self.assertNotEqual(old.returncode, 0)
        self.assertIn("replaced by --train-budget-minutes", old.stderr[-2000:])

    def test_resume_reaches_the_straight_run(self):
        straight, resumed = params(self.d / "fast"), params(self.d / "resumed")
        self.assertEqual(straight["batch_chain"], resumed["batch_chain"])
        self.assertEqual(straight["windows"], resumed["windows"])
        for arm in straight["models"]:
            for k, v in straight["models"][arm].items():
                np.testing.assert_allclose(v.numpy(), resumed["models"][arm][k].numpy(), rtol=1e-5, atol=1e-6)
        self.assertTrue(self.read("resumed", "exposure.json")["passed"])

    def test_loader_processes_give_the_same_batches(self):
        self.assertEqual(params(self.d / "fast")["batch_chain"], params(self.d / "workers")["batch_chain"])

    def test_budgets(self):
        plan = self.read("fast", "plan.json")
        self.assertEqual(plan["train_budget_minutes"], 20.0)
        self.assertIn("evaluation_estimate_seconds", plan)
        done = self.read("fast", "done.json")
        self.assertTrue(done["evaluation_complete"])
        self.assertTrue(done["exposure_passed"])
        ev = self.read("fast", "a", "eval.json")["summary"]["evaluation"]
        self.assertEqual(ev["budget_seconds"], 600.0)

    def test_epoch_sampler_stopped_early_fails_the_rule(self):
        self.assertEqual(self.epoch.returncode, 0, self.epoch.stderr[-3000:])
        exp = self.read("epoch", "exposure.json")
        self.assertEqual(exp["sampler"], "epoch")
        self.assertFalse(exp["passed"])


if __name__ == "__main__":
    unittest.main()
