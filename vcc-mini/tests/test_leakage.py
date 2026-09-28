"""Leakage and portability checks on the synthetic dataset (python -m unittest discover -s tests).

1. No training or validation pair has a held-out target or a held-out line as query.
2. No pair, of any split, ever receives a source from the held-out group.
3. The gene descriptors do not move when the held-out line's effects and the held-out targets'
   effects (in every line) are replaced with noise: they cannot carry test information.
4. With the default settings the model has no parameter whose size depends on the gene count (P5).
"""
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data import Fold, Mini  # noqa: E402
from model import TransferNet  # noqa: E402

SYNTH = ROOT / "synth"


def setUpModule():
    if not (SYNTH / "genes.csv").exists():
        subprocess.run([sys.executable, str(ROOT / "make_synthetic.py")], check=True)


class Leakage(unittest.TestCase):
    def setUp(self):
        self.ds = Mini(SYNTH, "cpu")

    def test_pairs_and_sources(self):
        ds = self.ds
        for held in ds.groups:
            for fold in range(5):
                sp = ds.split(Fold(held, fold), seed=fold)
                held_lines = set(sp["held_lines"])
                for split in ("train", "val"):
                    for t, q in sp[split]:
                        self.assertNotIn(t, sp["test_t"])
                        self.assertNotIn(q, held_lines)
                test_pairs = [(t, q) for q in held_lines for t in ds.row[q]]
                for t, q in sp["train"] + sp["val"] + test_pairs:
                    for ls in ds.sources(t, q, sp["train_lines"]):
                        self.assertFalse(set(ls) & held_lines, (held, fold, t))

    def test_descriptors_ignore_test_information(self):
        ds = self.ds
        for held in ds.groups:
            sp = ds.split(Fold(held, 0), seed=0)
            torch.manual_seed(0)
            before, _ = ds.readout_svd(sp["train_lines"], sp["train_t"], k=16)
            saved = [d.clone() for d in ds.delta]
            g = torch.Generator().manual_seed(1)
            for li in range(len(ds.keys)):
                for t, i in ds.row[li].items():
                    if li in sp["held_lines"] or t in sp["test_t"] or t in sp["val_t"]:
                        ds.delta[li][i] = torch.randn(ds.G, generator=g)
            torch.manual_seed(0)
            after, _ = ds.readout_svd(sp["train_lines"], sp["train_t"], k=16)
            self.assertTrue(torch.allclose(before, after), held)
            # Negative control: changing one *training* row must change the descriptors,
            # otherwise the check above would pass for any input.
            li = sp["train_lines"][0]
            t = next(t for t in ds.row[li] if t in sp["train_t"])
            ds.delta[li][ds.row[li][t]] += 5.0
            torch.manual_seed(0)
            moved, _ = ds.readout_svd(sp["train_lines"], sp["train_t"], k=16)
            ds.delta = saved
            self.assertFalse(torch.allclose(before, moved), held)

    def test_no_per_gene_parameters(self):
        count = lambda G: sum(p.numel() for p in TransferNet(torch.zeros(G, 64)).parameters())
        self.assertEqual(count(500), count(8000))
        with_res = sum(p.numel() for p in TransferNet(torch.zeros(8000, 64), gene_res=True).parameters())
        self.assertEqual(with_res - count(8000), 8000 * 64)   # the ablation adds exactly G x d


if __name__ == "__main__":
    unittest.main()
