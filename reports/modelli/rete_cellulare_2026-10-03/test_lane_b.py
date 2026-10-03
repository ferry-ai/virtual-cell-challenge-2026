"""Lane B plumbing on the local HepG2 cells with made-up network outputs (skipped when the cells or the cube are not on
this machine): the six members are computed for every arm (transfer through the generator, the network's shifts
through the generator, the network's own cells) next to the replicate and baseline anchors. It checks the wiring,
not any score.

    python -m unittest test_lane_b -v             (from this folder, with the project venv; several minutes)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
from common import data_root  # noqa: E402

ROOT = data_root() / "processed" / "generalizzazione_contesti_2026-10-02"
CUBE = ROOT / "cube_r2"
PROTO = HERE.parent.parent / "analisi" / "generalizzazione_contesti_2026-10-02" / "PROTOCOLLO.json"


@unittest.skipUnless((CUBE / "manifest.json").is_file() and (ROOT / "hepg2_r2" / "manifest.json").is_file(),
                     "cube or HepG2 cells not on this machine")
class LaneB(unittest.TestCase):
    def test_plumbing(self):
        import csv
        import h5py
        sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
        from common import h5_column
        rows = list(csv.DictReader(open(CUBE / "hepg2_nadig" / "rows.csv", encoding="utf-8")))
        rows = [r for r in rows if float(r["n_cells"]) >= 50][:8]
        hepg2 = Path(json.loads((ROOT / "hepg2_r2" / "manifest.json").read_text(encoding="utf-8"))["input"]["path"])
        with h5py.File(hepg2, "r") as f:
            native = h5_column(f["var/gene_name"]).astype(str)
        rng = np.random.default_rng(0)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run, cells = d / "run", d / "gen"
            for arm in ("cells", "mean", "generic"):
                (run / arm).mkdir(parents=True)
            cells.mkdir()
            targets = [{"key": "hepg2_nadig|HepG2", "symbol": r["target"], "target_key": r["target_key"],
                        "table": "hepg2_nadig", "cube_cells": float(r["n_cells"])} for r in rows]
            (d / "targets.json").write_text(json.dumps(targets), encoding="utf-8")
            groups = [{"class": "C", "key": t["key"], "symbol": t["symbol"], "admitted_cells": 60,
                       "evaluated_cells": 60} for t in targets]
            (run / "eval_groups.json").write_text(json.dumps(groups), encoding="utf-8")
            G = native.size
            np.savez_compressed(run / "eval_observed.npz", genes=native,
                                observed=np.zeros((len(groups), G), np.float16))
            for arm in ("cells", "mean", "generic"):
                np.savez_compressed(run / arm / "eval_shifts.npz",
                                    predicted=rng.normal(0, 0.05, (len(groups), G)).astype(np.float16))
                n = 32
                lab = np.repeat([t["symbol"] for t in targets], n)
                x = rng.poisson(0.3, (lab.size, G)).astype(np.float32)
                import scipy.sparse as sp
                m = sp.csr_matrix(x)
                np.savez_compressed(cells / f"cells_{arm}.npz", data=m.data, indices=m.indices, indptr=m.indptr,
                                    shape=np.array(m.shape), labels=lab, genes=native)
            proc = subprocess.run([sys.executable, str(HERE / "lane_b_hepg2.py"), "--targets", str(d / "targets.json"),
                                   "--cells-dir", str(cells), "--run", str(run), "--cube", str(CUBE), "--protocol",
                                   str(PROTO), "--out", str(d / "out"), "--max-controls", "512", "--cap-cells", "32"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr[-4000:])
            table = (d / "out" / "bench" / "scaled_local.csv").read_text(encoding="utf-8")
            for arm in ("replicate", "baseline", "transfer_cells", "transfer_all", "cells_shift", "mean_shift",
                        "generic_shift", "cells_cells", "mean_cells", "generic_cells"):
                self.assertIn(arm, table)
            # the same through lane_b.py, from real cells stored as extract_cells.py writes them
            import scipy.sparse as sp
            from six_member_hepg2 import read_rows
            with h5py.File(hepg2, "r") as f:
                cell_gene = h5_column(f["obs/gene"])
            pick, labs = [], []
            for t in targets:
                r = np.flatnonzero(cell_gene == t["symbol"])[:32]
                pick.append(r)
                labs += [t["symbol"]] * r.size
            c = np.flatnonzero(cell_gene == "non-targeting")[:512]
            rows_all = np.concatenate(pick + [c])
            labs += ["non-targeting"] * c.size
            order = np.argsort(rows_all)
            xr = read_rows(hepg2, rows_all[order])
            xr = xr[np.argsort(order)].tocsr()
            np.savez_compressed(cells / "real_cells.npz", data=xr.data, indices=xr.indices, indptr=xr.indptr,
                                shape=np.array(xr.shape), labels=np.array(labs), genes=native)
            proc = subprocess.run([sys.executable, str(HERE / "lane_b.py"), "--held-group", "HepG2", "--real",
                                   str(cells / "real_cells.npz"), "--targets", str(d / "targets.json"), "--cells-dir",
                                   str(cells), "--run", str(run), "--cube", str(CUBE), "--protocol", str(PROTO),
                                   "--out", str(d / "out_generic")], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr[-4000:])
            table = (d / "out_generic" / "bench" / "scaled_local.csv").read_text(encoding="utf-8")
            for arm in ("replicate", "transfer_cells", "cells_shift", "generic_cells"):
                self.assertIn(arm, table)


if __name__ == "__main__":
    unittest.main()
