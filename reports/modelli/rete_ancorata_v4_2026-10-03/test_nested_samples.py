"""nested_samples.py on synthetic shards with known libraries and guides.

- every admitted single-target perturbed cell gets a level, controls none; the levels are nested and each holds
  min(n, cap) cells of its group;
- the first cells cover the strata: a group with 3 libraries x 2 guides has all 6 strata at the smallest cap;
- inclusion probabilities are the share of the stratum kept, 1 for a group kept whole;
- a level that keeps the whole group has r = 1 against the full group; larger caps lose less; the split-half
  reliability is reported; the totals add up.

    python -m unittest test_nested_samples -v     (from this folder, with the project venv; a few minutes)
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
sys.path.insert(0, str(HERE))
from fixtures import GENES, counts, key_in_fold, make_twins  # noqa: E402

CAPS = [8, 16, 32]


def write_shard(path, x, study, context, library, targets, guides, barcodes, source):
    import anndata as ad
    import scipy.sparse as sp
    n = x.shape[0]
    library = np.broadcast_to(np.asarray(library, dtype=object), (n,))
    targets = np.asarray(targets, dtype=object)
    obs = pd.DataFrame({"study": study, "context": context, "library": library, "target": targets,
                        "control_kind": np.where(targets == "NTC", "NTC", "none"), "modality": "CRISPRi",
                        "barcode": barcodes, "guides": guides,
                        "cell_key": [f"{study}|{l}|{b}" for l, b in zip(library, barcodes)]},
                       index=[f"c{i}" for i in range(n)])
    var = pd.DataFrame({"symbol": GENES, "official_index": np.arange(len(GENES), dtype=np.int64),
                        "measured": np.ones(len(GENES), bool)}, index=[f"f{i}" for i in range(len(GENES))])
    ad.AnnData(X=sp.csr_matrix(x.astype(np.int32)), obs=obs, var=var,
               uns={"source": {"locator": source, "release": "test"}}).write_h5ad(path)


class Nested(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(3)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        q = p.copy(); q[5] *= 4; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        for i in range(3):                       # G1: 3 libraries x 2 guides, 30 cells per library; G2: 6 per library
            t = ["NTC"] * 60 + ["G1"] * 30 + ["G2"] * 6
            g = ["NTC"] * 60 + [f"G1_g{j % 2}" for j in range(30)] + [f"G2_g{j % 2}" for j in range(6)]
            write_shard(sh / f"sk_{i}.h5ad", np.vstack([counts(rng, p, 60), counts(rng, q, 36)]), "sk", "K",
                        f"K{i}", t, g, [f"K{i}_{j}-1" for j in range(96)], "file://sk")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 80), counts(rng, q, 30)]), "sa", "La", "A1",
                    ["NTC"] * 80 + ["G1"] * 30, ["NTC"] * 80 + ["G1_g0"] * 30, [f"A{i}-1" for i in range(110)],
                    "file://sa")
        keys = {s: key_in_fold(s, 0, want=False) for s in ("G1", "G2")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE"}}), encoding="utf-8")
        pre = subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), "prepass", "--shards", str(sh), "--axis",
                              str(d / "axis.csv"), "--line-groups", str(d / "groups.json"), "--holdout-group", "LINE",
                              "--hidden-fold", "0", "--target-keys", str(d / "keys.json"), "--pool-size", "48",
                              "--ctrl-k", "16", "--input-genes", "16", "--eval-min-cells", "10",
                              "--min-controls-per-key", "20", "--out", str(d / "pre")], capture_output=True, text=True)
        assert pre.returncode == 0, pre.stderr[-3000:]
        make_twins(sh, d / "twins")
        cls.proc = subprocess.run([sys.executable, str(HERE / "nested_samples.py"), "--prepass", str(d / "pre"),
                                  "--shard-roots", str(sh), "--fast-roots", str(d / "twins"), "--caps",
                                  *map(str, CAPS), "--out", str(d / "out"), "--workers", "1"],
                                 capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_run(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])

    def selection(self):
        out = {}
        for f in sorted((self.d / "out" / "selection").glob("*.npz")):
            with np.load(f) as z:
                out[f.name.replace(".npz", "")] = (z["level"], z["prob"].astype(np.float32))
        return out

    def test_levels_nested_and_sized(self):
        sel = self.selection()
        lv = np.concatenate([sel[f"sk_{i}.h5ad"][0][60:90] for i in range(3)])         # G1 in K: 90 cells
        for j, c in enumerate(CAPS):
            self.assertEqual(int(((lv >= 1) & (lv <= j + 1)).sum()), min(90, c))
        self.assertTrue(all((sel[f"sk_{i}.h5ad"][0][:60] == 0).all() for i in range(3)))   # controls not sampled
        g2 = np.concatenate([sel[f"sk_{i}.h5ad"][0][90:] for i in range(3)])            # G2: 18 cells
        self.assertEqual(int((g2 == 1).sum()), 8)
        self.assertEqual(int((g2 <= 2).sum()), 16)
        self.assertEqual(int((g2 <= 3).sum()), 18)

    def test_strata_covered_first(self):
        df = pd.read_csv(self.d / "out" / "groups.csv.gz")
        row = df[(df.key == "sk|K") & (df.target == "G1")].iloc[0]
        self.assertEqual(row["strata"], 6)
        self.assertEqual(row["strata_8"], 6)                  # 3 libraries x 2 guides all in the first 8 cells
        self.assertEqual(row["guides_8"], 2)

    def test_probabilities(self):
        sel = self.selection()
        pr = np.concatenate([sel[f"sk_{i}.h5ad"][1][60:90] for i in range(3)])
        np.testing.assert_allclose(pr[:, 0].sum(), 8, atol=1e-2)      # expected kept cells = cap
        g2 = np.concatenate([sel[f"sk_{i}.h5ad"][1][90:] for i in range(3)])
        np.testing.assert_allclose(g2[:, 2], 1.0)                      # 18 cells kept whole at 32

    def test_information_loss(self):
        df = pd.read_csv(self.d / "out" / "groups.csv.gz")
        whole = df[df.cells <= 32]
        self.assertTrue((whole["r_32"] > 0.9999).all())
        g1 = df[(df.key == "sk|K") & (df.target == "G1")].iloc[0]
        self.assertLessEqual(g1["r_8"], g1["r_32"] + 1e-9)
        self.assertTrue(df["r_halves"].notna().any())
        s = json.loads((self.d / "out" / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(s["totals"][str(8)], int(np.minimum(df.cells, 8).sum()))
        for col in ("r_spec_8", "sign_top_spec_32", "r_spec_halves", "targets_in_key"):
            self.assertIn(col, df.columns)
        self.assertTrue((whole["r_spec_32"].dropna() > 0.9999).all())


class SpecificShift(unittest.TestCase):
    """rows_of_key on hand-made accumulators: a sample that keeps the key's generic response and loses the target's own
    one still correlates with the full group on the total shift; the specific shift shows the loss."""

    def test_generic_response_removed(self):
        import nested_samples as NS
        rng = np.random.default_rng(0)
        genes, targets, caps = 400, 40, [2, 4, 8]
        mc = rng.dirichlet(np.ones(genes) * 5)
        generic = rng.normal(0, 1.0, genes)                           # common to every target of the key
        own = rng.normal(0, 0.2, (targets, genes))
        n_ctrl, n_full = 50, 40
        acc, n = {}, {}
        for t in range(targets):
            full = mc * np.exp(generic + own[t])
            lost = mc * np.exp(generic - own[t])                      # level 1 of target 0: its own shift inverted
            means = [full, lost if t == 0 else full, full, full, full, full]
            cells = [n_full, 2, 4, 8, n_full // 2, n_full // 2]
            acc[t] = np.stack([m * c for m, c in zip(means, cells)]).astype(np.float32)
            n.update({(t, i): c for i, c in enumerate(cells)})
        res = {"key": 0, "acc": acc, "n": n, "ctrl_sum": mc * n_ctrl, "ctrl_n": n_ctrl, "genes": genes}
        rows = NS.rows_of_key(res, caps, 1e-5)
        self.assertEqual(len(rows), targets)
        self.assertEqual(rows[0]["targets_in_key"], targets)
        self.assertGreater(rows[0]["levels"][0]["total"]["r"], 0.8)   # the generic part hides the loss
        self.assertLess(rows[0]["levels"][0]["spec"]["r"], -0.8)      # the specific shift shows it
        self.assertGreater(rows[0]["levels"][2]["spec"]["r"], 0.9999)
        self.assertGreater(rows[5]["levels"][0]["spec"]["r"], 0.9999)
        self.assertEqual(NS.rows_of_key({**res, "ctrl_n": 0}, caps, 1e-5), {})


if __name__ == "__main__":
    unittest.main()
