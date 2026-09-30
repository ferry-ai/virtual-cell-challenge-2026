"""Tiny read-only fixture: historical QC parity, duplicate counts and fail-closed guards."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import scipy.sparse as sp

spec = importlib.util.spec_from_file_location('stream_screen', Path(__file__).with_name('stream_screen.py'))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def write_matrix(path, nf, nb, triples):
    with gzip.open(path, 'wt') as stream:
        stream.write(f'%%MatrixMarket matrix coordinate integer general\n% fixture\n{nf} {nb} {len(triples)}\n')
        for f, b, v in triples:
            stream.write(f'{f} {b} {v}\n')


def fixture(root):
    paths = {}
    arrays = {'transcriptome': (['GENE1', 'GENE2', 'GENE3'],
                               [(1, 1, 7), (1, 1, 3), (2, 1, 2), (1, 2, 5), (3, 2, 2), (2, 3, 3)]),
              'labels': (['untreated_1', 'activated_1'], [(1, 1, 8), (2, 2, 6), (1, 3, 2)]),
              'guides': (['GENE1_a', 'GENE1_b', 'GENE2_a', 'GENE2_b', 'CTRL_a'],
                         [(1, 1, 2), (2, 1, 3), (5, 1, 1), (3, 2, 5), (4, 2, 1)])}
    for name, (axis, entries) in arrays.items():
        matrix, features = root / (name + '.mtx.gz'), root / (name + '.tsv.gz')
        write_matrix(matrix, len(axis), 4, entries)
        with gzip.open(features, 'wt') as f:
            for idx, label in enumerate(axis):
                f.write(f'{idx}\t{label}\n')
        paths[name + '_matrix'], paths[name + '_features'] = matrix, features
    paths['pilot_code'] = root / 'pilot.py'
    paths['pilot_code'].write_text('raise RuntimeError("top level must never execute")\n'
        'def target_of(name):\n'
        '    base = name.rsplit("_", 1)[0]\n'
        '    return "non-targeting" if base.startswith("CTRL") else base\n')
    paths['pilot_code_sha256'] = s.digest(paths['pilot_code'])
    paths['panel_genes'] = ['GENE1', 'GENE2', 'GENE3']
    # Dense reference of the historical pilot equations; independent of chunking.
    totals = np.asarray([12, 7, 3, 0], dtype=float)
    threshold = .1 * np.quantile(np.sort(totals)[::-1][:4], .99)
    old = {'barcodes': 4, 'umi_threshold': threshold, 'cells_by_umi': 3,
           'cells_with_one_label': 2, 'untreated_cells': 1, 'activated_cells': 1,
           'guide_umi_threshold': 1, 'panel_genes_in_features': 3}
    paths['old_qc'] = root / 'old_qc.json'
    paths['old_qc'].write_text(json.dumps(old))
    return paths


class StreamTest(unittest.TestCase):
    def test_chunked_matches_historical_and_no_top_level_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = fixture(root)
            with patch.object(s.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 10 * 2**30})()):
                result = s.extract_channel(paths, root / 'out', expected=4, chunk_size=2)
                self.assertTrue(result['historical_qc_equal'])
                np.testing.assert_array_equal(np.load(root / 'out/counts.npy'), [[10, 2, 0], [5, 0, 2]])
                with np.load(root / 'out/metadata.npz', allow_pickle=False) as meta:
                    self.assertEqual(meta['guide_targets'][-1], 'non-targeting')
                    np.testing.assert_array_equal(meta['barcode_index'], [0, 1])
                    np.testing.assert_array_equal(meta['condition'], [0, 1])
                self.assertEqual(sp.load_npz(root / 'out/guides.npz').nnz, 5)
                with self.assertRaises(FileExistsError):
                    s.extract_channel(paths, root / 'out', expected=4, chunk_size=2)

    def test_bad_axes_entries_and_parser_hash_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = fixture(root)
            with self.assertRaises(ValueError):
                s.load_historical_parser(paths['pilot_code'], '0' * 64)
            malformed = root / 'bad.mtx.gz'
            write_matrix(malformed, 1, 1, [(2, 1, 1)])
            with self.assertRaises(ValueError):
                list(s.triples(malformed, chunk_size=2))
            with gzip.open(malformed, 'wt') as f:
                f.write('%%MatrixMarket matrix coordinate integer general\n1 1 2\n1 1 1\n')
            with self.assertRaises(ValueError):
                list(s.triples(malformed, chunk_size=2))


if __name__ == '__main__':
    unittest.main()
