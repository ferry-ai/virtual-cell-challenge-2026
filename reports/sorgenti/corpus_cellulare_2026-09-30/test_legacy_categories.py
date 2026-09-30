"""adapters.h5rows reads the old anndata encoding of categoricals (integer codes in obs/<col>, categories in
obs/__categories/<col>), as in the Replogle 2022 files on Figshare: until 1/10 it read the codes, so the targets of
jobs J06 and J07 were numbers and no control was found.

    python -m unittest test_legacy_categories -v          (from this folder)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adapters  # noqa: E402


def legacy_file(path: Path):
    genes = np.array([b"non-targeting", b"TFAM", b"LAT"])
    codes = np.array([0, 1, 2, 1, 0, 2], dtype=np.int8)
    gem = np.array([b"1", b"2"])
    with h5py.File(path, "w") as f:
        f.create_dataset("X", data=np.arange(6 * 4, dtype=np.float32).reshape(6, 4))
        obs = f.create_group("obs")
        obs.attrs["_index"] = "cell_barcode"
        obs.create_dataset("cell_barcode", data=np.array([f"AAAC{i}-1".encode() for i in range(6)]))
        obs.create_dataset("gene", data=codes)
        obs.create_dataset("gem_group", data=np.array([0, 0, 1, 1, 0, 1], dtype=np.int8))
        obs.create_dataset("UMI_count", data=np.full(6, 1000.0))
        cats = obs.create_group("__categories")
        cats.create_dataset("gene", data=genes)
        cats.create_dataset("gem_group", data=gem)
        var = f.create_group("var")
        var.attrs["_index"] = "gene_name"
        var.create_dataset("gene_name", data=np.array([b"G1", b"G2", b"G3", b"G4"]))


class LegacyCategories(unittest.TestCase):
    def test_codes_become_their_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.h5ad"
            legacy_file(path)
            (_, x, obs, var, _), = list(adapters.h5rows(str(path), "s", "K562", "10x", "CRISPRi", None, block=10,
                                                        target_col="gene", control_values=["non-targeting"],
                                                        library_col="gem_group", published_depth="UMI_count"))
        self.assertEqual(obs["target_published"].tolist(), ["non-targeting", "TFAM", "LAT", "TFAM", "non-targeting", "LAT"])
        self.assertEqual(obs["target"].tolist(), ["NTC", "TFAM", "LAT", "TFAM", "NTC", "LAT"])
        self.assertEqual(obs["control_kind"].tolist().count("NTC"), 2)
        self.assertEqual(obs["library"].tolist(), ["1", "1", "2", "2", "1", "2"])
        self.assertEqual(x.shape, (6, 4))


if __name__ == "__main__":
    unittest.main()
