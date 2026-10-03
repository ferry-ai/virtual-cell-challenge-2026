"""The KOLF job on a made-up CSC file with known counts: the parts of a file are disjoint, their union is the file, each
part ends complete on its own checks, and a part whose counts do not add up is refused.

    python -m unittest test_kolf_job -v           (from this folder, with the project venv)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kolf_job as kj  # noqa: E402

N, G, BLOCK = 53, 12, 7


def fixture(root: Path):
    rng = np.random.default_rng(17)
    dense = rng.integers(0, 9, size=(N, G)).astype(np.float32)
    dense[rng.random(dense.shape) < 0.6] = 0
    dense[11] = 0                                           # a cell without counts keeps its row
    obs = pd.DataFrame({"gene_target": pd.Categorical(["NTC" if i % 5 == 0 else f"G{i % 4}" for i in range(N)]),
                        "gene_target_ensembl_id": pd.Categorical(["NTC" if i % 5 == 0 else f"ENSG{i % 4:011d}" for i in range(N)]),
                        "gRNA": pd.Categorical([f"guide{i % 6}" for i in range(N)]),
                        "channel": pd.Categorical([f"ch{i % 3}" for i in range(N)])},
                       index=[f"BC{i:04d}-1" for i in range(N)])
    var = pd.DataFrame({"gene_ids": [f"ENSG{i:011d}" for i in range(G)]}, index=[f"G{i}" for i in range(G)])
    a = ad.AnnData(X=sp.csc_matrix(np.log1p(dense)), obs=obs, var=var)
    a.layers["counts"] = sp.csc_matrix(dense)
    a.write_h5ad(root / "kolf.h5ad")
    (root / "axis.csv").write_text("gene\n" + "\n".join(f"G{i}" for i in range(G)) + "\n", encoding="utf-8")
    spec = json.loads((HERE / "specs/kolf_pan_v1.json").read_text(encoding="utf-8"))
    spec["source"].update(cells=N, genes=G)
    spec["unit"]["block"] = BLOCK
    spec["unit"]["kwargs"].update(column_chunk=5, min_free_bytes=0)
    (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    return dense


def run(root: Path, name: str, *extra: str):
    return subprocess.run([sys.executable, str(HERE / "kolf_job.py"), "--spec", str(root / "spec.json"), "--axis",
                           str(root / "axis.csv"), "--stage", str(root / f"stage_{name}"), "--out",
                           str(root / f"out_{name}"), "--data-root", str(root), "--source", str(root / "kolf.h5ad"),
                           *extra], capture_output=True, text=True)


class Parts(unittest.TestCase):
    def test_ranges_are_disjoint_and_cover(self):
        for n_cells, block, n in ((2659209, 20000, 2), (2659209, 20000, 3), (53, 7, 4), (20000, 20000, 1)):
            cuts = [kj.part_range(n_cells, block, f"{i}/{n}") for i in range(n)]
            self.assertEqual(cuts[0][0], 0)
            self.assertEqual(cuts[-1][1], n_cells)
            self.assertTrue(all(a[1] == b[0] for a, b in zip(cuts, cuts[1:])))
            self.assertTrue(all(lo % block == 0 for lo, _ in cuts))
        self.assertEqual(kj.part_range(53, 7, None), (0, 53))
        with self.assertRaises(ValueError):
            kj.part_range(53, 7, "2/2")
        with self.assertRaises(ValueError):
            kj.part_range(7, 7, "0/2")

    def test_two_parts_make_the_file_and_each_is_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dense = fixture(root)
            rows, total, names = [], 0, []
            for i in range(2):
                r = run(root, f"p{i}", "--part", f"{i}/2")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                out = root / f"out_p{i}"
                done = json.loads((out / "complete.json").read_text(encoding="utf-8"))
                self.assertEqual(done["status"], "complete")
                self.assertFalse((out / "parity_failed.json").exists())
                m = json.loads((out / "kolf_pan_genome" / "manifest.json").read_text(encoding="utf-8"))
                self.assertTrue(m["parity"]["ok"])
                self.assertEqual(m["part"], f"{i}/2")
                listed = json.loads((out / "verify_manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(len(listed["files"]), m["totals"]["shards"])
                for s in m["shards"]:
                    a = ad.read_h5ad(s["path"])
                    names.append(s["shard"])
                    rows.extend(a.obs["source_row"].astype(int).tolist())
                    total += int(a.X.sum())
                    got = np.asarray(a.X.todense())
                    self.assertTrue(np.array_equal(got, dense[a.obs["source_row"].astype(int).to_numpy()]))
                    self.assertEqual(set(a.obs.loc[a.obs["control_kind"] == "NTC", "target"]) - {"NTC"}, set())
                    self.assertEqual(a.uns["writer"]["script"], "kolf_job.py")
            self.assertEqual(rows, list(range(N)))
            self.assertEqual(total, int(dense.sum()))
            self.assertEqual(len(names), len(set(names)))
            whole = run(root, "all")
            self.assertEqual(whole.returncode, 0, whole.stdout + whole.stderr)
            m = json.loads((root / "out_all" / "kolf_pan_genome" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(s["shard"] for s in m["shards"]), sorted(names))

    def test_smoke_is_named_and_wrong_size_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture(root)
            r = run(root, "smoke", "--max-cells", "10")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            done = json.loads((root / "out_smoke" / "complete.json").read_text(encoding="utf-8"))
            self.assertTrue(done["job_id"].endswith("_smoke"))
            self.assertEqual(done["units"]["kolf_pan_genome"]["cells"], 10)
            spec = json.loads((root / "spec.json").read_text(encoding="utf-8"))
            spec["source"]["cells"] = N + 1
            (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
            r = run(root, "wrong")
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((root / "out_wrong" / "complete.json").exists())

    def test_a_wrong_column_is_refused_before_the_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture(root)
            spec = json.loads((root / "spec.json").read_text(encoding="utf-8"))
            for key, bad in (("guides_col", "no_such_column"), ("layer", "X")):
                changed = json.loads(json.dumps(spec))
                changed["unit"]["kwargs"][key] = bad
                if key == "layer":                                  # the shape of the layer is checked too
                    changed["source"]["cells"] = N + 2
                (root / "spec.json").write_text(json.dumps(changed), encoding="utf-8")
                r = run(root, f"bad_{key}")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("precheck", r.stdout + r.stderr)
                self.assertFalse((root / f"stage_bad_{key}").exists())
                self.assertFalse((root / f"out_bad_{key}").exists())


if __name__ == "__main__":
    unittest.main()
