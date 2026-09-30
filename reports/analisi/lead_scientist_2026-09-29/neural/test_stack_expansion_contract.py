"""Frozen shell/archive contracts, without matrices, third-party packages or I/O."""
import ast
import hashlib
import json
from pathlib import Path
import re
import tarfile
import unittest

HERE = Path(__file__).resolve().parent
SETUP = HERE / "stack_expansion_setup_r1"
REL = "reports/analisi/lead_scientist_2026-09-29/neural"


class ExpansionContract(unittest.TestCase):
    def setUp(self):
        self.archive_bytes = (SETUP / "code_snapshot.tar.gz").read_bytes()
        self.manifest = json.loads((SETUP / "setup_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(self.archive_bytes).hexdigest(), self.manifest["code_archive_sha256"])
        with tarfile.open(SETUP / "code_snapshot.tar.gz", "r:gz") as archive:
            self.files = {item.name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile()}
        self.assertEqual(set(self.files), {row["path"] for row in self.manifest["files"]})
        for row in self.manifest["files"]:
            self.assertEqual(hashlib.sha256(self.files[row["path"]]).hexdigest(), row["sha256"])

    def registration_for(self, kind):
        text = (SETUP / f"colab_stack_{kind}_prepare_r1.sh").read_text(encoding="utf-8")
        self.assertIn(f"REPORT={REL}", text)
        self.assertIn(self.manifest["code_archive_sha256"], text)
        match = re.findall(r'--registration "\$REPORT/([^\"]+)"', text)
        self.assertEqual(len(match), 1)
        self.assertNotEqual(match[0], "target_registration.json")
        return json.loads(self.files[REL + "/" + match[0]])

    def test_production_shell_points_to_json_with_actual_packer_keys(self):
        registration = self.registration_for("production")
        tree = ast.parse(self.files[REL + "/stack_production_pack.py"].decode())
        keys = {node.slice.value for node in ast.walk(tree) if isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name) and node.value.id == "registration"
                and isinstance(node.slice, ast.Constant)}
        self.assertTrue(keys.issubset(registration))
        targets = registration["production_targets_subset_ge64"]
        fallback = registration["production_fallback_targets"]
        counts = registration["counts_per_panel_target"]
        self.assertEqual(len(targets), 254)
        self.assertEqual(len(fallback), 46)
        self.assertEqual(set(targets) | set(fallback), set(counts))
        self.assertFalse(set(targets) & set(fallback))
        self.assertTrue(all(counts[t] >= 64 for t in targets))
        self.assertTrue(all(counts[t] < 64 for t in fallback))

    def test_confirmation_registration_and_readable_summary_agree(self):
        registration = self.registration_for("confirmation")
        summary = json.loads((SETUP / "target_registration.json").read_text(encoding="utf-8"))
        mapping = {"production_targets": "production_targets_subset_ge64", "production_fallback": "production_fallback_targets",
                   "source_counts": "counts_per_panel_target", "confirmation_targets": "confirmation_targets_original"}
        for human_key, input_key in mapping.items():
            self.assertEqual(summary[human_key], registration[input_key])
        self.assertEqual(len(summary["confirmation_targets"]), 12)
        self.assertEqual(len(set(summary["confirmation_targets"])), 12)


if __name__ == "__main__":
    unittest.main()
