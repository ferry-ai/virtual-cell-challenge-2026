import tempfile
from pathlib import Path
import unittest
import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from diagnose_stack_a_failure import aggregate, geometry


class DiagnosticTest(unittest.TestCase):
    def test_noncontiguous_rows_and_different_libraries(self):
        x = np.array([[1, 3], [4, 0], [2, 0], [2, 6]], dtype=np.float32)
        labels = ['A', 'B', 'A', 'B']
        obj = ad.AnnData(sp.csr_matrix(x), obs=pd.DataFrame({'gene': labels}, index=list('abcd')),
                         var=pd.DataFrame(index=['G1', 'G2']))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'x.h5ad'; obj.write_h5ad(path)
            with h5py.File(path) as f:
                genes, stats, sizes = aggregate(f, ['B', 'A'])
        self.assertEqual(genes, ['G1', 'G2'])
        self.assertEqual(sizes, {'cells': [2, 2], 'reads': [12., 6.]})
        for i, target in enumerate(['B', 'A']):
            selected = x[np.array(labels)==target].astype(np.float64)
            normalized = selected/selected.sum(axis=1)[:, None]*1e6
            np.testing.assert_array_equal(stats['counts'][i], selected.sum(axis=0))
            np.testing.assert_allclose(stats['cpm'][i], normalized.mean(axis=0))
            np.testing.assert_allclose(stats['log1p_cpm'][i], np.log1p(normalized).mean(axis=0))
            np.testing.assert_allclose(stats['log1p_cpm_half1'][i], np.log1p(normalized)[0])

    def test_common_and_distinguishing_energy_are_separate(self):
        same = np.array([[1., 2.], [1., 2.]])
        stats = geometry(same)
        self.assertEqual(stats['common_energy_fraction'], 1.)
        self.assertEqual(stats['target_residual_rms'], 0.)
        opposite = geometry(np.array([[1., 0.], [-1., 0.]]))
        self.assertEqual(opposite['common_energy_fraction'], 0.)
        self.assertEqual(opposite['mean_pair_cosine'], -1.)


if __name__ == '__main__':
    unittest.main()
