"""cellnet.read_csr filters the stored CSR in place (1/10, incident E-20261001-001): the matrix must be the one built
from the dense counts and the column map, with native features out of axis order, two features on one gene (masked,
never summed), features off the axis and empty rows; and a cell's fingerprint must not depend on the native order.

    python -m unittest test_read_csr -v          (from this folder, with the project venv)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cell_data as CD  # noqa: E402
import cellnet as CN  # noqa: E402
from test_prepass import GENES, write_shard  # noqa: E402


def reference(x, native):
    """Dense counts on the model genes (the axis order), a colliding gene left empty."""
    out = np.zeros((x.shape[0], len(GENES)))
    names = np.asarray(native)
    for j, g in enumerate(GENES):
        hits = np.flatnonzero(names == g)
        if hits.size == 1:
            out[:, j] = x[:, hits[0]]
    return out


class ReadCsr(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, x, native, name):
        p = self.d / name
        write_shard(p, x, "s", "K", "L", ["NTC"] * x.shape[0], [f"b{i}" for i in range(x.shape[0])], "file://s",
                    native=native)
        info = CN.index_shard(p)
        return CN.read_csr(p, info.official_index, info.measured, np.arange(len(GENES)), len(GENES))

    def test_same_matrix_as_the_dense_reference(self):
        rng = np.random.default_rng(5)
        native = ["G9", "G2", "XOFF1", "G7", "G30", "G1", "G7", "XOFF2"] + \
                 [g for g in GENES if g not in ("G9", "G2", "G7", "G30", "G1")]
        x = rng.poisson(1.2, size=(200, len(native)))
        x[:7] = 0                                                   # empty rows
        m, mask = self.read(x, native, "a.h5ad")
        np.testing.assert_array_equal(m.toarray(), reference(x, native))
        self.assertFalse(mask[GENES.index("G7")])                  # two native features on G7: masked
        self.assertTrue(mask[GENES.index("G9")])
        self.assertEqual(m.shape, (200, len(GENES)))
        keep = np.sort(rng.choice(200, 80, replace=False))
        np.testing.assert_array_equal(m[keep].toarray(), reference(x, native)[keep])

    def test_fingerprints_do_not_depend_on_the_native_order(self):
        rng = np.random.default_rng(6)
        x = rng.poisson(2.0, size=(50, len(GENES)))
        order = rng.permutation(len(GENES))
        a, _ = self.read(x, GENES, "a.h5ad")
        b, _ = self.read(x[:, order], [GENES[i] for i in order], "b.h5ad")
        np.testing.assert_array_equal(a.toarray(), b.toarray())
        np.testing.assert_array_equal(CD.fingerprints(a), CD.fingerprints(b))


if __name__ == "__main__":
    unittest.main()
