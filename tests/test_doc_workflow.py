import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

new_checkpoint = load('new_checkpoint', '30_new_checkpoint.py')
check_docs = load('check_docs', '31_check_docs.py')

TEMPLATE = (ROOT / 'docs' / 'checkpoints' / 'TEMPLATE.md').read_text(encoding='utf-8')
INDEX = '# Indice\n\n## Elenco\n\n| N | Data | Titolo | Tipo | Corretto da |\n|---|---|---|---|---|\n| [0001](0001-primo.md) | 2026-09-12 | Primo | osservazione | — |\n'


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / 'TEMPLATE.md').write_text(TEMPLATE, encoding='utf-8')
        (self.dir / 'INDICE.md').write_text(INDEX, encoding='utf-8')
        (self.dir / '0001-primo.md').write_text('# CP-0001 — Primo\n', encoding='utf-8')

    def run_cli(self, *args):
        argv = ['30_new_checkpoint.py', '--dir', str(self.dir)] + list(args)
        with patch.object(sys, 'argv', argv):
            new_checkpoint.main()

    def test_numbers_after_the_highest_and_writes_an_index_row(self):
        self.run_cli('--slug', 'benchmark-cd4', '--title', 'Benchmark CD4',
                     '--date', '2026-09-20', '--type', 'esperimento')
        created = self.dir / '0002-benchmark-cd4.md'
        self.assertTrue(created.exists())
        text = created.read_text(encoding='utf-8')
        self.assertIn('# CP-0002 — Benchmark CD4', text)
        self.assertIn('- **Data:** 2026-09-20', text)
        self.assertIn('- **Tipo:** esperimento', text)
        self.assertIn('## 8. Domanda di comprensione', text)
        index = (self.dir / 'INDICE.md').read_text(encoding='utf-8')
        self.assertIn('| [0002](0002-benchmark-cd4.md) | 2026-09-20 | Benchmark CD4 |', index)
        self.assertLess(index.index('[0001]'), index.index('[0002]'))

    def test_skips_a_number_taken_by_a_misnamed_file(self):
        """A badly named file still occupies its slot: take the next one, touch nothing."""
        (self.dir / '0002-Bozza Vecchia.md').write_text('x', encoding='utf-8')
        self.run_cli('--slug', 'benchmark-cd4', '--title', 'Benchmark CD4')
        self.assertEqual((self.dir / '0002-Bozza Vecchia.md').read_text(encoding='utf-8'), 'x')
        self.assertTrue((self.dir / '0003-benchmark-cd4.md').exists())
        self.assertIn('[0003]', (self.dir / 'INDICE.md').read_text(encoding='utf-8'))

    def test_rejects_bad_slug_and_pipe_in_title(self):
        with self.assertRaises(ValueError):
            self.run_cli('--slug', 'Benchmark CD4', '--title', 'ok')
        with self.assertRaisesRegex(ValueError, r"cannot contain"):
            self.run_cli('--slug', 'ok-slug', '--title', 'a | b')
        self.assertEqual(len(list(self.dir.glob('0002-*'))), 0)

    def test_template_drift_fails_loudly(self):
        (self.dir / 'TEMPLATE.md').write_text('# CP-NNNN — TITOLO\n\nnothing else\n',
                                              encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'no longer contains'):
            self.run_cli('--slug', 'ok-slug', '--title', 'ok')

    def test_never_overwrites_a_file_a_second_agent_creates_mid_run(self):
        """The reviewer's race: the file appears after our scan, before our write."""
        victim = self.dir / '0002-benchmark-cd4.md'
        original = '# CP-0002 — scritto da un altro agente\n'

        def body(number):
            victim.write_text(original, encoding='utf-8')   # the concurrent creation
            return f'our text for {number}'

        path, number = new_checkpoint.claim(self.dir, 'benchmark-cd4', body)
        self.assertEqual(victim.read_text(encoding='utf-8'), original)
        self.assertEqual((path.name, number), ('0003-benchmark-cd4.md', 3))
        self.assertEqual(path.read_text(encoding='utf-8'), 'our text for 3')

    def test_claim_is_exclusive(self):
        first, _ = new_checkpoint.claim(self.dir, 'primo', lambda n: 'uno')
        second, _ = new_checkpoint.claim(self.dir, 'secondo', lambda n: 'due')
        self.assertEqual([first.name, second.name], ['0002-primo.md', '0003-secondo.md'])
        self.assertEqual(first.read_text(encoding='utf-8'), 'uno')

    def test_a_malformed_index_stops_before_the_checkpoint_is_created(self):
        (self.dir / 'INDICE.md').write_text('# Indice\n\nnessuna tabella\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Elenco'):
            self.run_cli('--slug', 'benchmark-cd4', '--title', 'Benchmark CD4')
        self.assertEqual(list(self.dir.glob('0002-*')), [])

    def test_lock_is_released_even_when_the_run_fails(self):
        lock = self.dir / '.INDICE.lock'
        with self.assertRaises(ValueError):
            self.run_cli('--slug', 'ok-slug', '--title', 'a | b')
        self.assertFalse(lock.exists())
        self.run_cli('--slug', 'ok-slug', '--title', 'ok')
        self.assertFalse(lock.exists())

    def test_a_held_lock_times_out_instead_of_racing(self):
        lock = self.dir / '.INDICE.lock'
        lock.write_text('9999', encoding='utf-8')
        self.addCleanup(lock.unlink, True)
        with self.assertRaisesRegex(TimeoutError, 'still held'):
            with new_checkpoint.file_lock(lock, timeout=0.1):
                pass


class CheckerTests(unittest.TestCase):
    def test_slug_matches_github_anchors(self):
        self.assertEqual(check_docs.slug('### R-001 — `README.md`'), 'r-001--readmemd')
        self.assertEqual(check_docs.slug('## Revisione periodica e pulizia'),
                         'revisione-periodica-e-pulizia')

    def test_tables_are_parsed_with_their_rows(self):
        text = 'intro\n\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\ntail\n'
        (line, header, rows), = check_docs.tables(text)
        self.assertEqual((line, header), (3, ['A', 'B']))
        self.assertEqual(rows, [['1', '2'], ['3', '4']])

    def test_reports_broken_paths_and_anchors(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        (root / 'README.md').write_text(
            'see `reports/gone.json` and [map](docs/PROGETTO.md#assente)\n', encoding='utf-8')
        (root / 'CLAUDE.md').write_text('ok\n', encoding='utf-8')
        (root / 'docs' / 'PROGETTO.md').write_text('# Mappa\n\n## Presente\n', encoding='utf-8')
        (root / 'docs' / 'REGISTRO.md').write_text('# R\n', encoding='utf-8')
        (root / 'docs' / 'DECISIONI.md').write_text('# D\n', encoding='utf-8')
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', root):
            check_docs.check_links(errors)
        self.assertTrue(any('reports/gone.json' in e for e in errors), errors)
        self.assertTrue(any('anchor' in e and 'PROGETTO' in e for e in errors), errors)

        (root / 'README.md').write_text(
            'see `docs/PROGETTO.md` and [map](docs/PROGETTO.md#presente)\n', encoding='utf-8')
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', root):
            check_docs.check_links(errors)
        self.assertEqual(errors, [])

    def test_entry_scope_covers_directories_recursively_and_files_exactly(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'reports' / 'probes' / 'deep').mkdir(parents=True)
        (root / 'docs' / 'sub').mkdir(parents=True)
        (root / 'reports' / 'probes' / 'deep' / 'a.txt').write_text('a', encoding='utf-8')
        (root / 'reports' / 'loose.json').write_text('{}', encoding='utf-8')
        (root / 'docs' / 'sub' / 'nested.md').write_text('x', encoding='utf-8')
        with patch.object(check_docs, 'REPO_ROOT', root):
            errors = []
            check_docs.check_coverage(['`reports/probes/`'], errors)
            reported = ' '.join(errors)
            # the directory entry reaches a file two levels down ...
            self.assertNotIn('deep/a.txt', reported)
            # ... while these two are uncovered, including one in a subdirectory
            self.assertIn('reports/loose.json', reported)
            self.assertIn('docs/sub/nested.md', reported)

            errors = []
            check_docs.check_coverage(
                ['`reports/probes/` `reports/loose.json` `docs/sub/nested.md`'], errors)
            self.assertEqual(errors, [])

    def test_a_file_entry_does_not_cover_its_siblings(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'docs').mkdir()
        (root / 'reports').mkdir()
        (root / 'docs' / 'one.md').write_text('1', encoding='utf-8')
        (root / 'docs' / 'two.md').write_text('2', encoding='utf-8')
        with patch.object(check_docs, 'REPO_ROOT', root):
            errors = []
            check_docs.check_coverage(['`docs/one.md`'], errors)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('docs/two.md', errors[0])

    def test_a_gitignored_artifact_counts_as_present_only_with_its_manifest(self):
        """D-001 keeps data out of the repo: a clone has the manifest, never the .h5ad."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'reports' / 'pilot').mkdir(parents=True)
        (root / '.gitignore').write_text('*.h5ad\n*.py[cod]\n', encoding='utf-8')
        (root / 'reports' / 'pilot' / 'cd4_64.manifest.json').write_text('{}', encoding='utf-8')
        with patch.object(check_docs, 'REPO_ROOT', root):
            # vouched for by the manifest beside it
            self.assertTrue(check_docs.path_exists('reports/pilot/cd4_64.h5ad'))
            # no manifest: still the broken path this check exists to catch
            self.assertFalse(check_docs.path_exists('reports/pilot/other.h5ad'))
            # a suffix .gitignore does not exclude gets no exemption at all
            self.assertFalse(check_docs.path_exists('reports/pilot/cd4_64.json'))

    def test_this_repository_is_consistent(self):
        done = subprocess.run([sys.executable, str(ROOT / 'scripts' / '31_check_docs.py')],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == '__main__':
    unittest.main()
