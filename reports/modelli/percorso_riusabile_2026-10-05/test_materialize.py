"""Tiny actual H5AD -> bank -> persistent sparse samples round trip."""
import gzip
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'ibrido_esecuzione_2026-10-04'))
sys.path.insert(0, str(HERE.parent/'ibrido_pseudobulk_2026-10-04'))
try:
    import psutil
except ImportError:
    sys.modules['psutil'] = SimpleNamespace(virtual_memory=lambda:SimpleNamespace(available=4<<30))
from bank import run_unit, sha
from materialize_samples import run


class MaterializeTests(unittest.TestCase):
    def test_counts_identity_nested_levels_and_raw_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unit = root/'job/shards/cd4_D1_Rest'; unit.mkdir(parents=True)
            x = np.array([[1,1,0,9],[10,0,0,8],[0,2,2,7],[1,3,0,6]],np.float32)
            obs = pd.DataFrame({'study':['fixture']*4,'context':['CD4T D1 Rest']*4,
                'donor_or_clone':['D1']*4,'condition':['Rest']*4,'modality':['CRISPRi']*4,
                'chemistry':['10x']*4,'library':['L']*4,'batch':['B']*4,
                'guides':['c','c','g','g'],'target':['NTC','NTC','T','T'],
                'control_kind':['NTC','NTC','none','none'],'cell_key':list('abcd')},index=list('abcd'))
            var = pd.DataFrame({'official_index':np.arange(4),'mapping':['unique']*4,
                                'measured':[True,True,True,False]},index=list('ABCD'))
            f = unit/'shard.h5ad'; ad.AnnData(sp.csr_matrix(x),obs=obs,var=var).write_h5ad(f)
            mp = unit/'manifest.json'
            mp.write_text(json.dumps({'shards':[{'shard':'shard','bytes':f.stat().st_size,
                                                 'cells':4,'sha256':sha(f)}]}))
            spec = {'name':'D1_Rest','cells':4,'receipt_sha256':'fixture',
                    'parts':[{'job':'job','unit':'cd4_D1_Rest','unit_manifest_sha256':sha(mp)}]}
            bank = root/'bank/D1_Rest'; run_unit(spec,root,bank)
            p = {'unit':'D1_Rest','spec':spec,'bank_receipt_sha256':sha(bank/'complete.json')}
            out = root/'samples/D1_Rest'; run(p,root,out)
            actual = sp.load_npz(out/'shard_00000.npz').toarray()
            x[:,3] = 0
            np.testing.assert_array_equal(actual[:,:4],x)
            with gzip.open(out/'shard_00000.jsonl.gz','rt') as z:
                records = [json.loads(line) for line in z]
            self.assertEqual([r['cell_key'] for r in records],list('abcd'))
            self.assertTrue(all(r['probabilities']=={'32':1.0,'64':1.0,'128':1.0} for r in records))
            self.assertEqual(json.loads((out/'complete.json').read_text())['levels'],{'32':4,'64':4,'128':4})
            with f.open('ab') as z:
                z.write(b'changed')
            with self.assertRaisesRegex(ValueError,'raw shard identity'):
                run(p,root,root/'corrupt_out')


if __name__ == '__main__':
    unittest.main()
