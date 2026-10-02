"""Smoke test of the P4 network on the synthetic cube: it runs end to end, never fits on the held-out group,
and writes one record per (target, arm). Tiny steps: this proves the code path, not the model."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from test_p3_synthetic import HERE, protocol, write_cube


class TestNetworkSmoke(unittest.TestCase):
    def test_runs_without_reading_the_held_out_group(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cube = tmp / 'cube'
            write_cube(cube, 0.8)
            coords = tmp / 'coords.tsv'
            pd.DataFrame(dict(symbol=['X'], gene_id=['ENSG0'])).to_csv(coords, sep='\t', index=False)
            proto = tmp / 'proto.json'
            protocol(proto, coords)
            run = tmp / 'run'
            done = subprocess.run([sys.executable, str(HERE / 'p3_run.py'), '--cube', str(cube), '--protocol', str(proto),
                                   '--out', str(run)], cwd=HERE, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr[-2000:])
            nn_proto = json.loads((HERE.parents[2] / 'reports/analisi/generalizzazione_contesti_2026-10-02/p4/PROTOCOLLO_NN.json')
                                  .read_text(encoding='utf-8'))
            nn_proto['parameters'].update(n_fit=100, step_grid=[10, 20], batch_rows=8, batch_genes=32, basis_k=4,
                                          pds_block=60, gene_coordinates=str(coords))
            nn_path = tmp / 'nn_proto.json'
            nn_path.write_text(json.dumps(nn_proto), encoding='utf-8')
            out = tmp / 'nn'
            done = subprocess.run([sys.executable, str(HERE / 'nn_residual.py'), '--cube', str(cube), '--gm-cache',
                                   str(run / 'gm_cache'), '--protocol', str(nn_path), '--out', str(out),
                                   '--groups', 'A', 'B'], cwd=HERE, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr[-3000:])
            meta = json.loads((out / 'run.json').read_text(encoding='utf-8'))
            for g, chk in meta['leak_checks'].items():
                self.assertEqual(chk['fit_reads_of_held_group'], [], g)
            rec = pd.read_csv(out / 'per_target_C_A.csv.gz')
            self.assertEqual(set(rec.arm), {'nn0', 'nn', 'nn_swap', 'nn_null1', 'nn_null2', 'nn_null3'})


if __name__ == '__main__':
    unittest.main()
