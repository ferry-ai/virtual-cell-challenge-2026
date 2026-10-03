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

    def test_skips_a_number_another_document_cites(self):
        """A checkpoint cited but never committed keeps its number (R-020, CP-0040)."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        folder = root / 'docs' / 'checkpoints'
        folder.mkdir(parents=True)
        for name in ('TEMPLATE.md', 'INDICE.md', '0001-primo.md'):
            shutil.copy(self.dir / name, folder / name)
        (root / 'reports' / 'x').mkdir(parents=True)
        (root / 'reports' / 'x' / 'R.md').write_text(
            'vedi [CP-0002](../../docs/checkpoints/0002-altra-sessione.md)\n', encoding='utf-8')
        with patch.object(sys, 'argv', ['30_new_checkpoint.py', '--dir', str(folder),
                                        '--slug', 'nuovo', '--title', 'Nuovo']):
            new_checkpoint.main()
        self.assertFalse((folder / '0002-nuovo.md').exists())
        self.assertTrue((folder / '0003-nuovo.md').exists())

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
            'see `docs/PROGETTO.md` and [map](docs/PROGETTO.md#presente); '
            'a template like `reports/trial_<data>/` names no file\n', encoding='utf-8')
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

    def test_an_archived_path_counts_as_existing(self):
        """A path listed in ARCHIVIO.md was moved into a tag, not lost.

        Checkpoints cannot be corrected, so they go on naming what left the tree. The
        archive list separates that from a path that vanished by accident, which must
        still be reported: for backtick paths and for markdown links alike.
        """
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        self.addCleanup(check_docs.archived_paths.cache_clear)
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        (root / 'CLAUDE.md').write_text('ok\n', encoding='utf-8')
        (root / 'docs' / 'PROGETTO.md').write_text('# Mappa\n', encoding='utf-8')
        (root / 'docs' / 'REGISTRO.md').write_text('# R\n', encoding='utf-8')
        (root / 'docs' / 'DECISIONI.md').write_text('# D\n', encoding='utf-8')
        (root / 'README.md').write_text(
            'archiviati `src/orchestrator/engine.py` e `configs/orchestrator/briefs/x.yaml`, '
            'sparito `scripts/99_gone.py`\n', encoding='utf-8')
        (root / 'docs' / 'checkpoints' / '0001-uno.md').write_text(
            'vedi [il contratto](../CICLO.md#3-fasi) e [il perso](../PERSO.md)\n',
            encoding='utf-8')
        (root / 'docs' / 'ARCHIVIO.md').write_text(
            'Restano `src/vcc2026/kept.py` e tutto `reports/`.\n\n'
            '| Percorso | Righe | Nota su `reports/x.json` |\n|---|---|---|\n'
            '| `src/orchestrator/engine.py` | 1143 | vedi `reports/y.json` |\n'
            '| `configs/orchestrator/` | 40 | |\n'
            '| `docs/CICLO.md` | 209 | |\n', encoding='utf-8')
        check_docs.archived_paths.cache_clear()
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', root):
            check_docs.check_links(errors)
            # a directory holding a listed file, and a file under a listed directory
            self.assertTrue(check_docs.path_exists('src/orchestrator/'))
            self.assertTrue(check_docs.path_exists('configs/orchestrator/briefs/x.yaml'))
            self.assertFalse(check_docs.path_exists('src/orchestrator_other/'))
            self.assertFalse(check_docs.path_exists('configs/orchestratore.yaml'))
            # paths named in the prose or in other cells are not archived by being named
            for named in ('src/vcc2026/kept.py', 'reports/gone.json', 'reports/x.json',
                          'reports/y.json'):
                self.assertFalse(check_docs.path_exists(named), named)
        reported = ' '.join(errors)
        for fine in ('engine.py', 'briefs/x.yaml', 'CICLO.md'):
            self.assertNotIn(fine, reported)
        self.assertIn('99_gone.py', reported)
        self.assertIn('PERSO.md', reported)

    def test_a_moved_report_path_is_followed_one_level_down(self):
        """D-046: report folders went into category folders with their names unchanged.

        Checkpoints and reports are never edited, so they go on naming reports/<folder>/;
        the checker finds the folder one level below, for backtick paths and links alike,
        and still reports a path that exists nowhere or twice.
        """
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'reports' / 'invii' / 'trial_x').mkdir(parents=True)
        (root / 'reports' / 'invii' / 'trial_x' / 'status.json').write_text('{}', encoding='utf-8')
        (root / 'reports' / 'storico' / 'twin').mkdir(parents=True)
        (root / 'reports' / 'invii' / 'twin').mkdir(parents=True)
        (root / 'docs' / 'storico').mkdir(parents=True)
        (root / 'docs' / 'storico' / 'VECCHIO.md').write_text('# V\n\n## Sezione\n', encoding='utf-8')
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        (root / 'docs' / 'checkpoints' / '0001-uno.md').write_text(
            'vedi `reports/trial_x/status.json`, [x](../../reports/trial_x/status.json), '
            '[v](../VECCHIO.md#sezione) e [w](../VECCHIO.md#assente)\n', encoding='utf-8')
        for name in ('CLAUDE.md', 'README.md'):
            (root / name).write_text('ok\n', encoding='utf-8')
        for name in ('PROGETTO.md', 'REGISTRO.md', 'DECISIONI.md'):
            (root / 'docs' / name).write_text('# X\n', encoding='utf-8')
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', root):
            self.assertTrue(check_docs.path_exists('reports/trial_x/status.json'))
            self.assertTrue(check_docs.path_exists('reports/trial_x/'))
            self.assertTrue(check_docs.path_exists('docs/VECCHIO.md'))
            self.assertFalse(check_docs.path_exists('reports/trial_y/status.json'))
            self.assertFalse(check_docs.path_exists('reports/twin/'))  # two matches: ambiguous
            check_docs.check_links(errors)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('VECCHIO.md#assente', errors[0])

    def test_a_renamed_document_is_followed_to_its_new_name(self):
        """A live document renamed on purpose keeps its old citations working (ARCHIVIO).

        Checkpoints are never edited, so they go on citing the old name: the checker follows it
        to the new file for backtick paths and links, checks the anchor there, does not count
        the old name as archived, and says the new name with --status. A name that is in no
        table is still an error.
        """
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        self.addCleanup(check_docs.archived_paths.cache_clear)
        self.addCleanup(check_docs.renamed_paths.cache_clear)
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        (root / 'docs' / 'guide').mkdir(parents=True)
        (root / 'docs' / 'PROCEDURE.md').write_text('# Procedure\n\n## 3. Job su Colab\n', encoding='utf-8')
        (root / 'docs' / 'guide' / 'a.md').write_text('# A\n', encoding='utf-8')
        (root / 'docs' / 'ARCHIVIO.md').write_text(
            '# Archivio\n\n| Percorso | Righe |\n|---|---|\n| `src/gone.py` | 3 |\n\n'
            '## Nomi cambiati\n\n| Nome vecchio | Nome nuovo | Dal | Perché |\n|---|---|---|---|\n'
            '| `docs/LAVORO.md` | `docs/PROCEDURE.md` | 30/09/2026 | più chiaro |\n'
            '| `docs/vecchia/` | `docs/guide/` | 30/09/2026 | cartella |\n', encoding='utf-8')
        (root / 'docs' / 'checkpoints' / '0001-uno.md').write_text(
            'vedi `docs/LAVORO.md`, `docs/vecchia/a.md`, [job](../LAVORO.md#3-job-su-colab), '
            '[assente](../LAVORO.md#assente) e [altro](../ALTRO.md)\n', encoding='utf-8')
        (root / 'docs' / 'REGISTRO.md').write_text(
            '# R\n\n| Percorso | Stato | Sostituito da | Nota | Scheda |\n|---|---|---|---|---|\n'
            '| `docs/PROCEDURE.md` | attuale | — | le procedure | — |\n', encoding='utf-8')
        for name in ('CLAUDE.md', 'README.md'):
            (root / name).write_text('ok\n', encoding='utf-8')
        for name in ('PROGETTO.md', 'DECISIONI.md'):
            (root / 'docs' / name).write_text('# X\n', encoding='utf-8')
        check_docs.archived_paths.cache_clear()
        check_docs.renamed_paths.cache_clear()
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', root):
            self.assertEqual(check_docs.renamed('docs/LAVORO.md'), 'docs/PROCEDURE.md')
            self.assertEqual(check_docs.renamed('docs/vecchia/a.md'), 'docs/guide/a.md')
            self.assertIsNone(check_docs.renamed('docs/ALTRO.md'))
            self.assertTrue(check_docs.path_exists('docs/LAVORO.md'))
            self.assertTrue(check_docs.path_exists('docs/vecchia/a.md'))
            self.assertFalse(check_docs.path_exists('docs/vecchia/b.md'))
            self.assertEqual(check_docs.archived_paths(root), frozenset({'src/gone.py'}))
            check_docs.check_links(errors)
            status = check_docs.registry_status('docs/LAVORO.md')
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any('LAVORO.md#assente' in e for e in errors), errors)
        self.assertTrue(any('ALTRO.md' in e for e in errors), errors)
        self.assertIn('renamed: now docs/PROCEDURE.md', status[0])
        self.assertIn('attuale', status[1])

    def test_status_prints_the_covering_entries_the_sheet_and_the_correction(self):
        """An agent asks about one path and gets its row, not the whole registry."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        (root / 'reports' / 'invii' / 'trial_x').mkdir(parents=True)
        (root / 'reports' / 'invii' / 'trial_x' / 'status.json').write_text('{}', encoding='utf-8')
        (root / 'docs' / 'VECCHIO.md').write_text('# V\n', encoding='utf-8')
        (root / 'reports' / 'invii' / 'README.md').write_text(
            '| Data | Cartella | Nocciolo | Vale? |\n|---|---|---|---|\n'
            '| 29/09 | [trial_x/](trial_x/) | una corsa | in parte, vedi CP-0002 |\n', encoding='utf-8')
        (root / 'docs' / 'checkpoints' / '0001-primo.md').write_text('# CP-0001 — Primo\n', encoding='utf-8')
        (root / 'docs' / 'checkpoints' / 'INDICE.md').write_text(
            INDEX.replace('| — |\n', '| [0002](0002-due.md), §3 |\n'), encoding='utf-8')
        (root / 'docs' / 'REGISTRO.md').write_text(
            '# R\n\n| Percorso | Stato | Sostituito da | Nota | Scheda |\n|---|---|---|---|---|\n'
            '| `docs/VECCHIO.md` | superato | `docs/NUOVO.md` | il §2 resta | [R-001](#r-001--docsvecchiomd) |\n'
            '| `docs/checkpoints/` | attuale | — | immutabili | — |\n'
            '| `reports/invii/` | attuale | — | gli invii, Δ e γ | — |\n'
            '| `reports/invii/trial_x/` | storico | — | una corsa | — |\n\n'
            '| Identificatore | Tipo | Stato | Provenienza | Riproducibile con | Nota |\n'
            '|---|---|---|---|---|---|\n'
            '| `C:/dati/effects.npz` | derivato | attuale | stadio 100 | ricetta | effetti |\n\n'
            '### R-001 — `docs/VECCHIO.md`\n', encoding='utf-8')
        with patch.object(check_docs, 'REPO_ROOT', root):
            old = check_docs.registry_status('docs/VECCHIO.md')
            report = check_docs.registry_status('reports/trial_x/status.json')  # the path of before D-046
            checkpoint = check_docs.registry_status('docs/checkpoints/0001-primo.md')
            data = check_docs.registry_status('C:/dati/effects.npz')
            nothing = check_docs.registry_status('docs/ALTRO.md')
        self.assertIn('superato', old[0])
        self.assertTrue(any('replaced by: `docs/NUOVO.md`' in line for line in old), old)
        self.assertTrue(any('R-001' in line and '#r-001--docsvecchiomd' in line for line in old), old)
        self.assertIn('now at reports/invii/trial_x', report[0])
        statuses = [line.split()[0] for line in report if '(entry' in line]
        self.assertEqual(statuses, ['storico', 'attuale'], report)  # the folder itself before its parent
        # the category index keeps its own verdict, printed beside the registry's
        self.assertEqual(report[-1], '  index reports/invii/README.md, Vale?: in parte, vedi CP-0002')
        # a corrected checkpoint says so first, before the registry's 'attuale' of its folder
        self.assertIn('corrected: read [0002](0002-due.md), §3', checkpoint[0])
        self.assertIn('Corretto da', checkpoint[0])
        self.assertIn('attuale', checkpoint[1])
        self.assertIn('attuale', data[0])
        self.assertEqual(nothing, [])

    def test_a_corrected_checkpoint_row_must_name_its_correction(self):
        """A checkpoint's own registry row cannot read 'attuale' without naming who corrected it."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        for name in ('0001-primo.md', '0002-due.md', '0003-tre.md'):
            (root / 'docs' / 'checkpoints' / name).write_text('# CP\n', encoding='utf-8')
        (root / 'docs' / 'checkpoints' / 'INDICE.md').write_text(
            INDEX.replace('| — |\n', '| [0002](0002-due.md), §7 |\n')
            + '| [0002](0002-due.md) | 2026-09-13 | Due | correzione | — |\n'
            + '| [0003](0003-tre.md) | 2026-09-14 | Tre | osservazione | [0002](0002-due.md) |\n',
            encoding='utf-8')
        registry = ('# R\n\n| Percorso | Stato | Sostituito da | Nota | Scheda |\n|---|---|---|---|---|\n'
                    '| `docs/checkpoints/` | attuale | — | la cartella | — |\n'
                    '| `docs/checkpoints/0001-primo.md` | attuale | — | {note} | — |\n'
                    '| `docs/checkpoints/0002-due.md` | attuale | — | la correzione | — |\n'
                    '| `docs/checkpoints/0003-tre.md` | storico | — | un altro stato | — |\n')
        cases = {'il primo': 1, 'il primo, corretto da CP-0002 §7': 0}
        for note, expected in cases.items():
            (root / 'docs' / 'REGISTRO.md').write_text(registry.format(note=note), encoding='utf-8')
            errors = []
            with patch.object(check_docs, 'REPO_ROOT', root):
                check_docs.check_corrected_checkpoints(errors)
            self.assertEqual(len(errors), expected, errors)
            if expected:
                self.assertIn('0001-primo.md', errors[0])
                self.assertIn('0002', errors[0])

    # The loop of docs/STRADE.md (D-055): registry, gate in new protocols, closure in experiment checkpoints.
    ROADS = ('# Strade\n\n| ID | Strada | Esito | Meccanismo | Aggiornata |\n|---|---|---|---|---|\n'
             '| S-001 | Una rete | perde | ipotizzato | 2026-10-04 |\n\n'
             '### S-001 — Una rete\n\n'
             '- **Che cosa si è provato:** una rete\n- **Prova:** un report\n- **Sintomo:** PDS a 0,5\n'
             '- **Meccanismo:** ipotizzato: una parte comune\n- **Che cosa esclude e che cosa no:** questo disegno\n'
             '- **Che cosa la riaprirebbe:** una correzione vincolata\n- **Segnale precoce:** PDS al passo 5.000\n'
             '- **Guardia eseguibile:** nessuna\n')

    def roads_root(self, text=None):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'docs' / 'checkpoints').mkdir(parents=True)
        (root / 'docs' / 'STRADE.md').write_text(self.ROADS if text is None else text, encoding='utf-8')
        return root

    def roads_errors(self, text):
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', self.roads_root(text)):
            ids = check_docs.check_roads(errors)
        return ids, errors

    def test_the_roads_registry_needs_every_field_and_a_mechanism_label(self):
        self.assertEqual(self.roads_errors(None), ({'S-001'}, []))
        _, errors = self.roads_errors(self.ROADS.replace('- **Segnale precoce:** PDS al passo 5.000\n', ''))
        self.assertTrue(any('Segnale precoce' in e for e in errors), errors)
        _, errors = self.roads_errors(self.ROADS.replace('- **Sintomo:** PDS a 0,5\n', '- **Sintomo:**\n'))
        self.assertTrue(any('Sintomo' in e for e in errors), errors)       # a label without text is not a field
        _, errors = self.roads_errors(self.ROADS.replace('| ipotizzato |', '| probabile |'))
        self.assertTrue(any('mechanism not in' in e for e in errors), errors)
        _, errors = self.roads_errors(self.ROADS.replace('**Meccanismo:** ipotizzato', '**Meccanismo:** accertato'))
        self.assertTrue(any('another label' in e for e in errors), errors)  # table and section must agree
        _, errors = self.roads_errors(self.ROADS.replace('**Meccanismo:** ipotizzato: ', '**Meccanismo:** forse '))
        self.assertTrue(any("must start with" in e for e in errors), errors)
        _, errors = self.roads_errors(self.ROADS + '\n### S-002 — Senza riga\n\n- **Prova:** x\n')
        self.assertTrue(any('S-002 has a section but no table row' in e for e in errors), errors)
        _, errors = self.roads_errors(self.ROADS.replace('### S-001 — Una rete', '### Una rete'))
        self.assertTrue(any("no '### S-001" in e for e in errors), errors)
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        errors = []
        with patch.object(check_docs, 'REPO_ROOT', root):
            self.assertEqual(check_docs.check_roads(errors), set())
        self.assertEqual(errors, ['docs/STRADE.md missing'])

    def test_a_new_protocol_must_name_its_precedents_and_its_early_stop(self):
        root = self.roads_root()
        good = ('# Protocollo\n\n## 2. Precedenti\n\nS-001: qui la correzione non può spostare la media.\n\n'
                '**Segnale precoce e arresto:** PDS sui bersagli nascosti al passo 5.000, arresto sotto l\'ancora.\n\n'
                '## 3. Regola\n\nS-999 citata fuori dalla sezione non conta.\n')

        def errors_for(text, folder='rete_nuova_2026-10-05', name='PROTOCOLLO.md'):
            path = root / 'reports' / 'modelli' / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
            errors = []
            with patch.object(check_docs, 'REPO_ROOT', root):
                check_docs.check_protocol_precedents({'S-001'}, errors)
            path.unlink()
            return errors

        self.assertEqual(errors_for(good), [])
        self.assertTrue(any("no '## ... Precedenti' section" in e for e in errors_for('# Protocollo\n\n## 1. Domanda\n')))
        self.assertTrue(any('cites no S-NNN' in e for e in errors_for(good.replace('S-001: ', 'Come le altre: '))))
        self.assertTrue(any('S-777' in e for e in errors_for(good.replace('S-001', 'S-777'))))
        self.assertTrue(any('Segnale precoce e arresto' in e
                            for e in errors_for(good.replace('**Segnale precoce e arresto:**', 'Segnale:'))))
        none = good.replace('S-001: qui la correzione non può spostare la media.',
                            'Nessun precedente pertinente: è il primo studio di questo tipo.')
        self.assertEqual(errors_for(none), [])
        # a protocol written before the gate is not judged by it; another file of the folder is not a protocol
        self.assertEqual(errors_for('# Protocollo\n', folder='rete_vecchia_2026-10-03'), [])
        self.assertEqual(errors_for('# Note\n', name='NOTE.md'), [])
        self.assertTrue(errors_for('# Emendato\n', name='PROTOCOLLO_NN.md'))

    def test_an_experiment_checkpoint_names_the_roads_it_updates(self):
        root = self.roads_root()
        path = root / 'docs' / 'checkpoints' / '0061-esito.md'

        def errors_for(text, number=61, registry=None):
            path.write_text(text, encoding='utf-8')
            if registry is not None:
                (root / 'docs' / 'STRADE.md').write_text(registry, encoding='utf-8')
            errors = []
            with patch.object(check_docs, 'REPO_ROOT', root):
                check_docs.check_checkpoint_roads({number: path}, {'S-001'}, errors)
            return errors

        head = '# CP-0061 — Esito\n\n- **Data:** 2026-10-04\n- **Tipo:** esperimento\n'
        self.assertTrue(any("needs '- **Strade:**" in e for e in errors_for(head)))
        self.assertTrue(any('does not cite CP-0061 back' in e for e in errors_for(head + '- **Strade:** S-001\n')))
        cited = self.ROADS.replace('- **Prova:** un report', '- **Prova:** CP-0061')
        self.assertEqual(errors_for(head + '- **Strade:** S-001\n', registry=cited), [])
        self.assertTrue(any('S-002' in e for e in errors_for(head + '- **Strade:** S-001, S-002\n')))
        self.assertEqual(errors_for(head + '- **Strade:** nessuna: è una replica senza esito nuovo\n'), [])
        template_line = [line for line in TEMPLATE.splitlines() if line.startswith('- **Strade:**')]
        self.assertEqual(len(template_line), 1)                         # the template carries the line...
        self.assertTrue(errors_for(head + template_line[0] + '\n'))     # ...and left as it is, it does not pass
        # older checkpoints and other kinds of checkpoint are not judged
        self.assertEqual(errors_for(head, number=60), [])
        self.assertEqual(errors_for(head.replace('esperimento', 'osservazione')), [])

    def test_this_repository_is_consistent(self):
        done = subprocess.run([sys.executable, str(ROOT / 'scripts' / '31_check_docs.py')],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == '__main__':
    unittest.main()
