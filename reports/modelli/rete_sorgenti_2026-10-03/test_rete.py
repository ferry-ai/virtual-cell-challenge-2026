"""Synthetic checks of the source-attention network (run from this folder: python -m unittest test_rete).

Keys of three cell types; a target's effect is a response shared within its type plus a weaker one shared by all,
plus noise; basal profiles cluster by type. The equal-weight transfer then mixes in the other types' responses, and
the network can only beat it by learning, from basal profiles, to trust same-type sources."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

import rete


def synthetic_keys(seed=0, G=600, T=50, per_type=5):
    rng = np.random.default_rng(seed)
    types = ["alpha", "beta", "gamma"]
    shared = {ty: rng.normal(0, 1.0, (T, G)) * (rng.random((T, G)) < 0.1) for ty in types}
    common = rng.normal(0, 0.4, (T, G)) * (rng.random((T, G)) < 0.05)
    centre = {ty: rng.normal(2.0, 1.0, G) for ty in types}
    targets = np.array([f"T{i:03d}" for i in range(T)])
    keys = []
    for ty in types:
        for j in range(per_type):
            eff = (shared[ty] + common + rng.normal(0, 0.3, (T, G))).astype(np.float16)
            eff[:, rng.random(G) < 0.05] = np.nan
            keep = rng.random(T) < 0.8
            basal = np.clip(centre[ty] + rng.normal(0, 0.3, G), 0, None).astype(np.float32)
            keys.append(rete.Key(f"study_{ty}{j}|line{j}", f"{ty}{j}", ty, targets[keep], eff[keep], basal,
                                 np.ones(G, bool)))
    return keys


class Rete(unittest.TestCase):
    def setUp(self):
        self.keys = synthetic_keys()

    def test_step0_is_the_equal_weight_transfer(self):
        cfg = rete.Config(panel=200)
        train = self.keys[1:]
        panel = rete.basal_panel(train, cfg.panel)
        B = np.stack([k.basal for k in train])[:, panel]
        model = rete.SourceAttention(600, panel, B.mean(0), B.std(0) + 1e-3, cfg)
        ep = rete.episode(self.keys[0], rete.allowed_sources(self.keys[0], train), np.random.default_rng(0), 16, 300)
        (l, _, _), alpha, _ = rete.run_episode(model, ep, cfg)
        (lu, _, _), _, _ = rete.run_episode(model, ep, cfg, uniform=True)
        self.assertAlmostEqual(float(l), float(lu), places=4)
        h = rete.attention_health(alpha, torch.as_tensor(ep["avail"]))
        self.assertAlmostEqual(h["entropy_norm"], 1.0, places=4)

    def test_exclusions(self):
        L = rete.Key("hipsci_targeted_19|kolf_2", "hipsci", "pluripotent", np.array(["A"]),
                     np.zeros((1, 3), np.float16), np.zeros(3, np.float32), np.ones(3, bool))
        kolf = rete.Key("kolf_strong|KOLF2.1J", "kolf", "pluripotent", np.array(["A"]),
                        np.zeros((1, 3), np.float16), np.zeros(3, np.float32), np.ones(3, bool))
        other = rete.Key("hipsci_targeted_19|zapk_3", "hipsci", "pluripotent", np.array(["A"]),
                         np.zeros((1, 3), np.float16), np.zeros(3, np.float32), np.ones(3, bool))
        self.assertEqual([k.key for k in rete.allowed_sources(kolf, [L, other])], [other.key])  # only kolf_2 out
        self.assertEqual([k.key for k in rete.allowed_sources(L, [kolf, other])], [other.key])  # KOLF2.1J out
        clone = rete.Key("hipsci_targeted_19|kolf_3", "hipsci", "pluripotent", np.array(["A"]),
                         np.zeros((1, 3), np.float16), np.zeros(3, np.float32), np.ones(3, bool))
        self.assertEqual(rete.allowed_sources(L, [clone]), [])                # same donor, another clone

    def test_learns_to_trust_same_type_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = rete.Config(panel=200, steps=400, eval_every=50, keep_steps=(0, 100), min_steps=400,
                              targets_per_episode=16, genes_per_episode=300, lr=1e-2)
            summ = rete.train(self.keys, val_groups=["alpha0", "beta0"], test_groups=["gamma0"],
                              out=Path(tmp), cfg=cfg)
            mon = [json.loads(l) for l in (Path(tmp) / "monitor.jsonl").read_text().splitlines()]
            evals = [m for m in mon if "delta_loss" in m]
            self.assertLess(evals[-1]["delta_loss"], 0, evals[-1])             # beats its own start on validation
            self.assertGreater(evals[-1]["net_cos"], evals[-1]["uni_cos"])
            trains = [m for m in mon if "entropy_norm" in m and m["entropy_norm"] is not None]
            self.assertLess(trains[-1]["entropy_norm"], 0.95)                  # attention moved off equal weights
            for s in (0, 100):
                self.assertTrue((Path(tmp) / f"ckpt_step{s:06d}.pt").exists())
            split = json.loads((Path(tmp) / "split.json").read_text())
            self.assertFalse(set(split["train"]) & (set(split["val"]) | set(split["test"])))
            # export on a line with no truth, the shape the benches read
            L = next(k for k in self.keys if k.group == "gamma0")
            model = rete.SourceAttention(600, rete.basal_panel([k for k in self.keys if k.key in split["train"]], 200),
                                         np.zeros(200), np.ones(200), cfg)
            path = Path(tmp) / "eff.npz"
            rete.export_effects(model, L, [k for k in self.keys if k.key in split["train"]], L.targets[:5], path)
            with np.load(path) as z:
                self.assertEqual(z["lfc"].shape, (5, 600))
            print(json.dumps(evals[-1]))


class Pipeline(unittest.TestCase):
    def test_files_in_the_dati_layout_train_and_export(self):
        keys = synthetic_keys(seed=1)
        with tempfile.TemporaryDirectory() as tmp:
            kd = Path(tmp) / "chiavi"
            kd.mkdir()
            for k in keys:                                     # the layout dati.py writes
                np.savez_compressed(kd / (k.key.replace("|", "__") + ".npz"), targets=k.targets, eff=k.eff,
                                    basal=k.basal, measured=k.measured, n_cells=np.ones(len(k.targets)), key=k.key,
                                    group=k.group, type=k.type)
            loaded = rete.load_keys(kd)
            self.assertEqual(sorted(k.key for k in loaded), sorted(k.key for k in keys))
            cfg = rete.Config(panel=200, steps=60, eval_every=20, keep_steps=(0,), min_steps=60,
                              targets_per_episode=8, genes_per_episode=200)
            run = Path(tmp) / "run"
            rete.train(loaded, ["alpha0"], ["gamma0"], run, cfg)
            gamma0 = next(k.key for k in loaded if k.group == "gamma0")
            done = rete.export_lines(kd, run, [gamma0], Path(tmp) / "exp")
            with np.load(Path(tmp) / "exp" / "net_gamma0.npz") as z:
                self.assertEqual(z["lfc"].shape[1], 600)
                self.assertTrue(np.isfinite(z["lfc"]).all())
            with np.load(Path(tmp) / "exp" / "net0_gamma0.npz") as z0:
                self.assertEqual(z0["lfc"].shape[0], done["net0_gamma0"]["targets"])
            self.assertNotIn(gamma0, done["net_gamma0"]["sources"])


if __name__ == "__main__":
    unittest.main()
