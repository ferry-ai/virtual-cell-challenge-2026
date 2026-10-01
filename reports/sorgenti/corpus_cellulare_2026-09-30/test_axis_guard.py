"""rlab_job stops a unit at its first shard when its features do not map to the official axis (1/10: the Replogle
shards kept the Ensembl ids of var as symbols, no gene mapped, every cell had zero counts on the model genes).

    python -m unittest test_axis_guard -v          (from this folder)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_legacy_categories import legacy_file  # noqa: E402


def run_job(tmp: Path, axis_genes):
    legacy_file(tmp / "src.h5ad")
    (tmp / "axis.csv").write_text("gene_name\n" + "\n".join(axis_genes) + "\n", encoding="utf-8")
    spec = {"job_id": "t", "min_free_stage_bytes": 0, "units": [{"name": "u", "adapter": "h5rows", "kwargs": {
        "path": str(tmp / "src.h5ad"), "study": "s", "context": "K", "chemistry": "10x", "modality": "CRISPRi",
        "axis_csv": str(tmp / "axis.csv"), "block": 10, "target_col": "gene", "control_values": ["non-targeting"],
        "library_col": "gem_group"}, "source": {"id": "s", "files": [{"locator": "local", "bytes": 1}]}}]}
    (tmp / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    return subprocess.run([sys.executable, str(HERE / "rlab_job.py"), "--spec", str(tmp / "spec.json"), "--stage",
                           str(tmp / "stage"), "--out", str(tmp / "out")], capture_output=True, text=True)


class AxisGuard(unittest.TestCase):
    def test_unmapped_features_stop_the_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_job(Path(tmp), ["TSPAN6", "TNMD"])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("features map to the official axis", r.stderr + r.stdout)
            self.assertTrue((Path(tmp) / "out" / "u" / "receipts" / "shard_00000.FAILED.json").is_file())

    def test_mapped_features_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_job(Path(tmp), ["G1", "G2", "G3", "G4"])
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
