"""Lane A on the real bench cube with a fake training output (skipped when the cube is not on this machine):
an oracle arm that predicts the cube's own truth must score PDS and cosine near 1, an arm of zeros must have no
cosine; the transfer baselines exist on C rows only; no baseline reads the held-out line for a fit.

    python -m unittest test_bench_effects -v      (from this folder, with the project venv; about a minute)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "risposta_contesto_2026-10-02"
sys.path.insert(0, str(BENCH))
from common import data_root  # noqa: E402

CUBE = data_root() / "processed" / "generalizzazione_contesti_2026-10-02" / "cube_r2"
PROTO = HERE.parent.parent / "analisi" / "generalizzazione_contesti_2026-10-02" / "PROTOCOLLO.json"


@unittest.skipUnless((CUBE / "manifest.json").is_file(), "bench cube not on this machine")
class LaneA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from arms import Cube
        cube = Cube(CUBE, min_cells=10)
        t = cube.tables_of("HepG2")[0]
        keys = cube.keys_of(t)[:150]
        sym = [cube.symbol[k] for k in keys]
        truth, _ = cube.get(t, "raw", keys, purpose="truth")
        cls.tmp = tempfile.TemporaryDirectory()
        run = Path(cls.tmp.name) / "run"
        (run / "oracle").mkdir(parents=True)
        (run / "zeros").mkdir()
        genes = cube.genes + ["NOT_IN_CUBE"]
        groups = [{"class": "C" if i < 120 else "J", "key": "s|HepG2", "symbol": s, "admitted_cells": 50,
                   "evaluated_cells": 50} for i, s in enumerate(sym)]
        groups.append({"class": "T", "key": "s|K562", "symbol": "XYZ", "admitted_cells": 50, "evaluated_cells": 50})
        (run / "eval_groups.json").write_text(json.dumps(groups), encoding="utf-8")
        G = len(genes)
        oracle = np.full((len(groups), G), np.nan, np.float16)
        oracle[:len(sym), :len(cube.genes)] = truth.astype(np.float16)
        np.savez_compressed(run / "eval_observed.npz", observed=oracle, genes=np.array(genes),
                            n_cells=np.full(len(groups), 50, np.int32))
        np.savez_compressed(run / "oracle" / "eval_shifts.npz", predicted=oracle)
        np.savez_compressed(run / "zeros" / "eval_shifts.npz", predicted=np.zeros((len(groups), G), np.float16))
        keys_json = Path(cls.tmp.name) / "keys.json"
        keys_json.write_text(json.dumps(dict(zip(sym, keys))), encoding="utf-8")
        cls.out = Path(cls.tmp.name) / "laneA"
        cls.proc = subprocess.run([sys.executable, str(HERE / "bench_effects.py"), "--run", str(run), "--cube", str(CUBE),
                                   "--protocol", str(PROTO), "--target-keys", str(keys_json), "--held-group", "HepG2",
                                   "--out", str(cls.out)], capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scores(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        df = pd.read_csv(self.out / "per_target_HepG2.csv.gz", keep_default_na=False, na_values=["", "nan", "NaN"])
        s = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(s["rows"], {"C": 120, "J": 30})
        o = df[df.arm == "oracle"]
        self.assertGreater(o["cos"].mean(), 0.99)
        self.assertGreater(o["pds"].mean(), 0.95)
        self.assertTrue(df[df.arm == "zeros"]["cos"].isna().all())
        for arm in ("transfer_cells", "transfer_all"):
            tr = df[df.arm == arm]
            self.assertTrue(tr[tr.cls == "J"]["cos"].isna().all())
            self.assertGreater(tr[tr.cls == "C"]["cos"].notna().mean(), 0.5)
        self.assertEqual(s["dropped_tables_for_cells"], ["k562_viperturb"])
        self.assertNotIn("CD4T", s["sources_cells"])
        self.assertIn("CD4T", s["sources_all"])


if __name__ == "__main__":
    unittest.main()
