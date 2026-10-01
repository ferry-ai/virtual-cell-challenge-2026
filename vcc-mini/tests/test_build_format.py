"""build_mini.py on fake files in the real formats, then one short training run on the result.

Bulk files mimic Replogle's raw_bulk: obs index `gene_transcript` ("<n>_<GENE>_<promoter>_<ENSG>"),
several non-targeting guide rows, num_cells_filtered, X = per-cell mean counts, var.gene_name.
Single-cell files mimic scPerturb: obs.perturbation with "control", integer counts, var.gene_name.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(0)
GENES = [f"G{i:03d}" for i in range(300)]
TARGETS = GENES[:60]


def fake_bulk(path, genes, targets):
    rows, idx, n = [], [], []
    base = rng.gamma(2.0, 1.0, len(genes))
    for k in range(4):                                   # control guides
        idx.append(f"{9000 + k}_non-targeting_non-targeting_non-targeting")
        rows.append(base * rng.uniform(0.95, 1.05, len(genes)))
        n.append(400)
    for j, t in enumerate(targets):
        for p in ("P1", "P2") if j % 7 == 0 else ("P1P2",):  # some genes have two transcripts
            eff = np.exp(rng.normal(0, 0.2, len(genes)))
            if t in genes:
                eff[genes.index(t)] = 0.3
            idx.append(f"{j}_{t}_{p}_ENSG{j:011d}")
            rows.append(base * eff)
            n.append(int(rng.integers(25, 200)))           # all above MIN_CELLS = 20
    obs = pd.DataFrame({"num_cells_filtered": n, "UMI_count_unfiltered": 1e4}, index=pd.Index(idx, name="gene_transcript"))
    var = pd.DataFrame({"gene_name": genes}, index=[f"ENSG{i:011d}" for i in range(len(genes))])
    ad.AnnData(np.array(rows, np.float32), obs=obs, var=var).write_h5ad(path)


def fake_singlecell(path, genes, targets):
    labels = ["control"] * 600 + [t for t in targets for _ in range(30)]
    base = rng.gamma(2.0, 1.0, len(genes))
    X = rng.poisson(np.tile(base, (len(labels), 1))).astype(np.float32)
    obs = pd.DataFrame({"perturbation": labels}, index=[f"c{i}" for i in range(len(labels))])
    var = pd.DataFrame({"gene_name": genes}, index=genes)
    ad.AnnData(X, obs=obs, var=var).write_h5ad(path)


class BuildFormat(unittest.TestCase):
    def test_build_then_train(self):
        sources = json.loads((ROOT / "sources.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            raw.mkdir()
            for e in sources:
                genes = GENES[:-5] if e["key"] == "Jurkat" else GENES        # panels differ a little
                (fake_bulk if e["key"] in ("K562_ess", "K562_gw", "RPE1") else fake_singlecell)(
                    raw / e["file"], genes, TARGETS)
                (raw / (e["file"] + ".verified.json")).write_text(json.dumps({"checksum": e["md5"]}))
            env = dict(os.environ, VCC_MINI_DATA=tmp)
            r = subprocess.run([sys.executable, str(ROOT / "build_mini.py")], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            mini = Path(tmp) / "mini"
            man = json.loads((mini / "manifest.json").read_text())
            self.assertEqual(man["n_genes"], 295)
            lines = pd.read_csv(mini / "lines.csv")
            self.assertTrue((lines.targets == 60).all(), lines)
            with np.load(mini / "effects_K562_gw.npz") as k:
                self.assertNotIn("non-targeting", set(k["targets"]))
                self.assertTrue(np.all(k["kd"] < -0.5), "the target gene must go down in its own knockdown")
            ess = [i for i in man["inputs"] if i["key"] == "K562_ess"][0]
            self.assertEqual(ess["control_rows"], 4)
            self.assertEqual(ess["label_source"], "obs index")
            r = subprocess.run([sys.executable, str(ROOT / "train.py"), "--data", str(mini), "--held", "HepG2",
                                "--out", str(Path(tmp) / "run"), "--epochs", "2", "--device", "cpu"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            res = json.loads((Path(tmp) / "run" / "results.json").read_text())
            self.assertIn("CT", res["results"]["HepG2"])


if __name__ == "__main__":
    unittest.main()
