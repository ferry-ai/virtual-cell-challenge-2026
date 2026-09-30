"""Synthetic builder test: preserve all original science/data and isolate B."""
import ast
import base64
import io
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import build_stack_variant_b_runtime as builder


class VariantRuntimeTest(unittest.TestCase):
    def test_original_files_exact_and_b_cli_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(out=Path(tmp) / "out", kernel="fixture/b", adapter_cli="direct")
            for key in ("adapter", "protocol", "scorer", "test"):
                setattr(args, key, builder.HERE / ("synthetic_b_" + key + ".py"))
                setattr(args, key + "_sha256", "fixturehash-" + key)
            with patch.object(builder, "read_checked", return_value=b"# synthetic only\n"):
                review = builder.build(args)
            self.assertEqual(review["dataset"], "davidmaisterx/vcc-stack-prompts-r1")
            self.assertEqual(review["bundle_archive_sha256"], "8c693c8457590edca74e626b08d7318a276c44f4b9737f5d4d4c13272814cf3e")
            self.assertEqual(review["kernel"], "fixture/b")
            source = (args.out / "stack_variant_b_r1.py").read_text()
            self.assertIn("report / 'synthetic_b_adapter.py', \"--bundle\", bundle,", source)
            self.assertNotIn('report / "stack_pilot.py", "infer",', source)
            self.assertIn("/kaggle/working/lead_stack_variant_b_r1", source)
            self.assertIn("/tmp/lead_stack_variant_b_scratch_r1", source)
            old_tree = ast.parse((builder.HERE / "stack_kaggle_fresh_r2/stack_kaggle_fresh_r2.py").read_text())
            old_payload = base64.b64decode(ast.literal_eval(old_tree.body[-1].value.args[0]))
            with tarfile.open(fileobj=io.BytesIO(old_payload), mode="r:gz") as old, tarfile.open(args.out / "code_snapshot.tar.gz", "r:gz") as new:
                for member in old.getmembers():
                    self.assertEqual(old.extractfile(member).read(), new.extractfile(member.name).read())
            notebook = json.loads((args.out / "stack_variant_b_r1.ipynb").read_text())
            self.assertEqual("".join(notebook["cells"][1]["source"]), source)
            self.assertTrue(json.loads((args.out / "kernel-metadata.json").read_text())["is_private"])

    def test_cannot_read_code_outside_reviewed_folder(self):
        with self.assertRaisesRegex(ValueError, "named file"):
            builder.read_checked(Path("C:/elsewhere/adapter.py"), "irrelevant")


if __name__ == "__main__":
    unittest.main()
