"""Twins of shards left in kernel outputs: build_fast_units.py through the kernel's own run.py, on a mock input.

Two fake part kernels, each with <job>/shards/<unit>/manifest.json and its shards, and the build code dataset:
- the kernel builds a twin per shard, each verified against the unit manifest and by exact decoding, and the package
  manifest is the one train_cellnet.resolve_twins accepts for a state naming those shards;
- a unit manifest whose sha256 is not the shard's makes the build fail and keeps no twin of that shard;
- a module of the code dataset that is not the launcher's file ends the kernel before anything is built.

    python -m unittest test_fast_units -v      (from this folder, with the project venv)
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fastshard as FS  # noqa: E402
import kaggle_fast_units as KU  # noqa: E402
from fixtures import GENES, counts, write_shard  # noqa: E402

OWNER = "davideferrante11"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def part(root: Path, job: str, unit: str, names, rng, p):
    """A part kernel's output: <job>/shards/<unit>/<shard>.h5ad and the unit manifest."""
    d = root / job.replace("_", "-") / job / "shards" / unit
    d.mkdir(parents=True)
    shards = []
    for name in names:
        x = counts(rng, p, 40)
        write_shard(d / f"{name}.h5ad", x, "st", "K", "L1", ["NTC"] * 20 + ["G1"] * 20,
                    [f"{name}_{i}-1" for i in range(40)], "file://x")
        shards.append({"shard": name, "bytes": (d / f"{name}.h5ad").stat().st_size, "sha256": sha(d / f"{name}.h5ad"),
                       "cells": 40})
    (d / "manifest.json").write_text(json.dumps({"unit": unit, "shards": shards}), encoding="utf-8")
    return d


class UnitTwins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(5)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        inp = d / "input"
        cls.unit_a = part(inp, "part_a_r1", "u", ["u__f1", "u__f2"], rng, p)
        part(inp, "part_b_r1", "u", ["u__f3"], rng, p)
        code = inp / "datasets" / OWNER / "build-ds"
        code.mkdir(parents=True)
        for f in KU.CODE_FILES + ("cell_data.py",):
            shutil.copyfile(HERE / f, code / f)
        prm = KU.params(OWNER, "build-ds", ["part-a-r1", "part-b-r1"], 1)
        (d / "run.py").write_text(KU.kernel_text(prm), encoding="utf-8", newline="\n")
        cls.good = cls.kernel(inp, d / "out")
        wrong = d / "input_sha"                                   # a unit manifest that names another sha256
        shutil.copytree(inp, wrong)
        mpath = wrong / "part-a-r1" / "part_a_r1" / "shards" / "u" / "manifest.json"
        m = json.loads(mpath.read_text(encoding="utf-8"))
        m["shards"][0]["sha256"] = "0" * 64
        mpath.write_text(json.dumps(m), encoding="utf-8")
        cls.bad_sha = cls.kernel(wrong, d / "out_sha")
        changed = d / "input_code"                                # a module that is not the launcher's file
        shutil.copytree(inp, changed)
        with open(changed / "datasets" / OWNER / "build-ds" / "fastshard.py", "a", encoding="utf-8") as fh:
            fh.write("\n# changed\n")
        cls.bad_code = cls.kernel(changed, d / "out_code")

    @classmethod
    def kernel(cls, inp: Path, out: Path):
        out.mkdir()
        env = {**os.environ, "VCC_KAGGLE_INPUT": str(inp), "VCC_KAGGLE_OUT": str(out)}
        return subprocess.run([sys.executable, str(cls.d / "run.py")], capture_output=True, text=True, env=env)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_twins_built_and_resolved(self):
        self.assertEqual(self.good.returncode, 0, self.good.stderr[-3000:])
        tw = self.d / "out" / "twins"
        m = json.loads((tw / "fast_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((len(m["shards"]), m["failed"]), (3, []))
        self.assertTrue(all(r["verified"] and r["matches_files_json"] for r in m["shards"]))
        import train_cellnet as TC
        state = [{"name": f"{n}.h5ad", "bytes": r["source_bytes"], "sha256": r["source_sha256"]}
                 for n, r in zip(("u__f1", "u__f2", "u__f3"), sorted(m["shards"], key=lambda r: r["name"]))]
        found = TC.resolve_twins(state, [tw])
        self.assertEqual(len(found), 3)
        src = self.unit_a / "u__f1.h5ad"
        self.assertTrue(FS.check(src, tw / FS.twin_name(src.name))["equal"])

    def test_wrong_sha_fails_and_keeps_no_twin(self):
        self.assertNotEqual(self.bad_sha.returncode, 0)
        tw = self.d / "out_sha" / "twins"
        self.assertFalse((tw / FS.twin_name("u__f1.h5ad")).exists())
        m = json.loads((tw / "fast_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([r["name"] for r in m["failed"]], ["u__f1.h5ad"])

    def test_changed_module_refused(self):
        self.assertNotEqual(self.bad_code.returncode, 0)
        self.assertFalse((self.d / "out_code" / "twins").exists())
        self.assertTrue((self.d / "out_code" / "preflight_failed.json").is_file())


if __name__ == "__main__":
    unittest.main()
