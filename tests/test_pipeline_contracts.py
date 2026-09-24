"""Tests for the contracts that fail silently if they break.

Every test here corresponds to a way this project could produce a confident
wrong number rather than an error: an unmeasured gene read as a zero effect, a
stale manifest overwritten. Speed and coverage are not the point; the point is
that these particular mistakes become loud. (The split, registry and
pseudobulk-parsing contracts left with their modules on 23 September; the
alignment, signature, model and delta-metric contracts on 24 September:
docs/ARCHIVIO.md.)
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.manifest import RunManifest, file_fingerprint  # noqa: E402


class TestManifest(unittest.TestCase):
    def test_manifest_refuses_to_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.json"
            RunManifest(run_id="r", stage="s").write(path)
            with self.assertRaises(FileExistsError):
                RunManifest(run_id="r", stage="s").write(path)
            RunManifest(run_id="r", stage="s").write(path, allow_overwrite=True)

    def test_manifest_records_environment_and_seed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.json"
            RunManifest(run_id="r", stage="s", seed=7).write(path)
            body = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(body["seed"], 7)
            self.assertIn("cell-eval2", body["environment"]["packages"])
            self.assertIn("python", body["environment"])

    def test_fingerprint_marks_sampled_hashes_as_sampled(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.bin"
            p.write_bytes(b"x" * 1024)
            self.assertEqual(file_fingerprint(p)["sha256_mode"], "full")
            self.assertIn("sample", file_fingerprint(p, full=False)["sha256_mode"])

    def test_fingerprint_of_missing_file_says_so(self):
        self.assertFalse(file_fingerprint(Path("nope.bin"))["exists"])


class TestConfigPortability(unittest.TestCase):
    """No new component may depend on a hardcoded Windows path."""

    def test_artifact_root_honours_environment(self):
        old = os.environ.get(config.ARTIFACT_ENV)
        try:
            os.environ[config.ARTIFACT_ENV] = str(Path(tempfile.gettempdir()) / "vccart")
            config.reset_caches()
            self.assertTrue(str(config.artifact_root()).endswith("vccart"))
        finally:
            if old is None:
                os.environ.pop(config.ARTIFACT_ENV, None)
            else:
                os.environ[config.ARTIFACT_ENV] = old
            config.reset_caches()

    def test_run_dir_rejects_path_traversal(self):
        for bad in ("..", "a/b", "a\\b", "", "a:b"):
            with self.assertRaises(ValueError, msg=f"accepted {bad!r}"):
                config.run_dir(bad, create=False)

    def test_no_hardcoded_data_root_in_new_modules(self):
        offenders = []
        for path in (REPO / "src" / "vcc2026").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "C:/Users" in text or "C:\\\\Users" in text:
                offenders.append(path.name)
        self.assertEqual(offenders, [], f"hardcoded paths in {offenders}")


if __name__ == "__main__":
    unittest.main()
