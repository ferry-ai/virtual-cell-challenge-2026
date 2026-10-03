"""The kernel of the nested-samples study (kaggle_nested.py) on a mock /kaggle/input, before any push.

On the synthetic corpus of test_nested_samples (3 libraries x 2 guides; a held-out LINE), with the real code files
staged as the code dataset, the prepass state as a kernel output, the shards as a corpus dataset and their twins as a
build kernel's output:
- the kernel's own run.py passes its preflight (code, state, every shard and every twin re-hashed), runs the study and
  writes the same groups table as nested_samples.py run directly on the same inputs;
- a twin with one byte changed (same size), a state other than the one given, or a module of the code dataset that is
  not the launcher's file each end the kernel with an error before the study: no nested/ folder, the problem named in
  verify.json.

    python -m unittest test_kaggle_nested -v      (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kaggle_nested as KN  # noqa: E402
from fixtures import GENES, counts, key_in_fold, make_twins  # noqa: E402
from test_nested_samples import CAPS, write_shard  # noqa: E402

OWNER = "davideferrante11"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class KernelNested(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(3)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        q = p.copy(); q[5] *= 4; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        inp = d / "input"
        sh = inp / "datasets" / "davidmaisterx" / "rlab-test"
        sh.mkdir(parents=True)
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        for i in range(3):
            t = ["NTC"] * 60 + ["G1"] * 30 + ["G2"] * 6
            g = ["NTC"] * 60 + [f"G1_g{j % 2}" for j in range(30)] + [f"G2_g{j % 2}" for j in range(6)]
            write_shard(sh / f"sk_{i}.h5ad", np.vstack([counts(rng, p, 60), counts(rng, q, 36)]), "sk", "K",
                        f"K{i}", t, g, [f"K{i}_{j}-1" for j in range(96)], "file://sk")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 80), counts(rng, q, 30)]), "sa", "La", "A1",
                    ["NTC"] * 80 + ["G1"] * 30, ["NTC"] * 80 + ["G1_g0"] * 30, [f"A{i}-1" for i in range(110)],
                    "file://sa")
        keys = {s: key_in_fold(s, 0, want=False) for s in ("G1", "G2")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE"}}), encoding="utf-8")
        pre = inp / "notebooks" / OWNER / "pre-k" / "prepass"
        r = subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), "prepass", "--shards", str(sh), "--axis",
                            str(d / "axis.csv"), "--line-groups", str(d / "groups.json"), "--holdout-group", "LINE",
                            "--hidden-fold", "0", "--target-keys", str(d / "keys.json"), "--pool-size", "48",
                            "--ctrl-k", "16", "--input-genes", "16", "--eval-min-cells", "10",
                            "--min-controls-per-key", "20", "--out", str(pre)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-3000:]
        make_twins(sh, inp / "notebooks" / OWNER / "fast-k" / "twins")
        code = inp / "datasets" / OWNER / "code-ds"
        code.mkdir(parents=True)
        for f in KN.CODE_FILES:
            shutil.copyfile(HERE / f, code / f)
        cls.direct = subprocess.run([sys.executable, str(HERE / "nested_samples.py"), "--prepass", str(pre),
                                     "--shard-roots", str(inp), "--fast-roots", str(inp), "--caps", *map(str, CAPS),
                                     "--out", str(d / "direct"), "--workers", "1"], capture_output=True, text=True)
        prm = KN.params(OWNER, "code-ds", "pre-k", sha(pre / "prepass.pkl"), CAPS, 1, hash_threads=2)
        (d / "run.py").write_text(KN.kernel_text(prm), encoding="utf-8", newline="\n")
        cls.good = cls.kernel(d / "run.py", inp, d / "out")
        # a twin with one byte changed, the size kept
        bad_twin = d / "input_twin"
        shutil.copytree(inp, bad_twin)
        twin = sorted((bad_twin / "notebooks" / OWNER / "fast-k" / "twins").glob("*.npz"))[0]
        raw = bytearray(twin.read_bytes())
        raw[len(raw) // 2] ^= 0xFF
        twin.write_bytes(bytes(raw))
        cls.twin = cls.kernel(d / "run.py", bad_twin, d / "out_twin")
        # a kernel told to expect another state
        other = KN.params(OWNER, "code-ds", "pre-k", "0" * 64, CAPS, 1, hash_threads=2)
        (d / "run_state.py").write_text(KN.kernel_text(other), encoding="utf-8", newline="\n")
        cls.state = cls.kernel(d / "run_state.py", inp, d / "out_state")
        # a module of the code dataset that is not the launcher's file
        bad_code = d / "input_code"
        shutil.copytree(inp, bad_code)
        with open(bad_code / "datasets" / OWNER / "code-ds" / "balanced.py", "a", encoding="utf-8") as fh:
            fh.write("\n# changed\n")
        cls.code = cls.kernel(d / "run.py", bad_code, d / "out_code")

    @classmethod
    def kernel(cls, run_py: Path, inp: Path, out: Path):
        out.mkdir()
        env = {**os.environ, "VCC_KAGGLE_INPUT": str(inp), "VCC_KAGGLE_OUT": str(out)}
        return subprocess.run([sys.executable, str(run_py)], capture_output=True, text=True, env=env)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_kernel_runs_and_equals_the_direct_run(self):
        self.assertEqual(self.direct.returncode, 0, self.direct.stderr[-3000:])
        self.assertEqual(self.good.returncode, 0, self.good.stderr[-3000:])
        out = self.d / "out"
        v = json.loads((out / "verify.json").read_text(encoding="utf-8"))
        self.assertEqual(v["problems"], [])
        self.assertEqual((v["shards"]["files"], v["twins"]["files"]), (4, 4))
        self.assertEqual(v["shards"]["differ"] + v["twins"]["differ"], [])
        self.assertEqual(json.loads((out / "kernel_done.json").read_text(encoding="utf-8"))["return_code"], 0)
        a = pd.read_csv(out / "nested" / "groups.csv.gz")
        b = pd.read_csv(self.d / "direct" / "groups.csv.gz")
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(sha(out / "code" / "nested_samples.py"), sha(HERE / "nested_samples.py"))
        self.assertEqual(len(list((out / "nested" / "selection").glob("*.npz"))), 4)

    def check_refused(self, proc, out: Path, word: str):
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse((out / "nested").exists())
        self.assertFalse((out / "kernel_done.json").exists())
        problems = json.loads((out / "verify.json").read_text(encoding="utf-8"))["problems"]
        self.assertTrue(any(word in p for p in problems), problems)

    def test_changed_twin_refused(self):
        self.check_refused(self.twin, self.d / "out_twin", "twins")

    def test_other_state_refused(self):
        self.check_refused(self.state, self.d / "out_state", "prepass state")

    def test_changed_module_refused(self):
        self.check_refused(self.code, self.d / "out_code", "code dataset")


if __name__ == "__main__":
    unittest.main()
