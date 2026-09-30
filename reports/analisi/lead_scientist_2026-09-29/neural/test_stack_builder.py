"""Exercise the full remote builder with a synthetic LF-plan bundle, no model."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class BuilderTest(unittest.TestCase):
    def test_lf_plan_matches_crlf_registration_and_artifacts_are_private(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepared, out = root / "prepared", root / "review"
            bundle = prepared / "bundle"
            bundle.mkdir(parents=True)
            plan = json.loads((HERE / "stack_plan_r1.json").read_text())
            content = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
            (prepared / "plan.json").write_bytes(content.encode())
            allow = json.loads((HERE / "STACK_ALLOWLIST.json").read_text())
            for name in allow["inference_bundle_files"]:
                if name != "bundle.json":
                    (bundle / name).write_bytes(b"synthetic builder test only")
            manifest = plan | {"plan_sha256": hashlib.sha256(content.encode()).hexdigest(),
                               "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.iterdir()}}
            (bundle / "bundle.json").write_text(json.dumps(manifest))
            with tarfile.open(prepared / "bundle.tar.gz", "w:gz") as t:
                for path in bundle.iterdir():
                    t.add(path, arcname="./" + path.name)
            subprocess.run([sys.executable, str(HERE / "build_stack_remote.py"), "--prepared", str(prepared),
                            "--out", str(out)], check=True, stdout=subprocess.PIPE, text=True)
            kernel = json.loads((out / "kernel-metadata.json").read_text())
            self.assertTrue(kernel["is_private"])
            self.assertTrue(kernel["enable_internet"])
            notebook = json.loads((out / "stack_pilot_r1.ipynb").read_text())
            compile("".join(notebook["cells"][1]["source"]), "frozen_notebook.py", "exec")
            compile((out / "colab_stack_infer_r1.py").read_text(), "frozen_colab.py", "exec")
            review = json.loads((out / "review_manifest.json").read_text())
            self.assertEqual(review["plan_sha256"], manifest["plan_sha256"])
            self.assertEqual(review["isolated_python"], "3.11.13")


if __name__ == "__main__":
    unittest.main()
