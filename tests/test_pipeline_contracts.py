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
from vcc2026.manifest import RunManifest, file_fingerprint, text_sha256  # noqa: E402


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

    def test_text_hash_does_not_depend_on_line_endings(self):
        """A recipe hashes the same on any checkout, and still tells two recipes apart."""
        with tempfile.TemporaryDirectory() as d:
            lf, crlf, other = (Path(d) / n for n in ("lf.json", "crlf.json", "other.json"))
            lf.write_bytes(b'{"name": "t15",\n "amplitude": 0.394}\n')
            crlf.write_bytes(b'{"name": "t15",\r\n "amplitude": 0.394}\r\n')
            other.write_bytes(b'{"name": "t15",\n "amplitude": 0.788}\n')
            self.assertNotEqual(file_fingerprint(lf)["sha256"], file_fingerprint(crlf)["sha256"])
            self.assertEqual(text_sha256(lf), text_sha256(crlf))
            self.assertEqual(text_sha256(lf), file_fingerprint(lf)["sha256"])
            self.assertNotEqual(text_sha256(lf), text_sha256(other))


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


class TestMovedPaths(unittest.TestCase):
    """D-046 moved the report folders one level down; a used recipe is never edited."""

    def test_every_repository_file_a_recipe_names_is_found(self):
        missing = []
        for recipe in sorted((REPO / "configs" / "recipes").glob("*.json")):
            spec = json.loads(recipe.read_text(encoding="utf-8"))
            named = [spec.get("cis", {}).get("pairs"), spec.get("gene_share", {}).get("path")]
            for raw in filter(None, named):
                if not config.repo_file(raw).is_file():
                    missing.append(f"{recipe.name}: {raw}")
        self.assertEqual(missing, [])

    def test_a_moved_folder_is_followed_and_anything_else_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "reports" / "trasferimento" / "cis_x").mkdir(parents=True)
            (root / "reports" / "trasferimento" / "cis_x" / "pairs.csv").write_text("a\n", encoding="utf-8")
            (root / "reports" / "a" / "twin").mkdir(parents=True)
            (root / "reports" / "b" / "twin").mkdir(parents=True)
            old = config.REPO_ROOT
            try:
                config.REPO_ROOT = root
                self.assertEqual(config.repo_file("reports/cis_x/pairs.csv"),
                                 root / "reports" / "trasferimento" / "cis_x" / "pairs.csv")
                self.assertEqual(config.repo_file("reports/trasferimento/cis_x/pairs.csv"),
                                 root / "reports" / "trasferimento" / "cis_x" / "pairs.csv")
                # nowhere, or in two places: returned as named, so the caller fails on it
                self.assertEqual(config.repo_file("reports/gone/pairs.csv"), root / "reports/gone/pairs.csv")
                self.assertEqual(config.repo_file("reports/twin"), root / "reports/twin")
                self.assertEqual(config.repo_file("configs/x.json"), root / "configs/x.json")
            finally:
                config.REPO_ROOT = old

    def test_a_renamed_document_is_followed_through_the_archive_table(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs" / "guide").mkdir(parents=True)
            (root / "docs" / "PROCEDURE.md").write_text("# P\n", encoding="utf-8")
            (root / "docs" / "guide" / "a.md").write_text("# A\n", encoding="utf-8")
            (root / "docs" / "ARCHIVIO.md").write_text(
                "| Percorso | Righe |\n|---|---|\n| `docs/ALTRO.md` | 3 |\n\n"
                "| Nome vecchio | Nome nuovo | Dal | Perché |\n|---|---|---|---|\n"
                "| `docs/LAVORO.md` | `docs/PROCEDURE.md` | 30/09/2026 | più chiaro |\n"
                "| `docs/vecchia/` | `docs/guide/` | 30/09/2026 | cartella |\n\n"
                "| `docs/FUORI.md` | `docs/DENTRO.md` | non è la tabella dei nomi |\n", encoding="utf-8")
            old = config.REPO_ROOT
            try:
                config.REPO_ROOT = root
                self.assertEqual(config.renamed_paths(),
                                 {"docs/LAVORO.md": "docs/PROCEDURE.md", "docs/vecchia/": "docs/guide/"})
                self.assertEqual(config.repo_file("docs/LAVORO.md"), root / "docs" / "PROCEDURE.md")
                self.assertEqual(config.repo_file("docs/vecchia/a.md"), root / "docs" / "guide" / "a.md")
                # renamed to a file that is not there, or never renamed: returned as named
                self.assertEqual(config.repo_file("docs/vecchia/b.md"), root / "docs/vecchia/b.md")
                self.assertEqual(config.repo_file("docs/ALTRO.md"), root / "docs/ALTRO.md")
            finally:
                config.REPO_ROOT = old

    def test_the_checker_and_repo_file_read_the_same_renames(self):
        """Two readers of one table in docs/ARCHIVIO.md: they must agree on the real one."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("check_docs", REPO / "scripts" / "31_check_docs.py")
        check_docs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check_docs)
        self.assertEqual(config.renamed_paths(), check_docs.renamed_paths(REPO))
        self.assertIn("docs/LAVORO.md", config.renamed_paths())


if __name__ == "__main__":
    unittest.main()
