"""Synthetic checks of frozen generalisation, leakage and context usage."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vcc2026.ctj import (Predictor, file_hash, frozen_splits, training_sources,
                         score_targets, paired_bootstrap)
from vcc2026.multisource import AxisTable


def table(name, targets, effects):
    effects = np.asarray(effects, np.float32)
    return AxisTable(name, list(targets), effects.copy(), effects.copy(),
                     np.full_like(effects, .001), np.full(len(targets), 100, np.float32))


class TestCTJ(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        self.genes = [f'g{i}' for i in range(60)]
        g = rng.normal(size=(30, 2))
        g = np.repeat(g, 2, axis=0)
        g[1::2] *= -1
        g, _ = np.linalg.qr(g)
        self.signal = (g @ np.array([[1., .4], [-.3, 2.]]) @ g.T).T.astype(np.float32)
        self.contexts = {'a': 'A', 'b': 'B', 'c': 'C'}
        self.basal = {c: np.ones(60, np.float32) for c in 'ABC'}
        self.sources = {s: table(s, self.genes[:40], self.signal[:40]) for s in 'abc'}

    def test_leakage_all_preprocessing_and_regimes(self):
        for regime in ('C', 'T', 'J'):
            spec = frozen_splits(self.sources, self.contexts, {}, regime, 3, 8)
            split = spec['splits'][0]
            train = training_sources(self.sources, spec, split)
            held = {t for t, f in spec['target_folds'].items() if f == split['fold']}
            for name, tab in train.items():
                self.assertFalse(held.intersection(tab.targets))
                self.assertNotIn(self.contexts[name], split['held_out_contexts'])
                self.assertEqual(tab.meta, {})
            before = Predictor('linear_embedding', self.genes, self.contexts, self.basal, 2).fit(train, 'A')
            changed = {s: table(s, tab.targets, tab.shrunk) for s, tab in self.sources.items()}
            for s, tab in changed.items():
                for i, t in enumerate(tab.targets):
                    if t in held or self.contexts[s] in split['held_out_contexts']:
                        tab.shrunk[i] = 1e6
                        tab.raw[i] = -1e6
                        tab.se[i] = 1e6
            after = Predictor('linear_embedding', self.genes, self.contexts, self.basal, 2).fit(
                training_sources(changed, spec, split), 'A')
            np.testing.assert_array_equal(before.b, after.b)
            np.testing.assert_array_equal(before.g, after.g)
            np.testing.assert_array_equal(before.predict(self.genes, 'A'), after.predict(self.genes, 'A'))

    def test_frozen_hash_and_reuse(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / 'input'
            path.write_bytes(b'original')
            hashes = {'input': file_hash(path)}
            spec = frozen_splits(self.sources, self.contexts, hashes, 'J', 3, 7)
            saved = Path(directory) / 'splits.json'
            saved.write_text(json.dumps(spec))
            self.assertEqual(spec, frozen_splits(self.sources, self.contexts, hashes, 'J', 4, 99, saved))
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Frozen'):
                frozen_splits(self.sources, self.contexts, {'input': file_hash(path)}, 'J', existing=saved)

    def test_null_and_metric_edges(self):
        truth = np.random.default_rng(4).normal(size=(20, 60)).astype(np.float32)
        rows = score_targets(np.zeros_like(truth), truth, np.ones_like(truth),
                             self.genes[:20], self.genes, np.ones(60))
        self.assertEqual(np.mean([r['pds'] for r in rows]), .5)
        self.assertEqual(np.mean([r['mse_ratio'] for r in rows]), 1.)
        missing = score_targets(np.full_like(truth, np.nan), truth, np.ones_like(truth),
                                self.genes[:20], self.genes, np.ones(60))
        self.assertTrue(all(np.isnan(r['pds']) for r in missing))

    def test_transfer_C_and_no_evidence_T(self):
        for regime in ('C', 'T'):
            spec = frozen_splits(self.sources, self.contexts, {}, regime, 3, 8)
            split = spec['splits'][0]
            model = Predictor('transfer', self.genes, self.contexts, self.basal).fit(
                training_sources(self.sources, spec, split), 'A')
            targets = [t for t in self.genes[:40] if regime == 'C' or spec['target_folds'][t] == split['fold']]
            pred = model.predict(targets, 'A')
            if regime == 'C':
                np.testing.assert_allclose(pred, self.signal[:40], atol=1e-7)
            else:
                self.assertTrue(np.isnan(pred).all())

    def test_linear_unseen_target_recovery_and_zero_swap(self):
        # Balanced +/- pairs make the training mean exactly zero.
        for name in ('common', 'linear_embedding'):
            model = Predictor(name, self.genes, self.contexts, self.basal, 2, 1e-9).fit(self.sources, 'A')
            a = model.predict(self.genes[40:], 'A')
            b = model.predict(self.genes[40:], 'B')
            np.testing.assert_array_equal(a, b)
            truth = self.signal[40:]
            sa = score_targets(a, truth, np.full_like(truth, .001), self.genes[40:], self.genes, np.ones(60))
            sb = score_targets(b, truth, np.full_like(truth, .001), self.genes[40:], self.genes, np.ones(60))
            for metric in ('pds', 'reach', 'precision_at_n', 'mse_ratio'):
                stats = paired_bootstrap([r[metric] for r in sa], [r[metric] for r in sb])
                self.assertEqual(stats['difference'], 0.)
                self.assertEqual(stats['low'], 0.)
                self.assertEqual(stats['high'], 0.)
            if name == 'linear_embedding':
                np.testing.assert_allclose(a, truth, atol=2e-6)

    def test_context_signal_and_swap(self):
        v = np.linspace(.1, 3.9, 60, dtype=np.float32)
        basal = {'A': v, 'B': 4-v, 'C': np.full(60, 2, np.float32)}
        sources = {s: table(s, self.genes[:40], self.signal[:40]*(1+basal[c]))
                   for s, c in self.contexts.items()}
        truth = self.signal[40:] * (1+v)
        errors = {}
        for name in ('linear_embedding', 'context_linear'):
            model = Predictor(name, self.genes, self.contexts, basal, 2, 1e-9).fit(sources, 'A')
            a = model.predict(self.genes[40:], 'A')
            b = model.predict(self.genes[40:], 'B')
            errors[name] = np.mean((a-truth)**2)
            delta = paired_bootstrap(np.mean((b-truth)**2, axis=1), np.mean((a-truth)**2, axis=1))
            if name == 'context_linear':
                self.assertGreater(delta['low'], 0.)
                np.testing.assert_allclose(a, truth, atol=3e-6)
            else:
                self.assertEqual(delta['difference'], 0.)
        self.assertLess(errors['context_linear'], errors['linear_embedding']*.001)

    def test_linear_recovers_frozen_T_and_J(self):
        for regime in ('T', 'J'):
            spec = frozen_splits(self.sources, self.contexts, {}, regime, 3, 12)
            for split in spec['splits'][:3]:
                train = training_sources(self.sources, spec, split)
                model = Predictor('linear_embedding', self.genes, self.contexts, self.basal,
                                  2, 1e-9).fit(train, split['context'])
                indices = [i for i, t in enumerate(self.genes[:40])
                           if spec['target_folds'][t] == split['fold']]
                targets = [self.genes[i] for i in indices]
                np.testing.assert_allclose(model.predict(targets, split['context']),
                                           self.signal[indices], atol=3e-6)

    def test_grouped_context_removal(self):
        contexts = dict(self.contexts, b='A')
        spec = frozen_splits(self.sources, contexts, {}, 'C', 3, 1)
        train = training_sources(self.sources, spec, spec['splits'][0])
        self.assertEqual(set(train), {'c'})

    def test_metric_hand_calculation(self):
        truth = np.array([[4., -3., 2., 1.], [-4., 3., -2., -1.]])
        pred = np.array([[4., -3., -2., 1.], [-4., 3., -2., -1.]])
        rows = score_targets(pred, truth, np.full_like(truth, .1), ['a', 'b'],
                             ['x', 'y', 'z', 'w'], np.ones(4), n=3)
        self.assertEqual(rows[0]['pds'], 1.)
        self.assertEqual(rows[0]['reach'], .5)
        self.assertAlmostEqual(rows[0]['precision_at_n'], 2/3)
        self.assertAlmostEqual(rows[0]['mse_ratio'], 16/30)

    def test_bootstrap_seed(self):
        a = np.arange(20.)
        self.assertEqual(paired_bootstrap(a, a/2, 8), paired_bootstrap(a, a/2, 8))
        self.assertNotEqual(paired_bootstrap(a, a/2, 8), paired_bootstrap(a, a/2, 9))

    def test_stage_frozen_outputs_and_refusals(self):
        stage_path = Path(__file__).resolve().parents[1] / 'scripts' / '105_ctj_bench.py'
        loader = importlib.util.spec_from_file_location('ctj_stage', stage_path)
        stage = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(stage)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            (root / 'controls').mkdir()
            pd.DataFrame({'gene_name': self.genes}).to_csv(root / 'controls' / 'gene_names.csv', index=False)
            cache = root / 'cache'
            cache.mkdir()
            for name, tab in self.sources.items():
                np.savez(cache / f'{name}.npz', targets=tab.targets, raw=tab.raw,
                         shrunk=tab.shrunk, se=tab.se, n_cells=tab.n_cells, meta='{}')
            basal = root / 'basal.csv'
            pd.DataFrame(dict(gene_name=self.genes, **self.basal)).to_csv(basal, index=False)
            base = [str(stage_path), '--cache', str(cache), '--basal', str(basal),
                    '--folds', '2', '--k', '2', '--bootstrap', '20']
            for name, context in self.contexts.items():
                base += ['--context-column', f'{name}={context}']
            original_fit = Predictor.fit
            for regime in ('C', 'T', 'J'):
                out = root / regime
                def checked_fit(model, train, context):
                    self.assertTrue((out / 'splits.json').exists())
                    return original_fit(model, train, context)
                argv = base + ['--regime', regime, '--out', str(out)]
                with patch.object(stage, 'paths', return_value=SimpleNamespace(raw=root)), \
                    patch.object(stage, 'official_axis', return_value=SimpleNamespace(symbols=self.genes)), \
                        patch.object(sys, 'argv', argv), patch.object(Predictor, 'fit', checked_fit):
                    stage.main()
                for filename in ('splits.json', 'summary.csv', 'per_target.csv', 'comparisons.csv', 'measurements.json'):
                    self.assertTrue((out / filename).is_file())
                with patch.object(sys, 'argv', argv):
                    with self.assertRaises(FileExistsError):
                        stage.main()
            first = root / 'T'
            replay = root / 'replay'
            argv = base + ['--regime', 'T', '--out', str(replay), '--seed', '999',
                           '--splits', str(first / 'splits.json')]
            with patch.object(stage, 'paths', return_value=SimpleNamespace(raw=root)), \
                    patch.object(stage, 'official_axis', return_value=SimpleNamespace(symbols=self.genes)), \
                    patch.object(sys, 'argv', argv):
                stage.main()
            for filename in ('splits.json', 'per_target.csv', 'summary.csv', 'comparisons.csv'):
                self.assertEqual((first / filename).read_bytes(), (replay / filename).read_bytes())
            basal.write_text(basal.read_text() + '\n')
            argv[argv.index(str(replay))] = str(root / 'refused')
            with patch.object(stage, 'paths', return_value=SimpleNamespace(raw=root)), \
                    patch.object(stage, 'official_axis', return_value=SimpleNamespace(symbols=self.genes)), \
                    patch.object(sys, 'argv', argv), patch.object(Predictor, 'fit') as fit:
                with self.assertRaisesRegex(ValueError, 'Frozen'):
                    stage.main()
                fit.assert_not_called()

    def test_stage_source_selection(self):
        stage_path = Path(__file__).resolve().parents[1] / 'scripts' / '105_ctj_bench.py'
        loader = importlib.util.spec_from_file_location('ctj_stage_sources', stage_path)
        stage = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(stage)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            (root / 'controls').mkdir()
            pd.DataFrame({'gene_name': self.genes}).to_csv(root / 'controls' / 'gene_names.csv', index=False)
            cache = root / 'cache'
            cache.mkdir()
            for name, tab in list(self.sources.items()) + [('extra', next(iter(self.sources.values())))]:
                np.savez(cache / f'{name}.npz', targets=tab.targets, raw=tab.raw,
                         shrunk=tab.shrunk, se=tab.se, n_cells=tab.n_cells, meta='{}')
            basal = root / 'basal.csv'
            pd.DataFrame(dict(gene_name=self.genes, **self.basal)).to_csv(basal, index=False)
            base = [str(stage_path), '--cache', str(cache), '--basal', str(basal), '--regime', 'C',
                    '--folds', '2', '--k', '2', '--bootstrap', '20']
            for name, context in self.contexts.items():
                base += ['--context-column', f'{name}={context}']
            runs = [(base + ['--out', str(root / 'all')], 'context mapping'),
                    (base + ['--sources', 'nope', '--out', str(root / 'unknown')], 'not in the cache'),
                    (base + ['--sources', *self.sources, '--out', str(root / 'chosen')], None)]
            for argv, error in runs:
                with patch.object(stage, 'paths', return_value=SimpleNamespace(raw=root)), \
                        patch.object(stage, 'official_axis', return_value=SimpleNamespace(symbols=self.genes)), \
                        patch.object(sys, 'argv', argv):
                    if error is None:
                        stage.main()
                    else:
                        with self.assertRaisesRegex(ValueError, error):
                            stage.main()
            spec = json.loads((root / 'chosen' / 'splits.json').read_text(encoding='utf-8'))
            self.assertEqual(spec['sources'], sorted(self.sources))
            self.assertNotIn('extra.npz', spec['hashes'])

    def test_stage_help(self):
        stage = Path(__file__).resolve().parents[1] / 'scripts' / '105_ctj_bench.py'
        run = subprocess.run([sys.executable, str(stage), '--help'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('--splits', run.stdout)


if __name__ == '__main__':
    unittest.main()
