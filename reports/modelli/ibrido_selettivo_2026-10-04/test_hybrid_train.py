"""Version 5 of train_cellnet.py (the D-056 network, PROTOCOLLO.md §4–5) on a synthetic anchored corpus.

- with --lr 0 the network is its anchor: every exported shift of the first arm equals 'ancora_sola' exactly, so
  R = s(N) - s(A) = 0 and the hybrid with any weight is the transfer;
- the common head is in the training likelihood and never in a shift: forward returns anchor + delta whatever the
  head, common() returns the head (model level);
- a training with every option: exit 0, validation pairs chosen by the rule, their cells drawn with loss weight 0
  (val.json), guard checks written, exposure passed with the effective shares, best state exported and last state kept;
- a guard that cannot be met stops the run after --guard-patience checks ('guard'), and the line is still evaluated;
- resume is refused with guards; guards without validation pairs are refused.

    python -m unittest test_hybrid_train -v        (from this folder, with the project venv; a few minutes)
"""
from __future__ import annotations

import hashlib
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
import anchors as A  # noqa: E402
from fixtures import GENES, counts, key_in_fold, write_shard  # noqa: E402

TRAIN = ["--batch", "32", "--ctrl-k", "16", "--dim", "8", "--rank", "4", "--device", "cpu", "--measure-from", "2",
         "--measure-steps", "3", "--log-every", "5", "--reserve-export-minutes", "0.05", "--gate-mode", "off",
         "--delta-bound", "6", "--roles", "2", "--share-window", "10", "--time-every", "4", "--unit-buffer", "2",
         "--train-budget-minutes", "20", "--eval-budget-minutes", "10", "--epochs", "2"]
HYBRID = ["--gain-mode", "fixed", "--common-head", "--delta-l2", "0.05", "--val-frac", "1.0", "--val-per-key", "2",
          "--val-min-admitted", "10", "--guard-every", "10", "--guard-min-cells", "2", "--guard-min-pairs", "2"]


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), *map(str, args)], capture_output=True,
                          text=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_anchors(folder: Path, st, rng):
    """Anchors for every training pair and the held-out C groups, sources a made-up group 'SRC'."""
    index, rows = [], []
    G = len(st["genes"])
    for L, role, syms in A.jobs_of(st):
        for s in syms:
            index.append({"group": L, "symbol": s, "target_key": f"K:{s}", "role": role, "sources": ["SRC"],
                          "support": 1})
    for _ in index:
        v = rng.normal(0, 0.4, G).astype(np.float32)
        v[rng.random(G) < 0.1] = np.nan
        rows.append(v.astype(np.float16))
    U, _ = np.linalg.qr(rng.normal(size=(G, 2)))
    folder.mkdir(parents=True)
    np.savez(folder / "anchors.npz", rows=np.stack(rows), support=np.ones(len(index), np.int16),
             U=U.astype(np.float32), genes=np.array([str(g) for g in st["genes"]]))
    (folder / "anchors.json").write_text(json.dumps(index), encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps({
        "held_group": st["holdout_group"], "rows": len(index), "checks": {"passed": True},
        "anchored_modalities": ["CRISPRi"],
        "outputs": {"anchors_npz": sha(folder / "anchors.npz"), "anchors_json": sha(folder / "anchors.json")}}),
        encoding="utf-8")
    return folder


class HybridTrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(11)
        p = rng.dirichlet(np.ones(len(GENES)) * 2)
        p[-4:] = 0.0075
        p /= p.sum()
        q = p.copy(); q[5] *= 4; q /= q.sum()
        r = p.copy(); r[9] *= 3; r[2] *= 0.3; r /= r.sum()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        sh = d / "shards"
        sh.mkdir()
        (d / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
        for i in range(2):
            write_shard(sh / f"sk_{i}.h5ad", np.vstack([counts(rng, p, 120), counts(rng, q, 60), counts(rng, r, 60),
                                                        counts(rng, q, 50)]), "sk", "K", f"K{i}",
                        ["NTC"] * 120 + ["G1"] * 60 + ["G2"] * 60 + ["G3"] * 50,
                        [f"K{i}_{j}-1" for j in range(290)], "file://sk")
        write_shard(sh / "sq.h5ad", np.vstack([counts(rng, p, 100), counts(rng, q, 60), counts(rng, r, 60),
                                               counts(rng, q, 60)]), "sq", "Q", "Q1",
                    ["NTC"] * 100 + ["G1"] * 60 + ["G2"] * 60 + ["G4"] * 60, [f"Q{i}-1" for i in range(280)],
                    "file://sq")
        write_shard(sh / "sa.h5ad", np.vstack([counts(rng, p, 100), counts(rng, q, 40), counts(rng, r, 40),
                                               counts(rng, q, 30)]), "sa", "La", "A1",
                    ["NTC"] * 100 + ["G1"] * 40 + ["G2"] * 40 + ["G4"] * 30, [f"A{i}-1" for i in range(210)],
                    "file://sa")
        keys = {s: key_in_fold(s, 0, want=(s == "G4")) for s in ("G1", "G2", "G3", "G4")}
        (d / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
        (d / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE"}}), encoding="utf-8")
        cls.pre = run("prepass", "--shards", sh, "--axis", d / "axis.csv", "--line-groups", d / "groups.json",
                      "--holdout-group", "LINE", "--hidden-fold", "0", "--target-keys", d / "keys.json",
                      "--pool-size", "48", "--ctrl-k", "16", "--input-genes", "16", "--eval-min-cells", "10",
                      "--min-controls-per-key", "20", "--out", d / "pre")
        assert cls.pre.returncode == 0, cls.pre.stderr[-3000:]
        cls.st = pickle.loads((d / "pre" / "prepass.pkl").read_bytes())
        cls.anchors = write_anchors(d / "anchors", cls.st, np.random.default_rng(3))
        arms = ["--arm", "a=both", "--arm", "m=both/mean"]
        common = ["--prepass", d / "pre", "--anchors", cls.anchors, *arms, *TRAIN]
        cls.frozen = run("train", "--out", d / "frozen", "--lr", "0", *common, *HYBRID)
        cls.learned = run("train", "--out", d / "learned", "--lr", "3e-3", *common, *HYBRID)
        cls.stopped = run("train", "--out", d / "stopped", "--lr", "3e-3", *common, *HYBRID,
                          "--guard-ratio-max", "0", "--guard-patience", "2")
        cls.no_val = run("train", "--out", d / "no_val", *common, "--guard-every", "10")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, *parts):
        return json.loads(self.d.joinpath(*parts).read_text(encoding="utf-8"))

    def shifts(self, run_dir, arm):
        with np.load(self.d / run_dir / arm / "eval_shifts.npz") as z:
            return z["predicted"].astype(np.float32)

    def test_runs_finished(self):
        for name in ("frozen", "learned", "stopped"):
            proc = getattr(self, name)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr[-3000:]}")
        cfg = self.read("learned", "config.json")
        self.assertEqual(cfg["code_version"], 5)
        self.assertEqual(cfg["args"]["gain_mode"], "fixed")
        self.assertEqual(cfg["args"]["common_head"], "True")

    def test_untrained_network_is_its_anchor(self):
        groups = self.read("frozen", "eval_groups.json")
        net, anc = self.shifts("frozen", "a"), self.shifts("frozen", "ancora_sola")
        c_rows = [i for i, g in enumerate(groups) if g["class"] == "C" and g["evaluated_cells"]]
        self.assertTrue(c_rows)
        for i in c_rows:
            ok = np.isfinite(net[i]) & np.isfinite(anc[i])
            self.assertGreater(ok.sum(), 10)
            np.testing.assert_array_equal(net[i][ok], anc[i][ok])        # R = 0 exactly: w is irrelevant

    def test_common_head_never_in_the_shift(self):
        import torch
        import cellnet as CN
        G = 12
        torch.manual_seed(0)
        model = CN.build_model(G, 5, 1, 1, np.arange(4), dim=8, rank=4, target_code="identity", anchor_rank=2,
                               anchor_U=np.linalg.qr(np.random.default_rng(0).normal(size=(G, 2)))[0].astype(np.float32),
                               gain_mode="fixed", common_head=True)
        with torch.no_grad():
            model.common_net[2].weight.normal_()
            model.common_net[2].bias.normal_()
        z, beta = torch.randn(3, 8), torch.randn(3, G)
        anchor, info = torch.randn(3, G), torch.ones(3, 2)
        tgt, tg, mod = torch.tensor([0, 1, 2]), torch.tensor([-1, -1, -1]), torch.zeros(3, dtype=torch.long)
        shift, _ = model(z, beta, tgt, tg, mod, anchor, info)
        torch.testing.assert_close(shift, anchor)                        # delta starts at zero, no gain, no common
        self.assertGreater(float(model.common(z, mod).abs().sum()), 0.0)
        self.assertFalse(hasattr(model, "gain_head"))
        self.assertTrue(torch.all(model.gain(z, beta, tgt, tg, mod, anchor, info) == 1))

    def test_validation_pairs_carry_no_loss(self):
        v = self.read("learned", "val.json")
        self.assertTrue(v["zero_weight_passed"])
        self.assertEqual(v["loss_weight_of_validation_cells"], 0.0)
        self.assertGreater(v["val_draws"], 0)
        keys = {p["key"] for p in v["pairs"]}
        self.assertTrue(all(k.split("|")[1] in ("K", "Q") for k in keys))       # training keys only, never La
        per_key = {}
        for p in v["pairs"]:
            per_key[p["key"]] = per_key.get(p["key"], 0) + 1
            self.assertNotEqual(p["symbol"], "G4")                                 # hidden: no anchor, no pair
        self.assertTrue(all(n <= 2 for n in per_key.values()))
        exp = self.read("learned", "exposure.json")
        self.assertIn("effective_run_shares", exp)
        # the draws are balanced; the effective shares leave the validation cells out, and in this tiny corpus they
        # are a large part of one group: the receipt must say so and fail the run's exposure (PROTOCOLLO.md §10)
        self.assertLessEqual(exp["run_max_abs_deviation"], 0.02)
        eff = exp["effective_run_shares"]
        self.assertAlmostEqual(sum(eff.values()), 1.0, places=5)
        self.assertEqual(exp["effective_passed"], exp["effective_max_abs_deviation"] <= 0.02)
        self.assertEqual(exp["passed"], exp["effective_passed"] and not exp["windows_out_of_rule"]
                         and not exp["units_never_drawn"])

    def test_guards_and_exported_state(self):
        g = self.read("learned", "guard.json")
        self.assertGreaterEqual(len(g["checks"]), 2)
        for c in g["checks"]:
            for arm in ("a", "m"):
                m = c["arms"][arm]
                self.assertIn("breaches", m)
                self.assertGreater(m["pairs_used"], 0)
                self.assertIsNotNone(m["ratio"])
        v = self.read("learned", "val.json")
        self.assertIn(v["exported"]["a"]["state"], ("best check", "last (no check without a breach, or no guard)"))
        self.assertTrue((self.d / "learned" / "a" / "model_last.pt").is_file())
        self.assertTrue((self.d / "learned" / "ancora_sola" / "eval_shifts.npz").is_file())

    def test_guard_stop(self):
        v = self.read("stopped", "val.json")
        self.assertEqual(v["stop"], "guard")
        g = self.read("stopped", "guard.json")
        self.assertEqual(len(g["checks"]), 2)
        self.assertTrue(all("ratio" in c["arms"]["a"]["breaches"] for c in g["checks"]))
        self.assertTrue(self.read("stopped", "done.json")["evaluation_complete"])

    def test_refusals(self):
        self.assertNotEqual(self.no_val.returncode, 0)
        self.assertIn("needs validation pairs", self.no_val.stderr[-2000:])
        res = run("train", "--out", self.d / "resumed", "--resume", self.d / "learned", "--prepass", self.d / "pre",
                  "--anchors", self.anchors, "--arm", "a=both", *TRAIN, *HYBRID)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("resume is refused", res.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
