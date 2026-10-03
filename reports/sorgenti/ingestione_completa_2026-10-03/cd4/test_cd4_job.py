"""The CD4 job on a made-up file with known counts and labels: only the eligible rows are written, all of them; the
excluded ones are counted by reason; two parts make the file; a file without a required column is refused before any
count is read.

    python -m unittest test_cd4_job -v            (from this folder, with the project venv)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
N, G, BLOCK = 61, 9, 7


def fixture(root: Path):
    rng = np.random.default_rng(23)
    dense = rng.integers(0, 7, size=(N, G)).astype(np.float32)
    dense[rng.random(dense.shape) < 0.5] = 0
    group = np.array(["targeting single sgRNA"] * N, dtype=object)
    group[rng.random(N) < 0.2] = "no sgRNA"
    group[(rng.random(N) < 0.15) & (group == "targeting single sgRNA")] = "multi sgRNA"
    single = group == "targeting single sgRNA"
    control = single & (np.arange(N) % 6 == 0)
    gene = np.array([f"ENSG{i % 5:011d}" for i in range(N)], dtype=object)
    typ = np.where(group == "no sgRNA", None, np.where(control, "non-targeting", "targeting"))
    ids = np.where(~single, None, np.where(control, "NTC", gene))
    low = rng.random(N) < 0.15
    obs = pd.DataFrame({"low_quality": low, "guide_group": pd.Categorical(group), "guide_type": pd.Categorical(typ),
                        "perturbed_gene_id": pd.Categorical(ids),
                        "guide_id": pd.Categorical([f"g{i % 11}" for i in range(N)]),
                        "lane_id": pd.Categorical([f"lane{i % 3}" for i in range(N)]),
                        "total_counts": dense.sum(axis=1)}, index=[f"BC{i:04d}" for i in range(N)])
    var = pd.DataFrame({"gene_ids": [f"ENSG{i:011d}" for i in range(G)], "gene_name": [f"G{i}" for i in range(G)]},
                       index=[f"ENSG{i:011d}" for i in range(G)])
    ad.AnnData(X=sp.csr_matrix(dense), obs=obs, var=var).write_h5ad(root / "D1_Rest.assigned_guide.h5ad")
    (root / "axis.csv").write_text("gene\n" + "\n".join(f"G{i}" for i in range(G)) + "\n", encoding="utf-8")
    spec = json.loads((HERE / "specs/cd4_v1.json").read_text(encoding="utf-8"))
    spec["files"]["D1_Rest"].update(cells=N, genes=G)
    spec["unit"]["block"] = BLOCK
    (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    eligible = single & ~low
    return dense, eligible, control


def run(root: Path, name: str, *extra: str):
    return subprocess.run([sys.executable, str(HERE / "cd4_job.py"), "--spec", str(root / "spec.json"), "--file",
                           "D1_Rest", "--axis", str(root / "axis.csv"), "--stage", str(root / f"stage_{name}"), "--out",
                           str(root / f"out_{name}"), "--data-root", str(root), "--source",
                           str(root / "D1_Rest.assigned_guide.h5ad"), *extra], capture_output=True, text=True)


class Cd4(unittest.TestCase):
    def test_two_parts_hold_every_eligible_cell_and_count_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dense, eligible, control = fixture(root)
            rows, raw, excluded = [], 0, 0
            for i in range(2):
                r = run(root, f"p{i}", "--part", f"{i}/2", "--readahead", "4")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                out = root / f"out_p{i}"
                self.assertEqual(json.loads((out / "complete.json").read_text(encoding="utf-8"))["status"], "complete")
                m = json.loads((out / "cd4_D1_Rest" / "manifest.json").read_text(encoding="utf-8"))
                self.assertTrue(m["parity"]["ok"])
                self.assertEqual((m["donor"], m["condition"]), ("D1", "Rest"))
                raw += m["rows"]["raw"]
                excluded += m["rows"]["excluded"]
                for s in m["shards"]:
                    a = ad.read_h5ad(s["path"])
                    src = a.obs["source_row"].astype(int).to_numpy()
                    rows.extend(src.tolist())
                    self.assertTrue(np.array_equal(np.asarray(a.X.todense()), dense[src]))
                    self.assertTrue(((a.obs["control_kind"] == "NTC").to_numpy() == control[src]).all())
                    self.assertEqual(set(a.obs["context"]), {"CD4T D1 Rest"})
                    self.assertEqual(set(a.obs["modality"]), {"CRISPRi"})
            self.assertEqual(rows, np.flatnonzero(eligible).tolist())
            self.assertEqual((raw, excluded), (N, int((~eligible).sum())))

    def test_a_missing_column_is_refused_before_any_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture(root)
            with h5py.File(root / "D1_Rest.assigned_guide.h5ad", "r+") as f:
                del f["obs"]["lane_id"]
            r = run(root, "bad")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("precheck", r.stdout + r.stderr)
            self.assertFalse((root / "out_bad").exists())

    def test_smoke_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, eligible, _ = fixture(root)
            r = run(root, "smoke", "--max-cells", "20")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            done = json.loads((root / "out_smoke" / "complete.json").read_text(encoding="utf-8"))
            self.assertTrue(done["job_id"].endswith("_smoke"))
            self.assertEqual(done["units"]["cd4_D1_Rest"]["cells"], int(eligible[:20].sum()))


if __name__ == "__main__":
    unittest.main()
