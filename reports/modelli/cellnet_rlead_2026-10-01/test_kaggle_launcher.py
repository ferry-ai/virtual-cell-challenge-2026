"""The Kaggle launcher of this folder, without Kaggle: dry runs, and the generated kernels run on a local /kaggle tree.

- `code --dry-run` stages this folder's three files with their sha256 under <owner>/rlead-cellnet-code;
- `kernel --dry-run` writes kernels owned by --owner that attach the shards and assets of --data-owner, accept the
  arm `generic`, and refuse an owner equal to the data owner;
- the prepass kernel (CPU) and then the training kernel (arms identity and generic, resume cycle), run against a
  fake /kaggle/input with synthetic shards mounted under the two owners as Kaggle mounts them, end with return code
  0, and a code file that differs from its manifest stops the kernel before anything runs;
- an evaluation kernel (--eval-from, 2/10) reads the training kernel's output, trains nothing, and evaluates the same
  last checkpoint to the same eval.json, adding eval_discrimination.json.

    python -m unittest test_kaggle_launcher -v          (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from test_prepass import GENES, counts, write_shard

HERE = Path(__file__).resolve().parent
OWNER, DATA = "teammate-test", "davidmaisterx"
SMALL = ("--epochs 1 --batch 32 --ctrl-k 8 --buffer-shards 2 --dim 8 --rank 4 --measure-from 2 --measure-steps 3 "
         "--log-every 5 --reserve-export-minutes 0.05 --eval-reserve-seconds 5")


def launch(*args):
    return subprocess.run([sys.executable, str(HERE / "kaggle_train.py"), *map(str, args)], capture_output=True,
                          text=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_kernel(stage, root, inp):
    """Run a staged run.py with /kaggle/input moved to inp and /kaggle/working to root/working."""
    text = (Path(stage) / "run.py").read_text(encoding="utf-8")
    text = text.replace('Path("/kaggle/input")', repr(str(inp)).join(("Path(", ")")))
    text = text.replace('Path("/kaggle/working")', repr(str(root / "working")).join(("Path(", ")")))
    (root / "working").mkdir(parents=True)
    (root / "run_local.py").write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, str(root / "run_local.py")], capture_output=True, text=True, cwd=root)


class DryRuns(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_stage_carries_this_folders_files_and_their_hashes(self):
        r = launch("code", "--config-dir", self.d, "--owner", OWNER, "--stage", self.d / "c", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        meta = json.loads((self.d / "c" / "dataset-metadata.json").read_text())
        self.assertEqual(meta["id"], f"{OWNER}/rlead-cellnet-code")
        man = json.loads((self.d / "c" / "code_manifest.json").read_text())
        for f in ("cellnet.py", "cell_data.py", "train_cellnet.py"):
            self.assertEqual(man["files"][f], sha(HERE / f))
            self.assertEqual(sha(self.d / "c" / f), sha(HERE / f))
        self.assertEqual(sorted(p.name for p in (self.d / "c").iterdir()),
                         ["cell_data.py", "cellnet.py", "code_manifest.json", "dataset-metadata.json", "train_cellnet.py"])

    def test_kernel_owned_by_owner_reads_data_of_data_owner(self):
        r = launch("kernel", "--config-dir", self.d, "--owner", OWNER, "--stage", self.d / "k", "--slug", "rlead-t1",
                   "--datasets", "rlab-a", "rlab-b", "--prepass-from", "rlead-p1", "--arm", "g=generic",
                   "--arm", "d=descriptors", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        meta = json.loads((self.d / "k" / "kernel-metadata.json").read_text())
        self.assertEqual(meta["id"], f"{OWNER}/rlead-t1")
        self.assertEqual(meta["dataset_sources"], [f"{OWNER}/rlead-cellnet-code", f"{DATA}/rlab-cellnet-code",
                                                   f"{DATA}/rlab-a", f"{DATA}/rlab-b"])
        self.assertEqual(meta["kernel_sources"], [f"{OWNER}/rlead-p1"])
        self.assertTrue(meta["is_private"])
        self.assertFalse(meta["enable_internet"])

    def test_refusals(self):
        same = launch("kernel", "--config-dir", self.d, "--owner", DATA, "--stage", self.d / "k1", "--slug", "x",
                      "--datasets", "rlab-a", "--prepass-args=", "--dry-run")
        self.assertNotEqual(same.returncode, 0)
        bad = launch("kernel", "--config-dir", self.d, "--owner", OWNER, "--stage", self.d / "k2", "--slug", "x",
                     "--datasets", "rlab-a", "--prepass-from", "p", "--arm", "x=unknown", "--dry-run")
        self.assertNotEqual(bad.returncode, 0)


class LocalKaggle(unittest.TestCase):
    """Prepass kernel, then training kernel, on synthetic shards mounted as Kaggle mounts them."""

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(5)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        inp = d / "kaggle" / "input"
        # the data owner's shard dataset, with its files.json as publish_kaggle.py writes it
        ds = inp / "datasets" / DATA / "rlab-syn"
        ds.mkdir(parents=True)
        targets = [f"G{i}" for i in range(1, 13)]
        for k, (ctx, lib) in enumerate((("K", "L1"), ("K", "L2"), ("H", "L3"))):
            x = np.vstack([counts(rng, p, 120)] + [counts(rng, q, 25) for _ in targets])
            t = ["NTC"] * 120 + [g for g in targets for _ in range(25)]
            write_shard(ds / f"s{k}.h5ad", x, f"s{k}", ctx, lib, t, [f"S{k}_{i}-1" for i in range(len(t))],
                        f"file://s{k}")
        (ds / "files.json").write_text(json.dumps([
            {"file": f.name, "bytes": f.stat().st_size, "sha256": sha(f), "cells": 120 + 25 * len(targets)}
            for f in sorted(ds.glob("*.h5ad"))]))
        # the data owner's assets: the axis and the descriptors
        assets = inp / "datasets" / DATA / "rlab-cellnet-code"
        assets.mkdir(parents=True)
        (assets / "gene_names.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        np.save(assets / "descriptors.npy", rng.normal(size=(len(GENES), 6)).astype(np.float32))
        (assets / "genes.txt").write_text("\n".join(GENES) + "\n", encoding="utf-8")
        # the owner's code dataset, staged by the launcher itself
        cls.code = launch("code", "--config-dir", d, "--owner", OWNER, "--stage", d / "stage_code", "--dry-run")
        shutil.copytree(d / "stage_code", inp / "datasets" / OWNER / "rlead-cellnet-code")
        common = ["--config-dir", d, "--owner", OWNER, "--datasets", "rlab-syn", "--cpu", "--dry-run"]
        cls.k_pre = launch("kernel", *common, "--stage", d / "stage_pre", "--slug", "rlead-prepass-syn",
                           "--prepass-args=--holdout-context H --holdout-target-frac 0.34 --pool-size 256 "
                           "--input-genes 16 --eval-min-cells 10 --min-controls-per-key 20")
        cls.pre = run_kernel(d / "stage_pre", d / "kaggle_pre", inp)
        # the training kernel reads the prepass from the output of the first kernel, mounted as a notebook
        out = inp / "notebooks" / OWNER / "rlead-prepass-syn"
        shutil.copytree(d / "kaggle_pre" / "working", out)
        cls.k_train = launch("kernel", *common, "--stage", d / "stage_train", "--slug", "rlead-train-syn",
                             "--prepass-from", "rlead-prepass-syn", "--arm", "ident=identity", "--arm", "gen=generic",
                             "--cycle", "3", "6", f"--train-args={SMALL}")
        cls.train = run_kernel(d / "stage_train", d / "kaggle_train", inp)
        # the evaluation kernel reads the training kernel's output, mounted as a notebook
        shutil.copytree(d / "kaggle_train" / "working", inp / "notebooks" / OWNER / "rlead-train-syn")
        cls.k_eval = launch("kernel", *common, "--stage", d / "stage_eval", "--slug", "rlead-eval-syn",
                            "--prepass-from", "rlead-prepass-syn", "--eval-from", "rlead-train-syn",
                            "--arm", "ident=identity", "--arm", "gen=generic", f"--train-args={SMALL}")
        cls.ev = run_kernel(d / "stage_eval", d / "kaggle_eval", inp)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_stages_written(self):
        for r in (self.code, self.k_pre, self.k_train, self.k_eval):
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_prepass_kernel_verifies_and_runs(self):
        self.assertEqual(self.pre.returncode, 0, self.pre.stdout + self.pre.stderr)
        w = self.d / "kaggle_pre" / "working"
        v = json.loads((w / "verify.json").read_text())
        self.assertEqual(v["bad"], [])
        self.assertEqual(sorted(v["code_files"]), ["cell_data.py", "cellnet.py", "train_cellnet.py"])
        self.assertIn(f"datasets/{DATA}/rlab-syn", v["mounts"]["rlab-syn"].replace("\\", "/"))
        self.assertIn(f"datasets/{OWNER}/rlead-cellnet-code", v["code"].replace("\\", "/"))
        self.assertTrue((w / "prepass" / "controls.json").is_file(), (w / "prepass.log").read_text())
        self.assertEqual(json.loads((w / "kernel_done.json").read_text())["return_code"], None)

    def test_training_kernel_resumes_and_trains_both_arms(self):
        w = self.d / "kaggle_train" / "working"
        logs = "".join((w / f).read_text() for f in ("train.log",) if (w / f).is_file())
        self.assertEqual(self.train.returncode, 0, self.train.stdout + self.train.stderr + logs)
        self.assertTrue(json.loads((w / "resume_check.json").read_text())["passed"])
        self.assertEqual(json.loads((w / "kernel_done.json").read_text())["return_code"], 0)
        cfg = json.loads((w / "train" / "config.json").read_text())
        self.assertEqual({x["name"]: x["target_code"] for x in cfg["arms"]}, {"ident": "identity", "gen": "generic"})
        self.assertEqual((cfg["mixture"], cfg["loss_norm"]), ("logits", "global"))
        self.assertTrue(any((w / "train" / "checkpoints").glob("ckpt_*.pt")))
        self.assertTrue((w / "train" / "done.json").is_file())

    def test_eval_kernel_trains_nothing_and_reproduces_the_evaluation(self):
        w, t = self.d / "kaggle_eval" / "working", self.d / "kaggle_train" / "working"
        logs = (w / "train.log").read_text() if (w / "train.log").is_file() else ""
        self.assertEqual(self.ev.returncode, 0, self.ev.stdout + self.ev.stderr + logs)
        meta = json.loads((self.d / "stage_eval" / "kernel-metadata.json").read_text())
        self.assertEqual(meta["kernel_sources"], [f"{OWNER}/rlead-prepass-syn", f"{OWNER}/rlead-train-syn"])
        cov, cov_t = (json.loads((x / "train" / "coverage.json").read_text()) for x in (w, t))
        self.assertEqual(cov["stop"], "eval-only")
        self.assertEqual(cov["steps"], cov_t["steps"])
        self.assertFalse((w / "train" / "checkpoints").exists() and any((w / "train" / "checkpoints").iterdir()))
        for arm in ("ident", "gen"):
            e, e_t = (json.loads((x / "train" / arm / "eval.json").read_text()) for x in (w, t))
            for c in ("C", "T", "J"):
                self.assertEqual(e["summary"][c], e_t["summary"][c])
            d, d_t = (json.loads((x / "train" / arm / "eval_discrimination.json").read_text()) for x in (w, t))
            self.assertTrue(d["eval_only"])
            self.assertEqual({c: d[c] for c in ("C", "T", "J") if c in d}, {c: d_t[c] for c in ("C", "T", "J") if c in d_t})

    def test_code_that_differs_from_its_manifest_stops_the_kernel(self):
        root = self.d / "kaggle_tampered"
        shutil.copytree(self.d / "kaggle" / "input", root / "input")
        with open(root / "input" / "datasets" / OWNER / "rlead-cellnet-code" / "cellnet.py", "a") as fh:
            fh.write("\n# changed after staging\n")
        r = run_kernel(self.d / "stage_pre", root, root / "input")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rlead-cellnet-code/cellnet.py", json.dumps(json.loads((root / "working" / "verify.json").read_text())["bad"]))
        self.assertFalse((root / "working" / "prepass").exists())


if __name__ == "__main__":
    unittest.main()
