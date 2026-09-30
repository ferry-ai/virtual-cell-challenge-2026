"""Serialization-only resume must preserve science and cached runtime."""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_stack_resume_r2 import parsed

HERE = Path(__file__).resolve().parent


class ResumeFormatTest(unittest.TestCase):
    def test_frozen_payload_and_scientific_guard_are_preserved(self):
        old, old_args, old_kw = parsed(HERE / "stack_resume_r2/colab_stack_infer_r2.py")
        new, new_args, new_kw = parsed(HERE / "stack_resume_r3/colab_stack_infer_r3.py")
        self.assertEqual(old_args, new_args)
        self.assertEqual(old_kw["bundle_archive"], new_kw["bundle_archive"])
        self.assertEqual(old_kw["scratch"], new_kw["scratch"])
        self.assertNotEqual(old_kw["work"], new_kw["work"])
        def guard(tree):
            return next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "guarded_entry" for t in n.targets))
        old_guard, new_guard = guard(old), guard(new)
        self.assertEqual(new_guard.replace("import anndata as ad\nad.settings.allow_write_nullable_strings = True\n", ""), old_guard)

    def test_main_has_no_install_or_download(self):
        tree, _, _ = parsed(HERE / "stack_resume_r3/colab_stack_infer_r3.py")
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)]
        forbidden = {"create_managed_runtime", "download_pinned"}
        self.assertFalse(any(isinstance(n.func, ast.Name) and n.func.id in forbidden for n in calls))
        for call in calls:
            if isinstance(call.func, ast.Name) and call.func.id == "run" and call.args and isinstance(call.args[0], ast.List):
                self.assertNotIn("install", [n.value for n in call.args[0].elts if isinstance(n, ast.Constant)])

    def test_two_nullable_index_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, HERE / "stack_resume_r3/serialization_roundtrip.py",
                                     Path(tmp) / "roundtrip"], text=True, capture_output=True, check=True)
            self.assertIn('"counts_exact": true', result.stdout)
            self.assertIn('"axis_exact": true', result.stdout)
            self.assertEqual(result.stdout.count('"labels_exact": true'), 2)


if __name__ == "__main__":
    unittest.main()
