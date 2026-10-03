"""The package of the lanes for Kaggle (kaggle_lanes.py), without running a lane.

- the code snapshot is enough: unpacked alone in an empty folder, lane_b and bench_effects import (every module they
  need is inside it, laid out as in the repository);
- the kernel's own run.py, on a mock input, checks the snapshot's sha256 and the scorer version, rebuilds the cube
  folder from the flat dataset, points the protocol at the dataset's gene table and stops on the missing inputs before
  any lane, naming them; a snapshot that is not the launcher's is refused.

    python -m unittest test_kaggle_lanes -v      (from this folder, with the project venv)
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kaggle_lanes as KL  # noqa: E402

OWNER = "davideferrante11"


class LanesPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = Path(cls.tmp.name)
        cls.raw, cls.names = KL.snapshot()
        cls.args = types.SimpleNamespace(owner=OWNER, held_group="H1", train_kernel="train-k", gen_kernel="gen-k",
                                         real_kernel="real-k", prepass_kernel="pre-k", anchors_kernel="anc-k",
                                         anchors_dir="anchors_H1_all", code_slug="code-ds", cube_slug="cube-ds")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_snapshot_alone_imports_the_lanes(self):
        root = self.d / "alone"
        zipfile.ZipFile(io.BytesIO(self.raw)).extractall(root)
        env = {**os.environ, "PYTHONPATH": str(root / "src")}
        r = subprocess.run([sys.executable, "-c", "import lane_b, bench_effects, anchors; print(lane_b.HERE)"],
                           cwd=root / KL.V4, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        self.assertIn(str(root), r.stdout)                         # imported from the snapshot, not from the repository
        self.assertEqual(self.raw, KL.snapshot()[0])               # the same bytes for the same files

    def kernel(self, text: str, name: str):
        inp, out = self.d / f"in_{name}", self.d / f"out_{name}"
        cube = inp / "datasets" / OWNER / "cube-ds"
        cube.mkdir(parents=True)
        (cube / "cube__manifest.json").write_text("{}", encoding="utf-8")
        (cube / "cube__k562_gwps__raw.npy").write_bytes(b"x")
        (cube / "gene_coordinates_gencode_v50.tsv").write_text("symbol\tgene_id\n", encoding="utf-8")
        for k in ("train-k", "gen-k", "real-k", "pre-k", "anc-k"):
            (inp / "notebooks" / OWNER / k).mkdir(parents=True)
        (inp / "datasets" / OWNER / "code-ds").mkdir(parents=True)
        out.mkdir()
        (self.d / f"run_{name}.py").write_text(text, encoding="utf-8", newline="\n")
        env = {**os.environ, "VCC_KAGGLE_INPUT": str(inp), "VCC_KAGGLE_OUT": str(out), "VCC_SKIP_PIP": "1"}
        return subprocess.run([sys.executable, str(self.d / f"run_{name}.py")], capture_output=True, text=True,
                              env=env), out

    def test_kernel_prepares_and_stops_on_missing_inputs(self):
        text, prm = KL.kernel_text(self.args, self.raw)
        proc, out = self.kernel(text, "ok")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("inputs missing", proc.stderr)
        self.assertIn("eval_groups.json", proc.stderr)
        self.assertTrue((out / "cube_r2" / "manifest.json").is_file())
        self.assertTrue((out / "cube_r2" / "k562_gwps" / "raw.npy").is_file())
        proto = json.loads((out / "PROTOCOLLO.json").read_text(encoding="utf-8"))
        self.assertTrue(proto["parameters"]["gene_coordinates"].endswith("gene_coordinates_gencode_v50.tsv"))
        self.assertTrue(Path(proto["parameters"]["gene_coordinates"]).is_file())
        env = json.loads((out / "env.json").read_text(encoding="utf-8"))
        self.assertEqual(env["versions"]["cell-eval2"], prm["scorer_version"])
        self.assertFalse((out / "laneA").exists() or (out / "laneB").exists())

    def test_changed_snapshot_refused(self):
        text, prm = KL.kernel_text(self.args, self.raw)
        bad = text.replace(prm["snapshot_sha256"], "0" * 64)
        proc, out = self.kernel(bad, "bad")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("snapshot", proc.stderr)
        self.assertFalse((out / "repo").exists())


if __name__ == "__main__":
    unittest.main()
