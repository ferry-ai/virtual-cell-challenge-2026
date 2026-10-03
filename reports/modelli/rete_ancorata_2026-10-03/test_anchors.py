"""The anchors on the real bench cube with a made-up prepass state whose answers are known (skipped when the cube is not
on this machine): each training row comes from the cell groups other than its own and the held-out one; the held-out
line's rows are lane A's 'transfer_cells' (the same function, sources and amplitude); hidden targets and T cells get no
row; a planted row with its own group among the sources fails the check; the held-out tables are never read for a fit.

    python -m unittest test_anchors -v            (from this folder, with the project venv)
"""
from __future__ import annotations

import json
import pickle
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "risposta_contesto_2026-10-02"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BENCH))
import anchors as A  # noqa: E402
from common import data_root  # noqa: E402

ROOT = data_root() / "processed" / "generalizzazione_contesti_2026-10-02"
CUBE = ROOT / "cube_r2"
PROTO = HERE.parent.parent / "analisi" / "generalizzazione_contesti_2026-10-02" / "PROTOCOLLO.json"
CLASSES = ["train", "C", "T", "J", "control_holdout", "combined:train", "combined:T", "combined:C", "combined:J",
           "unlabelled"]
KEYS = {"EWSR1": "ENSG00000182944", "TFAM": "ENSG00000108064", "TARDBP": "ENSG00000120948",
        "HSPA5": "ENSG00000044574", "TEAD3": "ENSG00000007866"}
SYMBOLS = list(KEYS)


def shard(key, tgt, cls):
    n = len(tgt)
    return {"key": np.full(n, key, np.int32), "tgt": np.array(tgt, np.int64),
            "cls": np.array([CLASSES.index(c) for c in cls], np.int8), "admitted": np.ones(n, bool),
            "control": np.array([t < 0 for t in tgt], bool)}


def fake_state(genes):
    return {"holdout_group": "HepG2", "genes": genes, "symbols": SYMBOLS, "hidden": ["TEAD3"], "classes": CLASSES,
            "key_names": ["k562_a", "rpe1_a", "jurkat_a", "hepg2_a"],
            "key_group": {"k562_a": "K562", "rpe1_a": "RPE1", "jurkat_a": "Jurkat", "hepg2_a": "HepG2"},
            "shards": [shard(0, [0, 1, -1, 4], ["train", "train", "train", "T"]),
                       shard(1, [0, 2, -1], ["train", "train", "train"]),
                       shard(2, [3, -1], ["train", "train"]),
                       shard(3, [0, 1, 2, 3, 4, -1], ["C", "C", "C", "C", "J", "control_holdout"])],
            "eval_groups": [{"class": "C", "key": "hepg2_a", "symbol": s} for s in SYMBOLS[:4]]
                           + [{"class": "J", "key": "hepg2_a", "symbol": "TEAD3"}]}


@unittest.skipUnless((CUBE / "manifest.json").is_file(), "bench cube not on this machine")
class Anchors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        arms, fitting, splits = A.bench(BENCH)
        P = json.loads(PROTO.read_text(encoding="utf-8"))["parameters"]
        cls.arms, cls.fitting = arms, fitting
        cls.cube = arms.Cube(CUBE, min_cells=P["min_cells"])

        class Sub(arms.Cube):
            def tables_of(self, group):
                return [t for t in super().tables_of(group) if t not in A.NOT_IN_CELL_CORPUS]

        cls.sub = Sub(CUBE, min_cells=P["min_cells"])
        cls.commons, _ = arms.table_means(cls.cube, splits.Split("C", "HepG2", None, P["n_folds"]))
        rng = np.random.default_rng(0)
        cls.genes = sorted(rng.choice(cls.cube.genes, 3000, replace=False).tolist())
        cls.st = fake_state(cls.genes)
        cls.R, cls.index, cls.U = A.compute(cls.st, cls.sub, cls.commons, KEYS, fitting.transfer_for,
                                            arms.AMPLITUDE_T25, fitting.basis, rank=4, log=lambda *_: None)

    def test_rows_and_sources(self):
        got = {(r["group"], r["symbol"]): r for r in self.index}
        self.assertEqual(set(got), {("K562", "EWSR1"), ("K562", "TFAM"), ("RPE1", "EWSR1"), ("RPE1", "TARDBP"),
                                    ("Jurkat", "HSPA5"), ("HepG2", "EWSR1"), ("HepG2", "TFAM"), ("HepG2", "TARDBP"),
                                    ("HepG2", "HSPA5")})
        for (g, _), r in got.items():
            self.assertNotIn(g, r["sources"])
            self.assertNotIn("HepG2", r["sources"])
            self.assertEqual(r["role"], "eval" if g == "HepG2" else "train")
        self.assertFalse(any(r["symbol"] == "TEAD3" for r in self.index))
        self.assertTrue(A.check(self.st, self.index)["passed"])

    def test_eval_rows_are_lane_a_transfer(self):
        srcs = [h for h in A.CELL_GROUPS if h != "HepG2" and h in self.sub.groups]
        keys = [KEYS[s] for s in SYMBOLS[:4]]
        s, _ = self.fitting.transfer_for(self.sub, keys, srcs, self.commons)
        cpos = {g: i for i, g in enumerate(self.cube.genes)}
        cols = np.array([cpos[g] for g in self.genes])
        for j, sym in enumerate(SYMBOLS[:4]):
            i = next(n for n, r in enumerate(self.index) if r["group"] == "HepG2" and r["symbol"] == sym)
            want = (s[j, cols] * self.arms.AMPLITUDE_T25).astype(np.float16)
            np.testing.assert_array_equal(np.isnan(self.R[i]), np.isnan(want))
            ok = ~np.isnan(want)
            np.testing.assert_allclose(self.R[i][ok].astype(np.float32), want[ok].astype(np.float32), rtol=1e-3,
                                       atol=1e-3)

    def test_projection(self):
        self.assertEqual(self.U.shape, (len(self.genes), 4))
        np.testing.assert_allclose(self.U.T @ self.U, np.eye(4), atol=1e-4)

    def test_planted_leak_fails(self):
        bad = self.index + [{"group": "K562", "symbol": "HSPA5", "target_key": KEYS["HSPA5"], "role": "train",
                             "sources": ["K562", "RPE1"], "support": 2}]
        self.assertFalse(A.check(self.st, bad)["passed"])
        hidden = self.index + [{"group": "RPE1", "symbol": "TEAD3", "target_key": KEYS["TEAD3"], "role": "train",
                                "sources": ["K562"], "support": 1}]
        self.assertFalse(A.check(self.st, hidden)["passed"])

    def test_script_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "pre").mkdir()
            with open(d / "pre" / "prepass.pkl", "wb") as fh:
                pickle.dump(self.st, fh, protocol=4)
            (d / "keys.json").write_text(json.dumps(KEYS), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(HERE / "anchors.py"), "--prepass", str(d / "pre"), "--cube",
                                   str(CUBE), "--protocol", str(PROTO), "--target-keys", str(d / "keys.json"),
                                   "--rank", "4", "--out", str(d / "out")], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr[-3000:])
            m = json.loads((d / "out" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m["rows"], 9)
            self.assertTrue(m["checks"]["passed"])
            self.assertEqual(m["dropped_tables"], ["k562_viperturb"])
            with np.load(d / "out" / "anchors.npz") as z:
                self.assertEqual(z["rows"].shape, (9, len(self.genes)))
                self.assertEqual(z["rows"].dtype, np.float16)


if __name__ == "__main__":
    unittest.main()
