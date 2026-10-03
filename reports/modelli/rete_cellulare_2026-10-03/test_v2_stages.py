"""End to end on synthetic contract shards, version 2 of train_cellnet.py (the corrections of the audit of 1/10).

Corpus, each part with a known answer:
- line group LINE: contexts La (study sa) and Lb (study sb), held out together (--holdout-group LINE);
- kept: study sk, context K, three libraries with 200, 70 and 5 controls; study sq, context Q; study sr, context R,
  with 10 controls only: QC drops the key, and G5, perturbed among kept contexts only in R, is never trained;
- G4 is in the hidden hash fold (--hidden-fold 0 with a key chosen for it).
Expected: G5 in the held-out line is J after QC (C before: the G2 counterexample of the audit); G4 is J there and T in
Q; the reservoir keeps min(n, ctrl_k) per library and no perturbed cell; library L3 (5 controls) draws from its key;
the loss coefficients of the two active groups are equal; the generic arm trains its unknown row; the three arms export
their shifts for every held-out group.

    python -m unittest test_v2_stages -v          (from this folder, with the project venv; a few minutes)
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
sys.path.insert(0, str(HERE))
import cell_data as CD  # noqa: E402
from test_prepass import GENES, counts  # noqa: E402


def write_shard(path, x, study, context, library, targets, barcodes, source):
    """test_prepass.write_shard with one library per cell (a string, or an array of them)."""
    import anndata as ad
    import pandas as pd
    import scipy.sparse as sp
    n = x.shape[0]
    library = np.broadcast_to(np.asarray(library, dtype=object), (n,))
    targets = np.asarray(targets, dtype=object)
    control = np.where(targets == "NTC", "NTC", "none")
    obs = pd.DataFrame({"study": study, "context": context, "library": library, "target": targets,
                        "control_kind": control, "modality": "CRISPRi", "barcode": barcodes,
                        "cell_key": [f"{study}|{l}|{b}" for l, b in zip(library, barcodes)]},
                       index=[f"c{i}" for i in range(n)])
    var = pd.DataFrame({"symbol": GENES, "official_index": np.arange(len(GENES), dtype=np.int64),
                        "measured": np.ones(len(GENES), bool)}, index=[f"f{i}" for i in range(len(GENES))])
    ad.AnnData(X=sp.csr_matrix(x.astype(np.int32)), obs=obs, var=var,
               uns={"source": {"locator": source, "release": "test"}}).write_h5ad(path)

TRAIN = ["--epochs", "2", "--batch", "32", "--ctrl-k", "32", "--buffer-shards", "2", "--dim", "8", "--rank", "4",
         "--device", "cpu", "--measure-from", "2", "--measure-steps", "3", "--log-every", "5",
         "--reserve-export-minutes", "0.05", "--eval-reserve-seconds", "5"]


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)], capture_output=True, text=True)


def key_in_fold(symbol, fold, want=True):
    for i in range(10000):
        k = f"KEY_{symbol}_{i}"
        if (CD.target_fold(k, 5) == fold) == want:
            return k
    raise AssertionError


class StagesV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(5)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q /= q.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        # kept K: libraries L1 (200 controls), L2 (70), L3 (5); G1, G2, G3 in every library
        x, t, lib = [], [], []
        for L, nc in (("L1", 200), ("L2", 70), ("L3", 5)):
            x += [counts(rng, p, nc), counts(rng, q, 40), counts(rng, q, 35), counts(rng, q, 30)]
            t += ["NTC"] * nc + ["G1"] * 40 + ["G2"] * 35 + ["G3"] * 30
            lib += [L] * (nc + 105)
        xk = np.vstack(x)
        write_shard(sh / "sk.h5ad", xk, "sk", "K", np.array(lib), t, [f"K{i}-1" for i in range(len(t))], "file://sk")
        write_shard(sh / "sq.h5ad", np.vstack([counts(rng, p, 150), counts(rng, q, 60), counts(rng, q, 60)]), "sq", "Q",
                    "Q1", ["NTC"] * 150 + ["G1"] * 60 + ["G4"] * 60, [f"Q{i}-1" for i in range(270)], "file://sq")
        write_shard(sh / "sr.h5ad", np.vstack([counts(rng, p, 10), counts(rng, q, 60)]), "sr", "R", "R1",
                    ["NTC"] * 10 + ["G5"] * 60, [f"R{i}-1" for i in range(70)], "file://sr")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 150), counts(rng, q, 50), counts(rng, q, 50),
                                               counts(rng, q, 40)]), "sa", "La", "A1",
                    ["NTC"] * 150 + ["G1"] * 50 + ["G5"] * 50 + ["G4"] * 40, [f"A{i}-1" for i in range(290)], "file://sa")
        write_shard(sh / "sb.h5ad", np.vstack([counts(rng, p, 100), counts(rng, q, 40), counts(rng, q, 40)]), "sb", "Lb",
                    "B1", ["NTC"] * 100 + ["G2"] * 40 + ["G3"] * 40, [f"B{i}-1" for i in range(180)], "file://sb")
        keys = {s: key_in_fold(s, 0, want=(s == "G4")) for s in ("G1", "G2", "G3", "G4", "G5")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE", "Lb": "LINE"}}), encoding="utf-8")
        common = ["--shards", sh, "--axis", d / "axis.csv", "--line-groups", d / "groups.json", "--holdout-group", "LINE",
                  "--hidden-fold", "0", "--target-keys", d / "keys.json", "--pool-size", "64", "--ctrl-k", "32",
                  "--input-genes", "16", "--eval-min-cells", "10", "--min-controls-per-key", "20"]
        cls.pre = run("prepass", *common, "--out", d / "pre")
        cls.pre_w2 = run("prepass", *common, "--out", d / "pre_w2", "--workers", "2")
        cls.tr = run("train", "--prepass", d / "pre", "--out", d / "run", "--arm", "d=identity", "--arm", "g=generic",
                     "--arm", "m=identity/mean", "--roles", "2", *TRAIN)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, *parts):
        return json.loads((self.d.joinpath(*parts)).read_text(encoding="utf-8"))

    def test_stages_finished(self):
        for name in ("pre", "pre_w2", "tr"):
            proc = getattr(self, name)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr[-3000:]}")

    def test_whole_line_held_out(self):
        s = self.read("pre", "splits.json")
        self.assertEqual(s["held_keys"], ["sa|La", "sb|Lb"])
        self.assertEqual(s["line_groups"]["LINE"], ["sa|La", "sb|Lb"])
        self.assertEqual(s["hidden_symbols"], ["G4"])

    def test_classes_after_qc(self):
        s = self.read("pre", "splits.json")
        self.assertEqual(s["roles_after_qc"]["cells_whose_class_changed"], {"C->J": 50})   # G5 in La
        st = pickle.loads((self.d / "pre" / "prepass.pkl").read_bytes())
        cls = {(g["class"], g["key"], g["symbol"]) for g in st["eval_groups"]}
        self.assertIn(("J", "sa|La", "G5"), cls)
        self.assertIn(("J", "sa|La", "G4"), cls)
        self.assertIn(("T", "sq|Q", "G4"), cls)
        self.assertIn(("C", "sa|La", "G1"), cls)
        self.assertIn(("C", "sb|Lb", "G2"), cls)
        self.assertNotIn(("C", "sa|La", "G5"), cls)

    def test_reservoir(self):
        qc = self.read("pre", "qc.json")["reservoir"]["by_key"]["sk|K"]
        self.assertEqual((qc["libraries"], qc["controls"], qc["kept"]), (3, 275, 69))
        self.assertEqual(qc["libraries_with_ctrl_k_kept"], 2)
        self.assertAlmostEqual(qc["perturbed_cells_by_draw"]["key_pool"], 105 / 315, places=4)
        st = pickle.loads((self.d / "pre" / "prepass.pkl").read_bytes())
        self.assertEqual(st["pool_key"].size, st["pool_x"].shape[0])
        self.assertEqual(st["pool_key"].size, sum(v["kept"] for v in
                                                  self.read("pre", "qc.json")["reservoir"]["by_key"].values()))
        two = pickle.loads((self.d / "pre_w2" / "prepass.pkl").read_bytes())
        for f in ("pool_x", "pool_lib", "pool_sid", "pool_libc", "pool_key", "input_genes", "key_weights"):
            self.assertTrue(np.array_equal(st[f], two[f]), f)

    def test_loss_shares_and_draws(self):
        cov = self.read("run", "coverage.json")
        self.assertTrue(cov["leakage_check"]["passed"])
        shares = cov["loss_shares"]["by_group"]
        self.assertEqual(set(shares), {"K", "Q"})                 # R lost its key in QC, LINE is held out
        self.assertAlmostEqual(shares["K"], 0.5, delta=0.03)
        draws = cov["control_draws"]["by_key"]["sk|K"]
        self.assertGreater(draws.get("key_pool", 0), 0)           # the cells of L3
        self.assertGreater(draws.get("own_library", 0), draws.get("key_pool", 0))

    def test_generic_arm_learns_its_unknown_row(self):
        import torch
        sys.path.insert(0, str(HERE))
        import cellnet as CN
        st = pickle.loads((self.d / "pre" / "prepass.pkl").read_bytes())
        n_sym = len(st["symbols"])
        torch.manual_seed(0)
        init = CN.build_model(st["G"], n_sym, len(st["modalities"]), len(st["studies"]), st["input_genes"], dim=8,
                              rank=4, target_code="generic").state_dict()["target_emb.weight"][n_sym]
        moved = {}
        for arm in ("g", "d"):
            m = torch.load(self.d / "run" / arm / "model.pt", weights_only=False)
            moved[arm] = float((m["state"]["target_emb.weight"][n_sym] - init).abs().max())
        self.assertGreater(moved["g"], 10 * moved["d"] + 1e-6)    # identity: only weight decay touches it
        self.assertEqual(torch.load(self.d / "run" / "m" / "model.pt", weights_only=False)["context_mode"], "mean")

    def test_exports(self):
        groups = self.read("run", "eval_groups.json")
        obs = np.load(self.d / "run" / "eval_observed.npz", allow_pickle=False)
        self.assertEqual(obs["observed"].shape, (len(groups), len(GENES)))
        for arm in ("d", "g", "m"):
            z = np.load(self.d / "run" / arm / "eval_shifts.npz")
            self.assertEqual(z["predicted"].shape, (len(groups), len(GENES)))
            held = [i for i, g in enumerate(groups) if g["class"] in ("C", "J")]
            self.assertTrue(np.isfinite(z["predicted"][held].astype(float)).any(axis=1).all(), arm)
        ev = self.read("run", "g", "eval.json")
        self.assertEqual(ev["summary"]["arm"]["target_code"], "generic")


    def test_generated_cells(self):
        import scipy.sparse as sp
        targets = self.d / "gen_targets.json"
        targets.write_text(json.dumps([{"key": "sa|La", "symbol": "G1"}, {"key": "sb|Lb", "symbol": "G2"},
                                       {"key": "sa|La", "symbol": "G5"}]), encoding="utf-8")
        out = self.d / "gen" / "cells_d.npz"
        proc = subprocess.run([sys.executable, str(HERE / "generate_cells.py"), "--prepass", str(self.d / "pre"),
                               "--arm-dir", str(self.d / "run" / "d"), "--targets", str(targets), "--n", "12",
                               "--ctrl-k", "32", "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-3000:])
        z = np.load(out)
        x = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))
        self.assertEqual(x.shape, (36, len(GENES)))
        self.assertEqual(list(z["labels"][:12]), ["G1"] * 12)
        self.assertTrue((x.data > 0).all())
        lib = np.asarray(x.sum(1)).ravel()
        self.assertTrue(500 < np.median(lib) < 20000)               # the libraries of the synthetic controls (e^8)
        side = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertTrue(all(0.0 <= b["pi"] <= 1.0 for b in side["blocks"]))
        self.assertEqual(sum(b["cells"] for b in side["blocks"]), 36)


class MeanContext(unittest.TestCase):
    def test_mean_mode_sees_only_the_pooled_profile(self):
        import torch
        sys.path.insert(0, str(HERE))
        import cellnet as CN
        rng = np.random.default_rng(0)
        a = torch.as_tensor(rng.poisson(5, (1, 4, 6)), dtype=torch.float32)
        b = a.clone()
        b[0, 0], b[0, 1] = a[0, 1], a[0, 0]                      # same cells, other order
        c = a.clone()                                             # other cells, same pooled counts and libraries
        c[0, 0, 0] += 3; c[0, 0, 1] -= 3; c[0, 1, 0] -= 3; c[0, 1, 1] += 3
        m = torch.ones(1, 4, 6, dtype=torch.bool)
        lib = torch.full((1, 4), 30.0)
        outs = {}
        for mode in ("cells", "mean"):
            torch.manual_seed(0)
            net = CN.build_model(6, 2, 1, 1, np.arange(6), dim=4, rank=2, context_mode=mode)
            with torch.no_grad():
                outs[mode] = [net.context(x, m, lib)[0] for x in (a, b, c)]
        self.assertTrue(torch.allclose(outs["cells"][0], outs["cells"][1], atol=1e-6))   # a set: order is not seen
        self.assertFalse(torch.allclose(outs["cells"][0], outs["cells"][2], atol=1e-6))  # cells: composition is seen
        self.assertTrue(torch.allclose(outs["mean"][0], outs["mean"][2], atol=1e-6))     # mean: only the pool


if __name__ == "__main__":
    unittest.main()
