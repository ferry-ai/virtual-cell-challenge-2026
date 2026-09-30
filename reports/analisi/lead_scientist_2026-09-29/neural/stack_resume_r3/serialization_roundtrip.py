import json, sys
from pathlib import Path
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
ad.settings.allow_write_nullable_strings = True
out = Path(sys.argv[1])
out.mkdir()
results = []
for arm, values in [('transfer', [[0, 3, 4], [5, 0, 6]]), ('stack', [[7, 1, 0], [0, 2, 8]])]:
    x = sp.csr_matrix(values, dtype=np.float32)
    obs = pd.DataFrame({'gene': pd.array(['TEST_A', 'TEST_B'], dtype='string')}, index=['c0', 'c1'])
    var = pd.DataFrame(index=pd.Index(pd.array(['G_B', 'G_A', 'G_C'], dtype='string'), name=None))
    obj = ad.AnnData(x, obs=obs, var=var)
    path = out / f'prediction_{arm}.h5ad'
    obj.write_h5ad(path, compression='gzip')
    restored = ad.read_h5ad(path)
    np.testing.assert_array_equal(restored.X.toarray(), x.toarray())
    assert list(restored.var_names) == ['G_B', 'G_A', 'G_C']
    assert restored.obs.gene.astype(str).tolist() == ['TEST_A', 'TEST_B']
    assert str(obj.var.index.dtype) == 'string'
    results.append({'arm': arm, 'counts_exact': True, 'axis_exact': True, 'labels_exact': True})
print(json.dumps({'setting': 'anndata.settings.allow_write_nullable_strings=True', 'anndata': ad.__version__, 'roundtrips': results}))
