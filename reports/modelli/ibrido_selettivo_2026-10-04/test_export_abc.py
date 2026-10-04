"""Tests of export_abc.py on synthetic inputs: an untrained network gives R = 0 exactly, w = 0 returns the t25 effects,
the control file is read as the prepass reservoir holds it."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402
import export_abc as EX  # noqa: E402


def tiny(seed=0, trained=False):
    import torch
    torch.manual_seed(seed)
    G, S, inp = 12, 4, np.array([0, 2, 4, 6], np.int64)
    U = np.linalg.qr(np.random.default_rng(seed).normal(size=(G, 3)))[0].astype(np.float32)
    desc = np.random.default_rng(seed).normal(size=(S + 1, 5)).astype(np.float32)
    m = CN.build_model(G, S, 3, 2, inp, dim=8, rank=4, target_desc=desc, target_code="both", pi_floor=0.01,
                       context_mode="cells", delta_bound=6.0, anchor_rank=3, anchor_U=U, gain_mode="fixed",
                       common_head=True)
    if trained:
        with torch.no_grad():
            m.delta_out.weight.normal_(0, 0.5)
            m.target_emb.weight.normal_(0, 0.5)
    m.eval()
    ck = {"genes": [f"g{i}" for i in range(G)], "symbols": ["g1", "g3", "g5", "zz"], "modalities": ["CRISPRa", "CRISPRi", "KO"],
          "input_genes": inp.tolist()}
    return m, ck


def controls(G=12, inp=(0, 2, 4, 6), n=200, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.poisson(5.0, size=(n, G)).astype(np.float32)
    return {"x_in": x[:, list(inp)].astype(np.float16), "lib": x.sum(1).astype(np.float32),
            "measured": np.ones(G, bool), "cells": n}


def anchors(targets, G=12, seed=2):
    rng = np.random.default_rng(seed)
    return {"eligible": np.array([True, True, False, True]), "anchor": rng.normal(0, 0.3, (len(targets), G)).astype(np.float16),
            "info": np.tile(np.array([[0.5, 1.0]], np.float32), (len(targets), 1))}


class TestExport(unittest.TestCase):
    def setUp(self):
        EX.DRAWS = 64            # small for the test; the export uses 1,024 (§14)

    def test_untrained_network_gives_zero_correction(self):
        m, ck = tiny(trained=False)
        targets = ["g1", "g3", "g5", "zz"]
        R, SA, how = EX.corrections(m, ck, controls(), anchors(targets), targets, log=lambda *_: None)
        self.assertTrue(np.all(np.isnan(R[2])))                     # not corrected: NaN row
        for i in (0, 1, 3):
            self.assertTrue(np.all(np.nan_to_num(R[i]) == 0.0))
            self.assertTrue(np.isfinite(SA[i]).all())
        self.assertEqual(how["corrected"], 3)

    def test_trained_network_moves_corrected_targets_only(self):
        m, ck = tiny(trained=True)
        targets = ["g1", "g3", "g5", "zz"]
        R, _, _ = EX.corrections(m, ck, controls(), anchors(targets), targets, log=lambda *_: None)
        self.assertTrue(np.nanmax(np.abs(R[0])) > 1e-3)
        self.assertTrue(np.all(np.isnan(R[2])))

    def test_hybrid_effects_parity_and_observed(self):
        rng = np.random.default_rng(3)
        lfc = rng.normal(size=(4, 12)).astype(np.float32)
        obs = rng.random((4, 12)) > 0.3
        R = rng.normal(size=(4, 12)).astype(np.float32)
        R[1, 3] = np.nan
        self.assertTrue(np.array_equal(EX.hybrid_effects(lfc, obs, R, np.zeros(4)), lfc))
        w = np.array([0.5, 1.0, 0.0, 0.2])
        out = EX.hybrid_effects(lfc, obs, R, w)
        self.assertTrue(np.array_equal(out[~obs], lfc[~obs]))
        self.assertTrue(np.array_equal(out[2], lfc[2]))
        i, j = np.argwhere(obs & np.isfinite(R) & (w[:, None] > 0))[0]
        self.assertAlmostEqual(float(out[i, j]), float(lfc[i, j] + w[i] * R[i, j]), places=5)
        if obs[1, 3]:
            self.assertEqual(out[1, 3], lfc[1, 3])                   # an undefined R counts as 0

    def test_read_controls(self):
        import h5py
        import scipy.sparse as sp
        model_genes = ["a", "b", "c", "d", "e"]
        var = ["b", "a", "x", "c", "e"]                             # 'x' off the model axis, 'd' absent
        x = np.array([[1, 2, 7, 3, 0], [0, 4, 1, 0, 5]], np.float32)
        m = sp.csr_matrix(x)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ctrl.h5ad"
            with h5py.File(p, "w") as f:
                g = f.create_group("X")
                g.attrs["shape"] = np.array(m.shape)
                g["data"], g["indices"], g["indptr"] = m.data, m.indices, m.indptr
                f.create_group("var")["_index"] = np.array(var, dtype="S")
            c = EX.read_controls(p, model_genes, np.array([0, 3, 4], np.int64))     # a, d, e
        self.assertEqual(c["measured"].tolist(), [True, True, True, False, True])
        self.assertEqual(c["lib"].tolist(), [6.0, 9.0])                # without the off-axis gene
        self.assertEqual(c["x_in"].astype(float).tolist(), [[2, 0, 0], [4, 0, 5]])
        self.assertEqual(c["input_genes_absent"], 1)


if __name__ == "__main__":
    unittest.main()
