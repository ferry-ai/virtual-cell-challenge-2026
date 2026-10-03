"""The generation package of version 4, end to end, and the coherence of effect, export and generated cells.

On the synthetic corpus of test_train_v4 (held-out LINE with contexts La and Lb; G4 hidden) with made-up anchors in
version 4's manifest format (max_sources, regime-J commons):
- an anchored v4 training (balanced batches, two arms) exports its shifts;
- the kernel's own run.py (kaggle_gen.kernel_text) runs on a mock /kaggle/input built from the training's output, the
  prepass state, the anchors and the staged generation dataset (stage_data, the real FILES): every module the
  generator imports is in the dataset, every arm's cells are written, gen_done.json reports success;
- coherence: for each held-out C target, the shift of the generated cells against the same cells drawn from the
  baseline (--with-baseline) agrees with the shift the training exported for that group (correlation above 0.95 and
  small absolute error on the expressed genes); so effect -> export -> generated cells carry the same response,
  anchor included (every block is marked anchored);
- a missing module in the dataset or a missing input makes the kernel fail, not succeed silently.

    python -m unittest test_generation_v4 -v      (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anchors as A  # noqa: E402
import kaggle_gen as KG  # noqa: E402
from fixtures import GENES, counts, key_in_fold, write_shard  # noqa: E402

TRAIN = ["--batch", "32", "--ctrl-k", "16", "--dim", "8", "--rank", "4", "--device", "cpu", "--measure-from", "2",
         "--measure-steps", "3", "--log-every", "5", "--reserve-export-minutes", "0.05", "--gate-mode", "off",
         "--delta-bound", "6", "--roles", "2", "--share-window", "10", "--time-every", "4",
         "--train-budget-minutes", "20", "--eval-budget-minutes", "10", "--epochs", "2"]
OWNER = "davideferrante11"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_anchors_v4(folder: Path, st, rng):
    """Anchors for every training pair and the held-out C groups from a made-up source group, in version 4's format."""
    index, rows = [], []
    G = len(st["genes"])
    for L, role, syms in A.jobs_of(st):
        for s in syms:
            index.append({"group": L, "symbol": s, "target_key": f"K:{s}", "role": role, "sources": ["SRC"],
                          "support": 1})
    for _ in index:
        v = rng.normal(0, 0.5, G).astype(np.float32)
        rows.append(v.astype(np.float16))
    U, _ = np.linalg.qr(rng.normal(size=(G, 2)))
    folder.mkdir(parents=True)
    np.savez(folder / "anchors.npz", rows=np.stack(rows), support=np.ones(len(index), np.int16),
             U=U.astype(np.float32), genes=np.array([str(g) for g in st["genes"]]))
    (folder / "anchors.json").write_text(json.dumps(index), encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps({
        "held_group": st["holdout_group"], "rows": len(index), "checks": {"passed": True}, "version": 4,
        "anchored_modalities": ["CRISPRi"], "max_sources": 1, "sources": {"rule": "test", "groups": ["SRC"]},
        "commons": {"regime": "J", "keys_kept_out": 1},
        "outputs": {"anchors_npz": sha(folder / "anchors.npz"), "anchors_json": sha(folder / "anchors.json")}}),
        encoding="utf-8")


def load(path):
    import scipy.sparse as sp
    z = np.load(path, allow_pickle=False)
    return sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"])), z["labels"].astype(str)


class GenerationV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(11)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q[9] /= 3; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        for i in range(2):
            x = np.vstack([counts(rng, p, 120), counts(rng, q, 80), counts(rng, q, 80), counts(rng, q, 70)])
            t = ["NTC"] * 120 + ["G1"] * 80 + ["G2"] * 80 + ["G3"] * 70
            write_shard(sh / f"sk_{i}.h5ad", x, "sk", "K", f"K{i}", t, [f"K{i}_{j}-1" for j in range(len(t))],
                        "file://sk")
        write_shard(sh / "sq.h5ad", np.vstack([counts(rng, p, 100), counts(rng, q, 60), counts(rng, q, 60)]), "sq", "Q",
                    "Q1", ["NTC"] * 100 + ["G1"] * 60 + ["G4"] * 60, [f"Q{i}-1" for i in range(220)], "file://sq")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 120), counts(rng, q, 40), counts(rng, q, 40),
                                               counts(rng, q, 30)]), "sa", "La", "A1",
                    ["NTC"] * 120 + ["G1"] * 40 + ["G2"] * 40 + ["G4"] * 30, [f"A{i}-1" for i in range(230)],
                    "file://sa")
        keys = {s: key_in_fold(s, 0, want=(s == "G4")) for s in ("G1", "G2", "G3", "G4")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE"}}), encoding="utf-8")
        desc = d / "desc"
        desc.mkdir()
        np.save(desc / "descriptors.npy", rng.normal(size=(4, 3)).astype(np.float32))
        (desc / "genes.txt").write_text("G1\nG2\nG3\nG4\n", encoding="utf-8")
        run = lambda *args: subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)],
                                           capture_output=True, text=True)
        cls.pre = run("prepass", "--shards", sh, "--axis", d / "axis.csv", "--line-groups", d / "groups.json",
                      "--holdout-group", "LINE", "--hidden-fold", "0", "--target-keys", d / "keys.json",
                      "--pool-size", "48", "--ctrl-k", "16", "--input-genes", "16", "--eval-min-cells", "10",
                      "--min-controls-per-key", "20", "--out", d / "pre")
        assert cls.pre.returncode == 0, cls.pre.stderr[-3000:]
        cls.st = pickle.loads((d / "pre" / "prepass.pkl").read_bytes())
        write_anchors_v4(d / "anc" / "anchors_LINE_all", cls.st, np.random.default_rng(2))
        cls.tr = run("train", "--prepass", d / "pre", "--out", d / "kern" / "train", "--descriptors", desc,
                     "--anchors", d / "anc" / "anchors_LINE_all", "--arm", "ancorata=both", "--arm",
                     "ancorata_mean=both/mean", *TRAIN)
        assert cls.tr.returncode == 0, cls.tr.stderr[-3000:]
        groups = json.loads((d / "kern" / "train" / "eval_groups.json").read_text(encoding="utf-8"))
        cls.targets = [{"key": g["key"], "symbol": g["symbol"]} for g in groups if g["class"] == "C"]
        (d / "targets_LINE.json").write_text(json.dumps(cls.targets), encoding="utf-8")
        # the mock /kaggle/input of the generation kernel
        inp = d / "input"
        KG.stage_data(cls.mk(inp / "datasets" / OWNER / "gen-ds"), OWNER, "gen-ds", {"LINE": d / "targets_LINE.json"})
        shutil.copytree(desc, inp / "datasets" / OWNER / "code-ds")
        shutil.copytree(d / "kern", inp / "notebooks" / OWNER / "train-k")
        shutil.copytree(d / "pre", inp / "notebooks" / OWNER / "pre-k" / "prepass")
        shutil.copytree(d / "anc", inp / "notebooks" / OWNER / "anc-k")
        args = types.SimpleNamespace(owner=OWNER, held_group="LINE", arms=["ancorata", "ancorata_mean"], n=1500,
                                     extra=["--with-baseline"], code_slug="code-ds", train_kernel="train-k",
                                     prepass_kernel="pre-k", gen_slug="gen-ds", anchors_kernel="anc-k",
                                     anchors_dir="anchors_LINE_all")
        (d / "run.py").write_text(KG.kernel_text(args), encoding="utf-8")
        env = {**os.environ, "VCC_KAGGLE_INPUT": str(inp), "VCC_KAGGLE_OUT": str(cls.mk(d / "out"))}
        cls.gen = subprocess.run([sys.executable, str(d / "run.py")], capture_output=True, text=True, env=env)
        broken = d / "input_broken"
        shutil.copytree(inp, broken)
        (broken / "datasets" / OWNER / "gen-ds" / "balanced.py").unlink()            # a module left out
        env_b = {**env, "VCC_KAGGLE_INPUT": str(broken), "VCC_KAGGLE_OUT": str(cls.mk(d / "out_broken"))}
        cls.gen_broken = subprocess.run([sys.executable, str(d / "run.py")], capture_output=True, text=True, env=env_b)

    @staticmethod
    def mk(p: Path) -> Path:
        p.mkdir(parents=True)
        return p

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_kernel_runs_on_the_package(self):
        self.assertEqual(self.gen.returncode, 0, self.gen.stderr[-3000:])
        done = json.loads((self.d / "out" / "gen_done.json").read_text(encoding="utf-8"))
        for arm in ("ancorata", "ancorata_mean"):
            self.assertEqual(done[f"generate_{arm}"]["returncode"], 0)
            side = json.loads((self.d / "out" / f"cells_{arm}.json").read_text(encoding="utf-8"))
            self.assertTrue(all(b["anchored"] for b in side["blocks"]))
            self.assertEqual(side["cells"], 1500 * len(self.targets))
        self.assertEqual(sorted(KG.FILES), sorted(p.name for p in (self.d / "input" / "datasets" / OWNER / "gen-ds")
                                                  .glob("*.py")))

    def test_missing_module_fails(self):
        self.assertNotEqual(self.gen_broken.returncode, 0)

    def test_generated_cells_carry_the_exported_shift(self):
        groups = json.loads((self.d / "kern" / "train" / "eval_groups.json").read_text(encoding="utf-8"))
        gi = {(g["key"], g["symbol"]): i for i, g in enumerate(groups)}
        for arm in ("ancorata", "ancorata_mean"):
            with np.load(self.d / "kern" / "train" / arm / "eval_shifts.npz") as z:
                exported = z["predicted"].astype(np.float32)
            x, lab = load(self.d / "out" / f"cells_{arm}.npz")
            xb, labb = load(self.d / "out" / f"cells_{arm}_baseline.npz")
            np.testing.assert_array_equal(lab, labb)
            for t in self.targets:
                rows = np.flatnonzero(lab == t["symbol"])
                L = np.asarray(x[rows].sum(1)).ravel()
                Lb = np.asarray(xb[rows].sum(1)).ravel()
                mp = np.asarray(x[rows].multiply(1 / L[:, None]).mean(0)).ravel()
                mb = np.asarray(xb[rows].multiply(1 / Lb[:, None]).mean(0)).ravel()
                ok = (mp > 2e-3) & (mb > 2e-3)
                gen_shift = np.log(mp[ok]) - np.log(mb[ok])
                exp_shift = exported[gi[(t["key"], t["symbol"])]][ok]
                good = np.isfinite(exp_shift)
                r = np.corrcoef(gen_shift[good], exp_shift[good])[0, 1]
                self.assertGreater(r, 0.95, f"{arm} {t['symbol']}: r = {r:.3f}")
                self.assertLess(np.abs(gen_shift[good] - exp_shift[good]).mean(), 0.08)


if __name__ == "__main__":
    unittest.main()
