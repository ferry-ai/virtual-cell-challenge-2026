"""Small tests for preflight integrity and held-out-target guards, without scoring."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import input_contract as IC
import export_effects as E


class PreparationTest(unittest.TestCase):
    def test_hash_guard_rejects_same_size_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "input"
            f.write_bytes(b"original")
            c = {"inputs": [{"local": str(f), "root": "data", "relative": "input", "bytes": 8,
                             "sha256": IC.sha(f)}], "scorer_version": "0.16.0"}
            self.assertTrue(IC.verify(c)["ok"])
            f.write_bytes(b"modified")
            with self.assertRaises(ValueError):
                IC.verify(c)
            with self.assertRaises(ValueError):
                IC.verify(c, {"data": Path(tmp)})

    def export_fixture(self, root, cls="C", changed=False):
        z = root / "real.npz"
        np.savez(z, labels=np.asarray(["A"] * 4 + ["non-targeting"] * 4), genes=np.asarray(["g1", "g2"]))
        (root / "targets.json").write_text(json.dumps([{"symbol": "A", "key": "a", "target_key": "a"}]))
        (root / "expected.json").write_text(json.dumps({"inputs": {"frozen": "yes"}}))
        (root / "weights.json").write_text("{}")
        s = SimpleNamespace(inputs={"frozen": "changed" if changed else "yes"},
                            cube=SimpleNamespace(genes=["g1", "g2"]), model_genes=["g1", "g2"],
                            groups=[{"key": "a", "symbol": "A", "class": cls}],
                            pred={"ibrido": np.array([[2., 3.]]), "ancora_sola": np.array([[1., 1.]])},
                            cubes={"transfer_all_J": None, "transfer_prod_J": None},
                            sources={"transfer_all_J": ["other"], "transfer_prod_J": ["other"]},
                            commons={}, held="fixture", check_reads=lambda: None)
        argv = ["export_effects.py", "--held-group", "fixture"]
        for name in ("run", "cube", "protocol", "target-keys", "splits", "anchors-manifest"):
            argv += ["--" + name, str(root / name)]
        argv += ["--real", str(z), "--targets", str(root / "targets.json"), "--expected", str(root / "expected.json"),
                 "--weights", str(root / "weights.json"), "--out", str(root / "out")]
        with patch.object(sys, "argv", argv), patch.object(E.HL, "Setup", return_value=s), \
                patch.object(E.HL, "load_weights", return_value={}), \
                patch.object(E.HL, "arm_weights", return_value=np.array([0.5])), \
                patch.object(E, "transfer_for", return_value=(np.array([[1., np.nan]]), np.array([1]))):
            E.main()

    def test_export_preserves_baseline_mask(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.export_fixture(root)
            with np.load(root / "out/prod_wR.npz") as z:
                self.assertEqual(z["targets"].tolist(), ["A"])
                np.testing.assert_array_equal(z["observed"], [[True, False]])
                np.testing.assert_allclose(z["lfc"], [[E.AMPLITUDE_T25 + 0.5, 0]])

    def test_hidden_targets_cannot_enter_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "frozen C"):
                self.export_fixture(Path(tmp), cls="J")
            self.assertFalse((Path(tmp) / "out").exists())

    def test_changed_training_inputs_cannot_enter_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "archived"):
                self.export_fixture(Path(tmp), changed=True)
            self.assertFalse((Path(tmp) / "out").exists())


if __name__ == "__main__":
    unittest.main()
