"""Tiny official query fixture: native normalization and metadata-only rejection."""
import tempfile
from pathlib import Path
import unittest
import h5py
import numpy as np
import scipy.sparse as sp
from official_ntc_worker import extract
from ntc_cells import BIO,sha,normalized_batch

class OfficialTest(unittest.TestCase):
    def test_query_native_depth_and_perturbed_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'control.h5ad'
            with h5py.File(path,'w') as h:
                obs=h.create_group('obs');var=h.create_group('var');string=h5py.string_dtype()
                obs.create_dataset('_index',data=['c1','c2','c3'],dtype=string)
                obs.create_dataset('ntc_id',data=['g1','g1','g2'],dtype=string)
                obs.create_dataset('target_gene',data=['non-targeting']*3,dtype=string)
                var.create_dataset('_index',data=['G1','G2'],dtype=string)
                x=h.create_group('X');x.attrs['encoding-type']='csr_matrix'
                sparse=sp.csr_matrix([[2,8],[4,16],[3,7]])
                for key in ('data','indices','indptr'):x.create_dataset(key,data=getattr(sparse,key))
            plan=dict(source=dict(bytes=path.stat().st_size,sha256=sha(path),cells=3),
                identity={k:'MISSING' for k in BIO},genes=['G1','G2'],seed='test',context_id='A',part_id='official_A',cells_per_stratum=1)
            bundle=extract(path,plan);value,mask=normalized_batch(bundle,np.arange(2))
            self.assertEqual(bundle['counts'].shape,(2,2));self.assertTrue(mask.all())
            np.testing.assert_allclose(value[0],np.log1p([2000,8000]),rtol=1e-6)
            with h5py.File(path,'r+') as h:h['obs/target_gene'][0]='G1'
            plan['source'].update(bytes=path.stat().st_size,sha256=sha(path))
            with self.assertRaisesRegex(ValueError,'non-control'):extract(path,plan)

if __name__=='__main__':unittest.main()
