"""Mechanical H5AD serialization guard around the immutable confirmation pack."""
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import sys

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
import stack_confirmation_pack as pack

PACK_SHA = 'd009261694b2a808dc6c8ab77dacb204f5796eceadd0d69b65b7865221e43f44'


def enable_serialization():
    if hasattr(ad.settings, 'allow_write_nullable_strings'):
        ad.settings.allow_write_nullable_strings = True


def preflight(out):
    if out.exists():
        raise FileExistsError(out)
    enable_serialization()
    out.mkdir(parents=True)
    genes = ['GENE_A', 'GENE_B']
    values = sp.csr_matrix(np.array([[1, 3], [4, 2]], dtype=np.float32))
    obj = ad.AnnData(values, obs=pd.DataFrame({'gene': pd.Series(['non-targeting'] * 2, dtype='string')},
                                             index=pd.Index([0, 1])),
                     var=pd.DataFrame(index=pd.Index(genes, dtype='string')))
    path = out / 'nullable_roundtrip.h5ad'
    obj.write_h5ad(path, compression='gzip')
    actual = ad.read_h5ad(path)
    if list(actual.var_names) != genes or list(actual.obs.gene) != ['non-targeting'] * 2:
        raise ValueError('Nullable H5AD metadata roundtrip differs')
    np.testing.assert_array_equal(actual.X.toarray(), values.toarray())
    pack.pilot.write_json(out / 'manifest.json', {'utc': datetime.now(timezone.utc).isoformat(),
        'status': 'nullable_string_and_counts_roundtrip_passed',
        'allow_write_nullable_strings': getattr(ad.settings, 'allow_write_nullable_strings', None),
        'versions': {name: importlib.metadata.version(name) for name in ['numpy', 'pandas', 'anndata', 'h5py']},
        'frozen_pack_sha256': pack.pilot.sha(pack.__file__),
        'roundtrip_sha256': pack.pilot.sha(path), 'runtime_wrapper_sha256': pack.pilot.sha(__file__)})


def main():
    if pack.pilot.sha(pack.__file__) != PACK_SHA:
        raise ValueError('Original confirmation pack changed')
    enable_serialization()
    if len(sys.argv) == 3 and sys.argv[1] == 'preflight':
        preflight(Path(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] in ('plan', 'prepare'):
        pack.main()
    else:
        raise ValueError('Use preflight <new-directory> or the original plan/prepare CLI')


if __name__ == '__main__':
    main()
