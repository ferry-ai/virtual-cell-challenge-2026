"""End-to-end check of banco_tipo.py on synthetic contract shards (run from this folder:
python -m unittest test_banco; needs cell_eval2 0.16.0 and the repo's src/ on the path).

Seven keys of five line types; every target has a response shared by its type plus a smaller one shared by all, so
the same-type arm must beat the cross-type arm and its own shuffled control on H1."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[2] / "src"
KEYS = [("replogle_k562_gwps", "K562", "myeloid"), ("hepg2_nadig", "HepG2", "hepatic"),
        ("jurkat_nadig", "Jurkat", "lymphoid_t"), ("h1_vcc2025", "H1", "pluripotent"),
        ("hipsci_targeted_19", "zapk_3", "pluripotent"), ("hipsci_targeted_19", "kolf_2", "pluripotent"),
        ("kolf_strong", "KOLF2.1J", "pluripotent"), ("rpe1_r2", "RPE1", "epithelial")]


def write_shards(root: Path, G=400, T=40, cells=90, ntc=400, seed=0):
    import anndata as ad

    rng = np.random.default_rng(seed)
    axis = np.array([f"G{i:04d}" for i in range(G)])
    pd.DataFrame({"gene_name": axis}).to_csv(root / "gene_names.csv", index=False)
    targets = axis[:T]
    base = rng.gamma(0.6, 2.0, size=G) + 0.05
    shared = {ty: rng.normal(0, 0.8, size=(T, G)) * (rng.random((T, G)) < 0.08)
              for ty in {k[2] for k in KEYS}}
    common = rng.normal(0, 0.4, size=(T, G)) * (rng.random((T, G)) < 0.04)
    for si, (study, ctx, ty) in enumerate(KEYS):
        line_base = base * rng.lognormal(0, 0.3, size=G)
        rows, labels = [], []
        for ti, t in enumerate(targets):
            lfc = shared[ty][ti] + common[ti]
            lfc[ti] = -2.0                                       # the knockdown itself
            mu = line_base * np.exp(lfc)
            rows.append(rng.poisson(mu[None, :] * rng.lognormal(0, 0.3, size=(cells, 1))))
            labels += [t] * cells
        rows.append(rng.poisson(line_base[None, :] * rng.lognormal(0, 0.3, size=(ntc, 1))))
        labels += ["NTC"] * ntc
        X = sp.csr_matrix(np.vstack(rows).astype(np.float32))
        n = X.shape[0]
        lab = np.array(labels)
        obs = pd.DataFrame({"study": study, "context": ctx, "target": lab, "modality": "CRISPRi",
                            "control_kind": np.where(lab == "NTC", "NTC", "none")},
                           index=[f"{study}|{ctx}|c{i}" for i in range(n)])
        native = np.arange(G)[::-1]                              # a native order that is not the axis order
        var = pd.DataFrame({"symbol": axis[native], "official_index": native, "measured": True, "mapping": "unique"},
                           index=[f"F{i}" for i in range(G)])
        a = ad.AnnData(X=X[:, native], obs=obs, var=var)
        d = root / "inputs" / study
        d.mkdir(parents=True, exist_ok=True)
        half = n // 2
        a[:half].copy().write_h5ad(d / f"{ctx}__shard_00000.h5ad")
        a[half:].copy().write_h5ad(d / f"{ctx}__shard_00001.h5ad")
    return axis


class EndToEnd(unittest.TestCase):
    def test_bench_runs_and_reads_the_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_shards(root)
            cmd = [sys.executable, str(HERE / "banco_tipo.py"), "--inputs", str(root / "inputs"),
                   "--axis", str(root / "gene_names.csv"), "--out", str(root / "out"), "--code", str(SRC),
                   "--lines", "h1", "kolf", "hepg2"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
            lett = json.loads((root / "out" / "lettura.json").read_text())
            src = json.loads((root / "out" / "sorgenti.json").read_text())
            self.assertFalse(src["keys"]["hipsci_targeted_19|kolf_2"]["group"] is None)
            h1 = lett["lines"]["h1"]
            self.assertTrue(h1["readable"], h1)
            comp = {(c["arm"], c["ref"]): c for c in h1["comparisons"]}
            self.assertGreater(comp[("same", "cross")]["mean"], 0)
            self.assertGreater(comp[("same", "same_shuf")]["mean"], 0)
            kolf = lett["lines"]["kolf"]
            self.assertIn("hipsci_targeted_19|kolf_2", kolf["excluded_keys"])
            self.assertIn("alloc", {c["arm"] for c in lett["lines"]["hepg2"]["comparisons"]})
            self.assertTrue((root / "out" / "effetti_hipsci.npz").exists())
            # the bootstrap's point estimate is the scorer's own aggregate, rescaled: it must match scaled_local.csv
            s = pd.read_csv(root / "out" / "bench_h1" / "scaled_local.csv", index_col=0, keep_default_na=False)
            for (arm, ref), c in comp.items():
                self.assertAlmostEqual(c["mean"], s.loc[arm, "avg"] - s.loc[ref, "avg"], places=6, msg=(arm, ref))
            print(json.dumps(lett["rule"], indent=1)[:2000])


if __name__ == "__main__":
    unittest.main()
