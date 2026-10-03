"""Synthetic check of esporta_abc.py (run from this folder: python -m unittest test_esporta).

A trained run on the synthetic keys of test_rete, fake control files for two contexts and a target list with one
target no source covers: the files must load the way stage 45 reads them (`read_effects`), every target present,
the uncovered one at 0 and never observed."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import rete
from test_rete import synthetic_keys


class Esporta(unittest.TestCase):
    def test_contexts_in_the_stage45_layout(self):
        import anndata as ad
        import scipy.sparse as sp

        keys = synthetic_keys(seed=2)
        G = keys[0].basal.size
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            kd = tmp / "chiavi"
            kd.mkdir()
            for k in keys:
                np.savez_compressed(kd / (k.key.replace("|", "__") + ".npz"), targets=k.targets, eff=k.eff,
                                    basal=k.basal, measured=k.measured, n_cells=np.ones(len(k.targets)), key=k.key,
                                    group=k.group, type=k.type)
            cfg = rete.Config(panel=200, steps=40, eval_every=20, keep_steps=(0,), min_steps=40,
                              targets_per_episode=8, genes_per_episode=200)
            rete.train(rete.load_keys(kd), ["alpha0"], ["gamma0"], tmp / "run", cfg)
            genes = np.array([f"G{i:04d}" for i in range(G)])
            pd.DataFrame({0: genes}).to_csv(tmp / "axis.csv", header=False, index=False)
            rng = np.random.default_rng(0)
            for ctx in ("A", "B"):
                X = sp.csr_matrix(rng.poisson(1.0, (30, G)).astype(np.float32))
                order = rng.permutation(G)                   # controls need not follow the axis order
                ad.AnnData(X[:, order], var=pd.DataFrame(index=genes[order])).write_h5ad(tmp / f"context_{ctx}.h5ad")
            covered = [str(t) for t in keys[0].targets[:5]]
            pd.DataFrame({"target_gene": covered + ["NOT_A_TARGET"]}).to_csv(tmp / "pert_counts.csv", index=False)
            out = tmp / "eff"
            r = subprocess.run([sys.executable, "esporta_abc.py", "--keys", str(kd), "--run", str(tmp / "run"),
                                "--controls", str(tmp), "--contexts", "A", "B", "--targets-csv",
                                str(tmp / "pert_counts.csv"), "--axis", str(tmp / "axis.csv"), "--out", str(out)],
                               capture_output=True, text=True, cwd=Path(__file__).parent)
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = json.loads((out / "export_abc.json").read_text())
            split = json.loads((tmp / "run" / "split.json").read_text())
            self.assertEqual(rep["sources"], sorted(split["train"]))
            for ctx in ("A", "B"):
                c = rep["contexts"][ctx]
                self.assertEqual((c["targets_covered"], c["targets_fallback_zero"]), (5, 1))
                with np.load(out / f"effects_{ctx}.npz", allow_pickle=False) as z:   # as stage 45 reads it
                    gpos = pd.Index(z["genes"].astype(str)).get_indexer(pd.Index(genes))
                    self.assertFalse((gpos < 0).any())
                    rows = {t: i for i, t in enumerate(z["targets"].astype(str))}
                    self.assertEqual(set(rows), set(covered) | {"NOT_A_TARGET"})
                    lfc, obs = z["lfc"][:, gpos], z["observed"][:, gpos]
                    self.assertTrue(np.isfinite(lfc).all())
                    self.assertFalse(obs[rows["NOT_A_TARGET"]].any())
                    self.assertTrue((lfc[rows["NOT_A_TARGET"]] == 0).all())
                    self.assertGreater(obs[rows[covered[0]]].mean(), 0.5)
                    self.assertGreater(np.abs(lfc[rows[covered[0]]]).sum(), 0)
            self.assertTrue(any(out.glob("effects_A.npz")))
            r2 = subprocess.run([sys.executable, "esporta_abc.py", "--keys", str(kd), "--run", str(tmp / "run"),
                                 "--controls", str(tmp), "--contexts", "A", "--targets-csv", str(tmp / "pert_counts.csv"),
                                 "--axis", str(tmp / "axis.csv"), "--out", str(out)],
                                capture_output=True, text=True, cwd=Path(__file__).parent)
            self.assertNotEqual(r2.returncode, 0)                # never overwrites
            self.assertIn("already holds effects", r2.stderr)

    def test_basal_matches_dati(self):
        """The context's basal is the same formula dati.py applies to a key's pooled control counts."""
        import anndata as ad
        import esporta_abc

        rng = np.random.default_rng(1)
        X = rng.poisson(2.0, (20, 50)).astype(np.float32)
        genes = np.array([f"G{i}" for i in range(50)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "context_A.h5ad"
            ad.AnnData(X, var=pd.DataFrame(index=genes)).write_h5ad(path)
            L = esporta_abc.context_key(path, genes, "A")
        frac = X.sum(0).astype(np.float64)
        np.testing.assert_allclose(L.basal, np.log1p(1e4 * frac / frac.sum()), rtol=1e-6)


if __name__ == "__main__":
    unittest.main()
