"""Mixed donor contexts survive an actual sparse bank/sample round trip."""
import json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
from prepare_archive_derivatives import modules

class ArchiveTest(unittest.TestCase):
 def test_mixed_contexts_and_lineage(self):
  payload=modules();prep=types.ModuleType('preparation');exec(payload['preparation.py'],prep.__dict__)
  bank=types.ModuleType('bank')
  with patch.dict(sys.modules,preparation=prep):exec(payload['bank.py'],bank.__dict__)
  sample=types.ModuleType('materialize_samples')
  with patch.dict(sys.modules,bank=bank):exec(payload['materialize_samples.py'],sample.__dict__)
  try:import psutil
  except ImportError:sys.modules['psutil']=types.SimpleNamespace(virtual_memory=lambda:types.SimpleNamespace(available=32<<30))
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);x=np.array([[1,1,0],[10,0,0],[0,2,2],[1,3,0]],np.uint32)
   obs=pd.DataFrame({'study':['fixture']*4,'context':['T']*4,'donor_or_clone':['D1','D1','D2','D2'],
    'condition':['Rest']*4,'modality':['KO']*4,'chemistry':['10x']*4,'library':['L']*4,
    'batch':['B']*4,'guides':['c','g','c','g'],'target':['NTC','A','NTC','A'],
    'control_kind':['NTC','none','NTC','none'],'cell_key':list('abcd')},index=list('abcd'))
   var=pd.DataFrame({'official_index':[0,1,2],'mapping':['unique']*3,'measured':[True]*3,
    'symbol':list('ABC')},index=list('ABC'))
   raw=root/'raw.h5ad';ad.AnnData(sp.csr_matrix(x),obs=obs,var=var).write_h5ad(raw)
   spec={'name':'fixture','line_group':'CD4T','cells':4,'receipt_sha256':'fixture',
    'axis':list('ABC')+['unused']*(18533-3),
    'files':[{'file':'raw.h5ad','bytes':raw.stat().st_size,'sha256':bank.sha(raw),'cells':4}]}
   b=root/'bank/fixture';bank.run_unit(spec,root,b)
   rows=pd.read_csv(b/'rows.csv');self.assertEqual(set(rows.donor_or_clone),{'D1','D2'})
   self.assertEqual(rows.n.sum(),4)
   out=root/'samples/fixture';sample.run({'unit':'fixture','spec':spec,'bank_input_path':str(b),
    'bank_receipt_sha256':bank.sha(b/'complete.json')},root,out)
   np.testing.assert_array_equal(sp.load_npz(out/'shard_00000.npz').toarray()[:,:3],x)
   self.assertEqual(json.loads((out/'complete.json').read_text())['levels']['64'],4)
   raw.write_bytes(raw.read_bytes()+b'tamper')
   with self.assertRaisesRegex(ValueError,'raw archive changed'):bank.run_unit(spec,root,root/'bad')

if __name__=='__main__':unittest.main()
