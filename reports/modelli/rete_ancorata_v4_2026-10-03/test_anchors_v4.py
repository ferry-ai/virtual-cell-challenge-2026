"""Version 4 anchors (anchors.py) on a synthetic bench cube written in the cube's own format, with known answers.

Cube: K562 (tables k562_gwps, k562_viperturb), RPE1, CD4T (cd4_rest), HCT116 and the held-out HepG2; targets SEEN and
SEEN2 (hash fold 1-4) and HIDDEN (fold 0, hidden by the prepass state). A made-up prepass state trains SEEN and SEEN2 in
K562 and RPE1 and evaluates SEEN in HepG2.
- invariance (Codex's P1 of 3/10, as a test): multiplying HIDDEN's responses by 100 in every source table changes no
  anchor and no projection; version 3's regime-C means would change them;
- positive control: changing SEEN2's responses in one source table changes SEEN2's anchors;
- the source rules: 'cells' drops CD4T, HCT116 and the VIPerturb table, 'all' keeps every table, 'production' keeps
  k562_gwps, CD4T and HCT116 only; max_sources and the support follow the rule;
- the checks refuse a row of a hidden key, and a state without a hidden fold.

    python -m unittest test_anchors_v4 -v         (from this folder, with the project venv; seconds)
"""
from __future__ import annotations

import json
import pickle
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "risposta_contesto_2026-10-02"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BENCH))
import anchors as A  # noqa: E402
import arms as ARMS  # noqa: E402
import splits as SPLITS  # noqa: E402

CLASSES = ["train", "C", "T", "J", "control_holdout", "combined:train", "combined:T", "combined:C", "combined:J",
           "unlabelled"]
GENES = [f"g{i}" for i in range(12)]
TABLES = {"k562_gwps": "K562", "k562_viperturb": "K562", "rpe1": "RPE1", "cd4_rest": "CD4T", "hct116": "HCT116",
          "hepg2_nadig": "HepG2"}


def key_with_fold(prefix, want_zero):
    for i in range(1000):
        k = f"ENSG{prefix}{i:05d}"
        if (SPLITS.target_fold(k, 5) == 0) == want_zero:
            return k
    raise AssertionError


KEYS = {"SEEN": key_with_fold("1", False), "SEEN2": key_with_fold("2", False), "HIDDEN": key_with_fold("3", True)}


def write_cube(folder: Path, rng, scale_hidden=1.0, bump_seen2=None):
    folder.mkdir(parents=True)
    pd.DataFrame({"gene": GENES}).to_csv(folder / "genes.csv", index=False)
    meta, basal = {}, {}
    for t, g in TABLES.items():
        (folder / t).mkdir()
        syms = ["SEEN", "SEEN2", "HIDDEN"]
        pd.DataFrame({"target_key": [KEYS[s] for s in syms], "target": syms, "n_cells": [80, 60, 70],
                      "duplicate_of_key": [False] * 3}).to_csv(folder / t / "rows.csv", index=False)
        tr = np.random.default_rng(sum(map(ord, t)))
        raw = tr.normal(0, 0.5, (3, len(GENES))).astype(np.float32)
        raw[2] *= scale_hidden
        if bump_seen2 == t:
            raw[1] += 3.0
        np.save(folder / t / "raw.npy", raw.astype(np.float16))
        np.save(folder / t / "shrunk.npy", (raw * 0.8).astype(np.float16))
        np.save(folder / t / "se.npy", np.full_like(raw, 0.1).astype(np.float16))
        meta[t] = {"rows": 3, "group": g}
        basal[t] = rng.normal(2, 1, len(GENES)).astype(np.float32)
    np.savez(folder / "basal.npz", **basal)
    (folder / "manifest.json").write_text(json.dumps({"tables": meta}), encoding="utf-8")


def shard(key, tgt, cls):
    n = len(tgt)
    return {"key": np.full(n, key, np.int32), "tgt": np.array(tgt, np.int64), "admitted": np.ones(n, bool),
            "cls": np.array([CLASSES.index(c) for c in cls], np.int8), "control": np.array([t < 0 for t in tgt], bool),
            "mod": np.zeros(n, np.int32)}


def state(hidden_fold="0"):
    syms = ["HIDDEN", "SEEN", "SEEN2"]
    return {"holdout_group": "HepG2", "genes": GENES, "symbols": syms, "hidden": ["HIDDEN"], "classes": CLASSES,
            "modalities": ["CRISPRi"], "key_names": ["k562", "rpe1", "hepg2"],
            "key_group": {"k562": "K562", "rpe1": "RPE1", "hepg2": "HepG2"},
            "args": {"hidden_fold": hidden_fold, "n_folds": "5"},
            "shards": [shard(0, [1, 2, 0, -1], ["train", "train", "T", "train"]),
                       shard(1, [1, 2, -1], ["train", "train", "train"]),
                       shard(2, [1, 0, -1], ["C", "J", "control_holdout"])],
            "eval_groups": [{"class": "C", "key": "hepg2", "symbol": "SEEN"},
                            {"class": "J", "key": "hepg2", "symbol": "HIDDEN"}]}


def run(d: Path, cube: Path, sources: str, out: str, st=None):
    pre = d / f"pre_{out}"
    pre.mkdir()
    with open(pre / "prepass.pkl", "wb") as fh:
        pickle.dump(st or state(), fh, protocol=4)
    proc = subprocess.run([sys.executable, str(HERE / "anchors.py"), "--prepass", str(pre), "--cube", str(cube),
                           "--protocol", str(d / "proto.json"), "--target-keys", str(d / "keys.json"),
                           "--sources", sources, "--rank", "2", "--bench-code", str(BENCH), "--out", str(d / out)],
                          capture_output=True, text=True)
    return proc


def load(d: Path, out: str):
    with np.load(d / out / "anchors.npz") as z:
        rows, U = z["rows"].astype(np.float32), z["U"]
    index = json.loads((d / out / "anchors.json").read_text(encoding="utf-8"))
    manifest = json.loads((d / out / "manifest.json").read_text(encoding="utf-8"))
    return rows, U, index, manifest


class AnchorsV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        (d / "proto.json").write_text(json.dumps({"parameters": {"min_cells": 10, "n_folds": 5}}), encoding="utf-8")
        (d / "keys.json").write_text(json.dumps(KEYS), encoding="utf-8")
        write_cube(d / "cube", np.random.default_rng(0))
        write_cube(d / "cube_hidden100", np.random.default_rng(0), scale_hidden=100.0)
        write_cube(d / "cube_seen2", np.random.default_rng(0), bump_seen2="rpe1")
        cls.procs = {name: run(d, d / cube, src, name) for name, cube, src in (
            ("all", "cube", "all"), ("all_h100", "cube_hidden100", "all"), ("all_s2", "cube_seen2", "all"),
            ("cells", "cube", "cells"), ("cells_h100", "cube_hidden100", "cells"), ("prod", "cube", "production"))}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_runs(self):
        for name, proc in self.procs.items():
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr[-3000:]}")

    def test_hidden_responses_change_nothing(self):
        for a, b in (("all", "all_h100"), ("cells", "cells_h100")):
            ra, ua, ia, ma = load(self.d, a)
            rb, ub, ib, mb = load(self.d, b)
            self.assertEqual(ia, ib)
            np.testing.assert_array_equal(np.isnan(ra), np.isnan(rb))
            np.testing.assert_array_equal(np.nan_to_num(ra), np.nan_to_num(rb))
            np.testing.assert_array_equal(ua, ub)
            self.assertEqual(ma["commons"]["regime"], "J")
            self.assertGreaterEqual(ma["commons"]["keys_kept_out"], 1)

    def test_regime_c_means_would_leak(self):
        """The version 3 means (regime C) move with the hidden responses: what version 4 removes."""
        c0 = ARMS.table_means(ARMS.Cube(self.d / "cube"), SPLITS.Split("C", "HepG2", None, 5))[0]
        c1 = ARMS.table_means(ARMS.Cube(self.d / "cube_hidden100"), SPLITS.Split("C", "HepG2", None, 5))[0]
        self.assertGreater(max(np.abs(c0[t] - c1[t]).max() for t in c0), 1.0)

    def test_positive_control(self):
        ra, _, ia, _ = load(self.d, "all")
        rb, _, ib, _ = load(self.d, "all_s2")
        moved = [i for i, r in enumerate(ia) if r["symbol"] == "SEEN2" and "RPE1" in r["sources"]]
        self.assertTrue(moved)
        self.assertGreater(np.nanmax(np.abs(ra[moved] - rb[moved])), 0.5)

    def test_source_rules(self):
        _, _, ia, ma = load(self.d, "all")
        _, _, ic, mc = load(self.d, "cells")
        _, _, ip, mp = load(self.d, "prod")
        self.assertEqual(ma["sources"]["groups"], ["CD4T", "HCT116", "K562", "RPE1"])
        self.assertEqual(mc["sources"]["groups"], ["K562", "RPE1"])
        self.assertIn("k562_viperturb", mc["sources"]["dropped_tables"])
        self.assertEqual(sorted(mp["sources"]["tables"]), ["cd4_rest", "hct116", "k562_gwps"])
        self.assertEqual((ma["max_sources"], mc["max_sources"], mp["max_sources"]), (4, 2, 3))
        ev = next(r for r in ia if r["role"] == "eval")
        self.assertEqual(ev["support"], 4)
        tr = next(r for r in ia if r["group"] == "K562")
        self.assertNotIn("K562", tr["sources"])
        self.assertFalse(any(r["symbol"] == "HIDDEN" for r in ia + ic + ip))
        for idx in (ia, ic, ip):
            self.assertTrue(A.check(state(), idx)["passed"])

    def test_refusals(self):
        _, _, ia, _ = load(self.d, "all")
        bad = ia + [{"group": "RPE1", "symbol": "X", "target_key": KEYS["HIDDEN"], "role": "train",
                     "sources": ["K562"], "support": 1}]
        self.assertFalse(A.check(state(), bad, forbidden={KEYS["HIDDEN"]})["passed"])
        proc = run(self.d, self.d / "cube", "all", "no_fold", st=state(hidden_fold="None"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no hidden fold", proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
