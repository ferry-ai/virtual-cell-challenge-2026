"""build_sampled_shards.py on synthetic contract shards with known answers (DECISIONE.md §2).

- a group above the level keeps exactly `level` cells, a group below keeps all of them, every control is kept, the
  unassigned cells are dropped and counted;
- the levels are nested (the cells of level 32 are among those of level 64) and the strata alternate: with two
  libraries of equal size the first cells of a group split evenly;
- the selection does not depend on the order or the names under which the shards are found, nor on the counts;
- the kept rows are the source's counts bit for bit, with obs and var unchanged.

    python -m unittest test_build_sampled_shards -v
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
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "rete_ancorata_v4_2026-10-03"))
from fixtures import GENES, counts, write_shard  # noqa: E402

import build_sampled_shards as BS  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "build_sampled_shards.py"), *map(str, args)], capture_output=True,
                          text=True)


class Sampled(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(3)
        p = rng.dirichlet(np.ones(len(GENES)))
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        (d / "a").mkdir()
        # shard 1: G1 100 cells over two libraries, G2 20 cells, 30 controls, 5 unassigned
        t1 = ["NTC"] * 30 + ["G1"] * 100 + ["G2"] * 20 + ["UNASSIGNED"] * 5
        lib1 = ["L1"] * 30 + ["L1"] * 50 + ["L2"] * 50 + ["L1"] * 20 + ["L1"] * 5
        write_shard(d / "a" / "s1.h5ad", counts(rng, p, len(t1)), "st", "C1", np.array(lib1, dtype=object), t1,
                    [f"s1_{i}-1" for i in range(len(t1))], "file://s1")
        # shard 2: 60 more G1 cells (the group spans shards) and 10 controls
        t2 = ["NTC"] * 10 + ["G1"] * 60
        write_shard(d / "a" / "s2.h5ad", counts(rng, p, len(t2)), "st", "C1", "L2", t2,
                    [f"s2_{i}-1" for i in range(len(t2))], "file://s2")
        cls.r64 = run("--shard-roots", d / "a", "--out", d / "o64", "--level", "64", "--workers", "1")
        cls.r32 = run("--shard-roots", d / "a", "--out", d / "o32", "--level", "32", "--workers", "1")
        # the same shards under other names and folders, found in another order
        (d / "b" / "z").mkdir(parents=True)
        shutil.copy(d / "a" / "s1.h5ad", d / "b" / "z" / "x9.h5ad")
        shutil.copy(d / "a" / "s2.h5ad", d / "b" / "a0.h5ad")
        cls.rb = run("--shard-roots", d / "b", "--out", d / "ob", "--level", "64", "--workers", "1")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def manifest(self, name):
        return json.loads((self.d / name / "manifest.json").read_text(encoding="utf-8"))

    def kept(self, name, shard_out):
        import anndata as ad
        return ad.read_h5ad(self.d / name / shard_out)

    def test_runs(self):
        for r in (self.r64, self.r32, self.rb):
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])

    def test_caps_controls_and_drops(self):
        m = self.manifest("o64")
        g = {(x["study"], x["context"], x["target"]): x for x in m["groups_detail"]}
        self.assertEqual(g[("st", "C1", "G1")]["cells"], 160)
        self.assertEqual(g[("st", "C1", "G1")]["kept"]["64"], 64)
        self.assertEqual(g[("st", "C1", "G2")]["kept"]["64"], 20)
        self.assertEqual(m["totals"]["controls_kept"], 40)
        self.assertEqual(m["totals"]["perturbed_kept"], 84)
        self.assertEqual(m["totals"]["dropped_unlabelled_or_unassigned"], 5)
        a1, a2 = self.kept("o64", "s1__L64.h5ad"), self.kept("o64", "s2__L64.h5ad")
        tg = list(a1.obs["target"]) + list(a2.obs["target"])
        self.assertEqual(tg.count("G1"), 64)
        self.assertEqual(tg.count("NTC"), 40)
        self.assertNotIn("UNASSIGNED", tg)

    def test_nested_and_strata(self):
        k32 = set(self.kept("o32", "s1__L32.h5ad").obs["cell_key"]) | set(self.kept("o32", "s2__L32.h5ad").obs["cell_key"])
        k64 = set(self.kept("o64", "s1__L64.h5ad").obs["cell_key"]) | set(self.kept("o64", "s2__L64.h5ad").obs["cell_key"])
        self.assertTrue(k32 <= k64)
        obs = {n: BS.read_obs(self.d / "a" / f"{n}.h5ad") for n in ("s1", "s2")}
        level_of, _ = BS.plan(obs, [32, 64, 128], 2026)
        lib = np.concatenate([obs["s1"]["library"], obs["s2"]["library"]])
        lv = np.concatenate([level_of["s1"], level_of["s2"]])
        tgt = np.concatenate([obs["s1"]["target"], obs["s2"]["target"]])
        first = (tgt == "G1") & (lv == 32)
        self.assertEqual(int(first.sum()), 32)
        self.assertEqual(int((lib[first] == "L1").sum()), 16)           # two strata of (library, guides) alternate

    def test_independent_of_names_and_order(self):
        def keys(name):
            m = self.manifest(name)
            out = set()
            for r in m["shards"]:
                out |= set(self.kept(name, r["output"]).obs["cell_key"])
            return out
        self.assertEqual(keys("o64"), keys("ob"))

    def test_counts_bit_for_bit(self):
        import anndata as ad
        m = self.manifest("o64")
        self.assertEqual(m["reread_failures"], [])
        src = ad.read_h5ad(self.d / "a" / "s1.h5ad")
        out = self.kept("o64", "s1__L64.h5ad")
        pos = {k: i for i, k in enumerate(src.obs["cell_key"])}
        rows = [pos[k] for k in out.obs["cell_key"]]
        self.assertEqual((src.X[rows] != out.X).nnz, 0)
        self.assertEqual(list(out.var_names), list(src.var_names))
        self.assertEqual(out.uns["rows"]["level"], 64)
        self.assertEqual(out.uns["parity"]["kept_cells"], out.n_obs)


if __name__ == "__main__":
    unittest.main()
