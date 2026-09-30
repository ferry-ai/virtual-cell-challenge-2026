"""Check frozen confirmation input/code contracts in the actual r2 archive."""
import ast
import hashlib
import json
from pathlib import Path
import tarfile
import unittest

HERE = Path(__file__).resolve().parent
SETUP = HERE / "stack_expansion_setup_r2"
REL = "reports/analisi/lead_scientist_2026-09-29/neural"


class ConfirmationSnapshotContract(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((SETUP / "setup_manifest.json").read_text())
        content = (SETUP / "code_snapshot.tar.gz").read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), self.manifest["code_archive_sha256"])
        with tarfile.open(SETUP / "code_snapshot.tar.gz", "r:gz") as tar:
            self.files = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
        self.assertEqual(set(self.files), {row["path"] for row in self.manifest["files"]})
        for row in self.manifest["files"]:
            self.assertEqual(hashlib.sha256(self.files[row["path"]]).hexdigest(), row["sha256"])

    def test_protocol_adapter_scorer_and_destination_size_binding(self):
        fixed = {"stack_confirmation_infer.py": "a6147fd5dc0aea614de9101a14c13fd4c627fcecab27c93971b81e89429c6b30",
                 "stack_confirmation_score.py": "c69d41aac1aa4bc14bcb9239b39cea675430c944ea1e7c1078f659b483a6df71",
                 "PROTOCOLLO_STACK_CONFERMA.md": "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"}
        for name, expected in fixed.items():
            self.assertEqual(hashlib.sha256(self.files[REL + "/" + name]).hexdigest(), expected)
        packer = self.files[REL + "/stack_confirmation_pack.py"].decode()
        self.assertIn('"destination_size": old["destination_size"]', packer)
        for key in ("protocol_sha256", "inference_adapter_sha256", "scoring_code_sha256"):
            self.assertIn('"' + key + '"', packer)
        self.assertIn(REL + "/test_stack_confirmation_score.py", self.files)

    def test_shell_points_to_r2_and_registration_targets_agree(self):
        shell = (SETUP / "colab_stack_confirmation_prepare_r1.sh").read_text()
        self.assertIn("lead_stack_expansion_setup_2026-09-29_r2", shell)
        self.assertIn(self.manifest["code_archive_sha256"], shell)
        self.assertIn('--registration "$REPORT/expansion_metadata_r1.json"', shell)
        self.assertNotIn("stack_confirmation_infer.py", shell)
        tree = ast.parse(self.files[REL + "/stack_confirmation_pack.py"].decode())
        targets = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "EXPECTED" for t in n.targets))
        registration = json.loads(self.files[REL + "/expansion_metadata_r1.json"])
        self.assertEqual(targets, registration["confirmation_targets_original"])
        self.assertEqual(len(targets), 12)


if __name__ == "__main__":
    unittest.main()
