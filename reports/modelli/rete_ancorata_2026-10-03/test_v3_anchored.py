"""Version 3 (the transfer-anchored network) end to end on the synthetic corpus of test_v2_stages, with made-up anchors
whose answers are known:
- with --lr 0 the network is its anchor: the first arm's exported shifts equal 'ancora_sola' (gain 1, correction 0 at
  initialisation), and are 0 for the groups without an anchor (J);
- a training moves away from the anchor (lr > 0);
- anchors that break the rule are refused before training: a row with its own group among the sources, a hidden target,
  another held-out group, a file that does not hash as its manifest says;
- a resume with other anchors is refused; the generator adds the anchor of each held-out target.

    python -m unittest test_v3_anchored -v        (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import hashlib
import json
import pickle
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anchors as A  # noqa: E402
from test_prepass import GENES, counts  # noqa: E402
from test_v2_stages import key_in_fold, write_shard  # noqa: E402

TRAIN = ["--epochs", "2", "--batch", "32", "--ctrl-k", "32", "--buffer-shards", "2", "--dim", "8", "--rank", "4",
         "--device", "cpu", "--measure-from", "2", "--measure-steps", "3", "--log-every", "5",
         "--reserve-export-minutes", "0.05", "--eval-reserve-seconds", "5", "--gate-mode", "off", "--delta-bound", "6",
         "--roles", "2"]


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)], capture_output=True, text=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_anchors(folder: Path, st, rng, extra=(), held=None):
    """Anchors for every training pair and the held-out C groups, sources a made-up group 'SRC', plus `extra` rows."""
    index, rows = [], []
    G = len(st["genes"])
    for L, role, syms in A.jobs_of(st):
        for s in syms:
            index.append({"group": L, "symbol": s, "target_key": f"K:{s}", "role": role, "sources": ["SRC"],
                          "support": 1})
    index += list(extra)
    for _ in index:
        v = rng.normal(0, 0.4, G).astype(np.float32)
        v[rng.random(G) < 0.1] = np.nan
        rows.append(v.astype(np.float16))
    U, _ = np.linalg.qr(rng.normal(size=(G, 2)))
    folder.mkdir(parents=True)
    np.savez(folder / "anchors.npz", rows=np.stack(rows), support=np.ones(len(index), np.int16),
             U=U.astype(np.float32), genes=np.array([str(g) for g in st["genes"]]))
    (folder / "anchors.json").write_text(json.dumps(index), encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps({
        "held_group": held or st["holdout_group"], "rows": len(index), "checks": {"passed": True},
        "outputs": {"anchors_npz": sha(folder / "anchors.npz"), "anchors_json": sha(folder / "anchors.json")}}),
        encoding="utf-8")
    return folder


class AnchoredV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(5)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        x, t, lib = [], [], []
        for L, nc in (("L1", 200), ("L2", 70), ("L3", 5)):
            x += [counts(rng, p, nc), counts(rng, q, 40), counts(rng, q, 35), counts(rng, q, 30)]
            t += ["NTC"] * nc + ["G1"] * 40 + ["G2"] * 35 + ["G3"] * 30
            lib += [L] * (nc + 105)
        write_shard(sh / "sk.h5ad", np.vstack(x), "sk", "K", np.array(lib), t, [f"K{i}-1" for i in range(len(t))],
                    "file://sk")
        write_shard(sh / "sq.h5ad", np.vstack([counts(rng, p, 150), counts(rng, q, 60), counts(rng, q, 60)]), "sq", "Q",
                    "Q1", ["NTC"] * 150 + ["G1"] * 60 + ["G4"] * 60, [f"Q{i}-1" for i in range(270)], "file://sq")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 150), counts(rng, q, 50), counts(rng, q, 50),
                                               counts(rng, q, 40)]), "sa", "La", "A1",
                    ["NTC"] * 150 + ["G1"] * 50 + ["G2"] * 50 + ["G4"] * 40, [f"A{i}-1" for i in range(290)],
                    "file://sa")
        keys = {s: key_in_fold(s, 0, want=(s == "G4")) for s in ("G1", "G2", "G3", "G4")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE"}}), encoding="utf-8")
        cls.pre = run("prepass", "--shards", sh, "--axis", d / "axis.csv", "--line-groups", d / "groups.json",
                      "--holdout-group", "LINE", "--hidden-fold", "0", "--target-keys", d / "keys.json",
                      "--pool-size", "64", "--ctrl-k", "32", "--input-genes", "16", "--eval-min-cells", "10",
                      "--min-controls-per-key", "20", "--out", d / "pre")
        assert cls.pre.returncode == 0, cls.pre.stderr[-3000:]
        cls.st = pickle.loads((d / "pre" / "prepass.pkl").read_bytes())
        cls.anchors = write_anchors(d / "anchors", cls.st, np.random.default_rng(1))
        arms = ["--arm", "a=both", "--arm", "m=both/mean"]
        cls.frozen = run("train", "--prepass", d / "pre", "--out", d / "frozen", "--anchors", cls.anchors, *arms,
                         "--lr", "0", *TRAIN)
        cls.learned = run("train", "--prepass", d / "pre", "--out", d / "learned", "--anchors", cls.anchors, *arms,
                          *TRAIN)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def shifts(self, run_dir, arm):
        with np.load(self.d / run_dir / arm / "eval_shifts.npz") as z:
            return z["predicted"].astype(np.float32)

    def test_runs_finished(self):
        for proc in (self.frozen, self.learned):
            self.assertEqual(proc.returncode, 0, proc.stderr[-3000:])
        cfg = json.loads((self.d / "frozen" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["code_version"], 3)
        self.assertEqual(cfg["args"]["anchors_sha256"], sha(self.anchors / "anchors.npz"))

    def test_untrained_network_is_its_anchor(self):
        groups = json.loads((self.d / "frozen" / "eval_groups.json").read_text(encoding="utf-8"))
        net, anc = self.shifts("frozen", "a"), self.shifts("frozen", A_ARM)
        anchored = [i for i, g in enumerate(groups) if g["class"] == "C"]
        self.assertTrue(anchored)
        np.testing.assert_allclose(net[anchored], anc[anchored], atol=2e-3, equal_nan=True)
        self.assertGreater(np.nanmax(np.abs(anc[anchored])), 0.1)          # the anchor is not zero
        for i, g in enumerate(groups):
            if g["class"] == "J":                                           # hidden targets have no anchor
                self.assertLess(np.nanmax(np.abs(net[i])), 1e-3)

    def test_training_moves_away_from_the_anchor(self):
        groups = json.loads((self.d / "learned" / "eval_groups.json").read_text(encoding="utf-8"))
        c = [i for i, g in enumerate(groups) if g["class"] == "C"]
        diff = np.nanmax(np.abs(self.shifts("learned", "a")[c] - self.shifts("learned", A_ARM)[c]))
        self.assertGreater(diff, 1e-3)

    def refused(self, folder, why):
        proc = run("train", "--prepass", self.d / "pre", "--out", self.d / f"bad_{folder.name}", "--anchors", folder,
                   "--arm", "a=both", *TRAIN)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(why, proc.stderr[-2000:])

    def test_leaks_and_tampering_are_refused(self):
        rng = np.random.default_rng(2)
        own = write_anchors(self.d / "own", self.st, rng, extra=[{
            "group": "K", "symbol": "G3", "target_key": "x", "role": "train", "sources": ["K"], "support": 1}])
        self.refused(own, "leakage rule")
        hidden = write_anchors(self.d / "hidden", self.st, rng, extra=[{
            "group": "Q", "symbol": "G4", "target_key": "x", "role": "train", "sources": ["SRC"], "support": 1}])
        self.refused(hidden, "leakage rule")
        other = write_anchors(self.d / "other", self.st, rng, held="K")
        self.refused(other, "anchors of K")
        tampered = self.d / "tampered"
        shutil.copytree(self.anchors, tampered)
        with np.load(tampered / "anchors.npz") as z:
            parts = {k: z[k] for k in z.files}
        parts["rows"] = parts["rows"] * 2
        np.savez(tampered / "anchors.npz", **parts)
        self.refused(tampered, "does not hash")

    def test_resume_with_other_anchors_is_refused(self):
        first = run("train", "--prepass", self.d / "pre", "--out", self.d / "part", "--anchors", self.anchors,
                    "--arm", "a=both", "--stop-after-steps", "4", "--checkpoint-minutes", "0", *TRAIN)
        self.assertEqual(first.returncode, 0, first.stderr[-3000:])
        other = write_anchors(self.d / "other_resume", self.st, np.random.default_rng(3))
        proc = run("train", "--prepass", self.d / "pre", "--out", self.d / "resumed", "--anchors", other,
                   "--arm", "a=both", "--resume", self.d / "part", *TRAIN)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("anchors_sha256", proc.stderr[-2000:])

    def test_generated_cells_carry_the_anchor(self):
        targets = self.d / "gen_targets.json"
        targets.write_text(json.dumps([{"key": "sa|La", "symbol": "G1"}, {"key": "sa|La", "symbol": "G2"}]),
                           encoding="utf-8")
        out = self.d / "gen" / "cells_a.npz"
        proc = subprocess.run([sys.executable, str(HERE / "generate_cells.py"), "--prepass", str(self.d / "pre"),
                               "--arm-dir", str(self.d / "frozen" / "a"), "--anchors", str(self.anchors),
                               "--targets", str(targets), "--n", "12", "--ctrl-k", "32", "--out", str(out)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-3000:])
        side = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertTrue(all(b["anchored"] for b in side["blocks"]))
        no_anchor = subprocess.run([sys.executable, str(HERE / "generate_cells.py"), "--prepass", str(self.d / "pre"),
                                    "--arm-dir", str(self.d / "frozen" / "a"), "--targets", str(targets), "--n", "12",
                                    "--ctrl-k", "32", "--out", str(self.d / "gen" / "cells_x.npz")],
                                   capture_output=True, text=True)
        self.assertNotEqual(no_anchor.returncode, 0)                  # an anchored model needs its anchors


A_ARM = "ancora_sola"

if __name__ == "__main__":
    unittest.main()
