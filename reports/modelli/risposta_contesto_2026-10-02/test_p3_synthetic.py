"""Positive and negative controls of the whole P3 chain (cube layout -> p3_run -> decide) on synthetic data.

A synthetic cube of five line groups is written in the layout of cube.py. In the positive control the
response of every gene is scaled by its expression in the line relative to the other lines
(beta = 0.8): only an arm that reads the held-out controls can recover it. In the negative control
beta = 0. The test checks that the frozen rule detects the planted context and does not invent one,
and that the leak audit holds. It says nothing about real data.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
GROUPS = {'A': ['a1', 'a2'], 'B': ['b1'], 'C': ['c1'], 'D': ['d1'], 'E': ['e1']}


def write_cube(folder: Path, beta: float, seed: int = 3) -> None:
    rng = np.random.default_rng(seed)
    n_genes, n_keys = 80, 160
    genes = [f'G{i:02d}' for i in range(n_genes)]
    keys = [f'K{i:03d}' for i in range(n_keys)]
    symbols = {k: genes[i % n_genes] for i, k in enumerate(keys)}
    mu = rng.uniform(0.5, 5.0, n_genes)
    shift = {g: rng.normal(0, 1.0, n_genes) for g in GROUPS}
    basal = {}
    for g, ts in GROUPS.items():
        for t in ts:
            basal[t] = np.clip(mu + shift[g] + rng.normal(0, 0.1, n_genes), 0.05, None).astype(np.float32)
    xbar = np.mean([np.mean([basal[t] for t in ts], 0) for ts in GROUPS.values()], 0)
    effect = np.zeros((n_keys, n_genes))
    for i in range(n_keys):
        idx = rng.choice(n_genes, 25, replace=False)
        effect[i, idx] = rng.normal(0, 1.0, 25)
    folder.mkdir(parents=True)
    tables = {}
    for g, ts in GROUPS.items():
        common = rng.normal(0, 0.05, n_genes)
        for t in ts:
            present = rng.random(n_keys) < 0.75
            y = effect * (1 + beta * (basal[t] - xbar))[None, :] + common[None, :]
            y = y + rng.normal(0, 0.05, y.shape)
            y = y[present].astype(np.float16)
            (folder / t).mkdir()
            np.save(folder / t / 'raw.npy', y)
            np.save(folder / t / 'shrunk.npy', (0.9 * y.astype(np.float32)).astype(np.float16))
            np.save(folder / t / 'se.npy', np.full(y.shape, 0.05, np.float16))
            ks = [k for k, p in zip(keys, present) if p]
            pd.DataFrame(dict(target_key=ks, target=[symbols[k] for k in ks], n_cells=100,
                              duplicate_of_key=False)).to_csv(folder / t / 'rows.csv', index=False)
            tables[t] = dict(rows=len(ks), group=g)
    np.savez(folder / 'basal.npz', **{t: np.log1p(np.expm1(v)) for t, v in basal.items()})
    pd.Series(genes, name='gene').to_csv(folder / 'genes.csv', index=False)
    pd.DataFrame(dict(target_key=keys, stratum='essential', groups=5)).to_csv(folder / 'keys.csv', index=False)
    (folder / 'manifest.json').write_text(json.dumps(dict(tables=tables)), encoding='utf-8')


def protocol(path: Path, coords: Path) -> None:
    base = json.loads((HERE.parents[2] / 'reports/analisi/generalizzazione_contesti_2026-10-02/PROTOCOLLO.json')
                      .read_text(encoding='utf-8'))
    base['parameters'].update(n_fit=120, m2_k_grid=[4], m2_d_grid=[1], m2_ridge_grid=[0.1], pds_block=60,
                              gene_coordinates=str(coords))
    path.write_text(json.dumps(base), encoding='utf-8')


def run_chain(tmp: Path, beta: float) -> dict:
    cube = tmp / f'cube_{beta}'
    write_cube(cube, beta)
    coords = tmp / 'coords.tsv'
    pd.DataFrame(dict(symbol=['X'], gene_id=['ENSG0'])).to_csv(coords, sep='\t', index=False)
    proto = tmp / 'proto.json'
    protocol(proto, coords)
    run = tmp / f'run_{beta}'
    out = tmp / f'decision_{beta}'
    runj = tmp / f'runj_{beta}'
    for cmd in ([sys.executable, str(HERE / 'p3_run.py'), '--cube', str(cube), '--protocol', str(proto),
                 '--out', str(run)],
                [sys.executable, str(HERE / 'p3_run_j.py'), '--cube', str(cube), '--protocol', str(proto),
                 '--out', str(runj), '--folds', '0', '--max-train-keys', '120', '--fit-keys-per-group', '60'],
                [sys.executable, str(HERE / 'decide.py'), '--run', str(run), '--protocol', str(proto),
                 '--out', str(out)]):
        done = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        if done.returncode:
            raise RuntimeError(f'{cmd[1]} failed:\n{done.stderr[-3000:]}')
    return dict(decision=json.loads((out / 'decision.json').read_text(encoding='utf-8')),
                run=json.loads((run / 'run.json').read_text(encoding='utf-8')),
                fits=json.loads((run / 'fits.json').read_text(encoding='utf-8')),
                runj=json.loads((runj / 'run.json').read_text(encoding='utf-8')))


class TestSyntheticControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        cls.pos = run_chain(tmp, 0.8)
        cls.neg = run_chain(tmp, 0.0)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_planted_context_is_detected(self):
        m1 = self.pos['decision']['regimes']['C']['context']['m1']
        self.assertTrue(m1['passed'], m1)
        self.assertEqual(self.pos['decision']['regimes']['C']['outcome'], 'context_benefit')

    def test_no_context_is_not_invented(self):
        m1n = self.neg['decision']['regimes']['C']['context']['m1']
        m1p = self.pos['decision']['regimes']['C']['context']['m1']
        self.assertLess(abs(m1n['delta_ctx_macro']), 0.25 * m1p['delta_ctx_macro'])

    def test_no_fit_read_a_held_out_table(self):
        for res in (self.pos, self.neg):
            for g, chk in res['run']['leak_checks'].items():
                self.assertEqual(chk['fit_reads_of_held_group'], [], g)
            for name, chk in res['runj']['leak_checks'].items():
                self.assertEqual(chk['fit_reads_of_held_group'], [], name)

    def test_inner_selection_never_sees_the_validation_group(self):
        for res in (self.pos, self.neg):
            for g, fit in res['fits'].items():
                for v, audit in fit['inner_audit'].items():
                    self.assertNotIn(v, audit['basis_and_pca_groups'])
                    self.assertNotIn(g, audit['basis_and_pca_groups'])
                    for h, sources in audit['transfer_sources'].items():
                        self.assertNotIn(v, sources)
                        self.assertNotIn(h, sources)
                        self.assertNotIn(g, sources)
                    self.assertNotIn(v, audit['validation_transfer_sources'])


if __name__ == '__main__':
    unittest.main()
