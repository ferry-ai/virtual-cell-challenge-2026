"""Check archive/expanded identity, corruption rejection, and frozen science."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load_runtime():
    source = (HERE / "stack_kaggle_fresh_r2/stack_kaggle_fresh_r2.py").read_text()
    tree = ast.parse(source)
    args = [ast.literal_eval(x) for x in tree.body[-1].value.args]
    tree.body.pop()
    namespace = {}
    exec(compile(tree, "runtime", "exec"), namespace)
    return namespace, args, source


class ExpandedTest(unittest.TestCase):
    def test_frozen_science_and_notebook(self):
        _, args, source = load_runtime()
        old = ast.parse((HERE / "stack_kaggle_fresh_r1/stack_kaggle_fresh_r1.py").read_text())
        old_args = [ast.literal_eval(x) for x in old.body[-1].value.args]
        self.assertEqual(args[0], old_args[0])
        for key, value in old_args[1].items():
            self.assertEqual(args[1][key], value)
        notebook = json.loads((HERE / "stack_kaggle_fresh_r2/stack_pilot_r2.ipynb").read_text())
        self.assertEqual("".join(notebook["cells"][1]["source"]), source)

    def test_archive_and_expanded_exact_parity(self):
        api, _, _ = load_runtime()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "vcc-stack-prompts-r1/bundle"
            source.mkdir(parents=True)
            (source / "x.bin").write_bytes(b"data")
            manifest = {"files": {"x.bin": api["sha"](source / "x.bin")}}
            (source / "bundle.json").write_text(json.dumps(manifest))
            review = {"dataset": "owner/vcc-stack-prompts-r1", "bundle_files": ["bundle.json", "x.bin"],
                      "bundle_manifest_sha256": api["sha"](source / "bundle.json")}
            self.assertEqual(api["locate_bundle"](review, root), source)
            m1, v1 = api["stage_bundle"](source, root / "expanded", review)
            self.assertFalse(v1["archive_sha256_verified"])
            archive = root / "bundle.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                for name in review["bundle_files"]:
                    tar.add(source / name, arcname=name)
            review["bundle_archive_sha256"] = api["sha"](archive)
            m2, v2 = api["stage_bundle"](archive, root / "archived", review)
            self.assertTrue(v2["archive_sha256_verified"])
            self.assertEqual(m1, m2)
            for name in review["bundle_files"]:
                self.assertEqual((root / "expanded" / name).read_bytes(), (root / "archived" / name).read_bytes())
            (source / "x.bin").write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "checksum"):
                api["stage_bundle"](source, root / "bad", review)
            self.assertFalse((root / "bad").exists())
            (source / "extra").write_bytes(b"unexpected")
            with self.assertRaisesRegex(ValueError, "file list"):
                api["verify_bundle_directory"](source, review)


if __name__ == "__main__":
    unittest.main()
