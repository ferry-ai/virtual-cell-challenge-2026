"""Ensure the fresh fallback changes runtime only, with private data routing."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class FreshRuntimeTest(unittest.TestCase):
    def test_science_payload_and_private_notebook_agree(self):
        original = ast.parse((HERE / "stack_remote_receipt_r2/colab_stack_infer_r1.py").read_text(encoding="utf-8"))
        source = (HERE / "stack_kaggle_fresh_r1/stack_kaggle_fresh_r1.py").read_text(encoding="utf-8")
        new = ast.parse(source)
        old_args = [ast.literal_eval(x) for x in original.body[-1].value.args]
        new_args = [ast.literal_eval(x) for x in new.body[-1].value.args]
        self.assertEqual(old_args[0], new_args[0])
        self.assertEqual(hashlib.sha256(base64.b64decode(new_args[0])).hexdigest(), old_args[1]["code_archive_sha256"])
        for key, value in old_args[1].items():
            if key not in ("dataset", "kernel"):
                self.assertEqual(new_args[1][key], value)
        self.assertFalse(new.body[-1].value.keywords)
        metadata = json.loads((HERE / "stack_kaggle_fresh_r1/kernel-metadata.json").read_text())
        self.assertTrue(metadata["is_private"])
        self.assertEqual(metadata["dataset_sources"], ["davidmaisterx/vcc-stack-prompts-r1"])
        notebook = json.loads((HERE / "stack_kaggle_fresh_r1/stack_pilot_r1.ipynb").read_text())
        self.assertEqual("".join(notebook["cells"][1]["source"]), source)

    def test_both_runtime_fixes_and_preflight_precede_checkpoint(self):
        tree = ast.parse((HERE / "stack_kaggle_fresh_r1/stack_kaggle_fresh_r1.py").read_text(encoding="utf-8"))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        strings = [(n.lineno, n.value) for n in ast.walk(main) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        pooch = next(line for line, text in strings if text == "pooch==1.8.2")
        imports = next(line for line, text in strings if text == "model_imports.log")
        roundtrip = next(line for line, text in strings if text == "serialization_roundtrip.log")
        download = next(n.lineno for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "download_pinned")
        self.assertLess(pooch, imports)
        self.assertLess(imports, roundtrip)
        self.assertLess(roundtrip, download)
        guard = next(text for _, text in strings if "def guarded_load" in text)
        self.assertIn("ad.settings.allow_write_nullable_strings = True", guard)
        self.assertIn("6 * 1024**3", guard)


if __name__ == "__main__":
    unittest.main()
