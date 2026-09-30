"""Verify durable checkpoint bytes and unchanged generation/package arguments."""
from pathlib import Path
import ast
import importlib.util
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NEW = HERE / "recovery_r2/generate_candidate_r2.py"
spec = importlib.util.spec_from_file_location("recovery", NEW)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def test_publish_exact_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, dest = root / "input", root / "output"
            source.write_bytes(bytes(range(256)) * 50)
            result = recovery.publish_verified(source, dest)
            self.assertEqual(source.read_bytes(), dest.read_bytes())
            self.assertEqual(result["sha256"], recovery.sha256(source))
            self.assertFalse((root / "output.partial").exists())
            with self.assertRaises(FileExistsError):
                recovery.publish_verified(source, dest)

    def test_partial_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "input").write_bytes(b"new")
            (root / "output.partial").write_bytes(b"old")
            with self.assertRaises(FileExistsError):
                recovery.publish_verified(root / "input", root / "output")
            self.assertEqual((root / "output.partial").read_bytes(), b"old")

    def test_stage_arguments_unchanged(self):
        def args(path):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            return {node.targets[0].id: ast.dump(node.value) for node in ast.walk(tree)
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in {"command45", "command48"}}
        self.assertEqual(args(HERE / "generate_candidate.py"), args(NEW))
        self.assertEqual(len(args(NEW)), 2)

    def test_checkpoint_precedes_packaging(self):
        source = NEW.read_text(encoding="utf-8")
        self.assertLess(source.index('save(checkpoint / "complete.json"'), source.index("run(command48,"))
        job = (HERE / "recovery_r2/079_lead_t28_generate_r2.sh").read_text()
        self.assertIn("078_lead_candidate_environment_r3.sh.done", job)
        self.assertIn("--run-id t28r2 --phi-scale 1", job)


if __name__ == "__main__":
    unittest.main()
