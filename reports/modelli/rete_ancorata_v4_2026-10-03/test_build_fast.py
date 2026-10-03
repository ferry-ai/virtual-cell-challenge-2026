"""build_fast.py on a mock /kaggle/input: two datasets with files.json, a glob, and a tampered sha256.

- every chosen shard gets a verified twin, the manifest lists them with the profile, and the training's resolver
  accepts them;
- a glob keeps only the matching files;
- a files.json whose sha256 is not the shard's fails the build and leaves no twin of that shard.

    python -m unittest test_build_fast -v         (from this folder, with the project venv; seconds)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fixtures import GENES, counts, write_shard  # noqa: E402


def files_json(folder: Path, tamper=None):
    out = []
    for p in sorted(folder.glob("*.h5ad")):
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        out.append({"file": p.name, "bytes": p.stat().st_size, "sha256": "0" * 64 if p.name == tamper else h})
    (folder / "files.json").write_text(json.dumps(out), encoding="utf-8")


class BuildFast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(3)
        p = rng.dirichlet(np.ones(len(GENES)))
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        for ds, names in (("ds-a", ["a1", "a2"]), ("ds-b", ["norman2019__x", "other__y"])):
            folder = d / "input" / "datasets" / "davidmaisterx" / ds
            folder.mkdir(parents=True)
            for n in names:
                write_shard(folder / f"{n}.h5ad", counts(rng, p, 30), n, "K", "L", ["NTC"] * 30,
                            [f"{n}{i}-1" for i in range(30)], f"file://{n}")
            files_json(folder)
        cls.ok = subprocess.run([sys.executable, str(HERE / "build_fast.py"), "--input", str(d / "input"),
                                 "--datasets", "ds-a", "ds-b", "--glob", "ds-b=norman2019__*.h5ad",
                                 "--out", str(d / "twins"), "--workers", "2"], capture_output=True, text=True)
        bad = d / "input_bad" / "datasets" / "davidmaisterx" / "ds-a"
        bad.mkdir(parents=True)
        for f in (d / "input" / "datasets" / "davidmaisterx" / "ds-a").glob("*.h5ad"):
            (bad / f.name).write_bytes(f.read_bytes())
        files_json(bad, tamper="a2.h5ad")
        cls.bad = subprocess.run([sys.executable, str(HERE / "build_fast.py"), "--input", str(d / "input_bad"),
                                  "--datasets", "ds-a", "--out", str(d / "twins_bad"), "--workers", "1"],
                                 capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build(self):
        self.assertEqual(self.ok.returncode, 0, self.ok.stderr[-3000:])
        m = json.loads((self.d / "twins" / "fast_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(r["name"] for r in m["shards"]), ["a1.h5ad", "a2.h5ad", "norman2019__x.h5ad"])
        self.assertTrue(all(r["verified"] and r["matches_files_json"] for r in m["shards"]))
        self.assertEqual(m["failed"], [])
        self.assertIn("h5py_read_decompress", m["profile"]["seconds_summed_over_processes"])
        for r in m["shards"]:
            twin = self.d / "twins" / r["twin"]
            self.assertEqual(hashlib.sha256(twin.read_bytes()).hexdigest(), r["twin_sha256"])

    def test_resolver_accepts_the_twins(self):
        import train_cellnet as TC
        m = json.loads((self.d / "twins" / "fast_manifest.json").read_text(encoding="utf-8"))
        shards = [{"name": r["name"], "sha256": r["source_sha256"], "bytes": r["source_bytes"]} for r in m["shards"]]
        got = TC.resolve_twins(shards, [self.d / "twins"])
        self.assertEqual([Path(p).name for p, _, _ in got], [r["twin"] for r in m["shards"]])

    def test_tampered_files_json_fails(self):
        self.assertNotEqual(self.bad.returncode, 0)
        m = json.loads((self.d / "twins_bad" / "fast_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([r["name"] for r in m["failed"]], ["a2.h5ad"])
        self.assertFalse((self.d / "twins_bad" / "a2.h5ad.fcsr.npz").exists())


if __name__ == "__main__":
    unittest.main()
