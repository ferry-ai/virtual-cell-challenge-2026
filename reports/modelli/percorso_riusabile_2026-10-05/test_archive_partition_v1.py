"""Partitions equal the unpartitioned moments, masks and nested sample identities."""
import gzip, json, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
from prepare_archive_derivatives import modules
from archive_partition_v1 import partition_bank, zero_population_sample


def load(source, name, dependency=None):
    m=types.ModuleType(name)
    with patch.dict(sys.modules, dependency or {}): exec(source, m.__dict__)
    return m


class PartitionTest(unittest.TestCase):
    def test_equivalent_full_population_and_samples(self):
        try: import psutil
        except ImportError:
            sys.modules['psutil']=types.SimpleNamespace(virtual_memory=lambda:types.SimpleNamespace(available=32 << 30))
        payload=modules(); prep=load(payload['preparation.py'],'preparation')
        full=load(payload['bank.py'],'bank',{'preparation':prep})
        part=load(partition_bank(payload['bank.py'].decode()),'bank',{'preparation':prep})
        samples=load(zero_population_sample(payload['materialize_samples.py'].decode()),
                     'materialize_samples',{'bank':full})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); x=np.array([[1,1,0],[10,0,0],[0,0,0],[0,2,2],[1,3,0],[0,2,0]],np.uint32)
            obs=pd.DataFrame({'study':['fixture']*6,'context':['T']*6,'donor_or_clone':['D1']*3+['D2']*3,
                'condition':['Rest']*6,'modality':['KO']*6,'chemistry':['10x']*6,'library':['L']*6,
                'batch':['B']*6,'guides':['c','g','z','c','g','z'],'target':['NTC','A','B']*2,
                'control_kind':['NTC','none','none']*2,'cell_key':list('abcdef')},index=list('abcdef'))
            var=pd.DataFrame({'official_index':[0,1,2],'mapping':['unique']*3,'measured':[True]*3,
                              'symbol':list('ABC')},index=list('ABC'))
            raw=root/'raw.h5ad'; ad.AnnData(sp.csr_matrix(x),obs=obs,var=var).write_h5ad(raw)
            spec={'name':'fixture','line_group':'CD4T','cells':6,'receipt_sha256':'fixture',
                  'axis':list('ABC')+['unused']*(18533-3),
                  'files':[{'file':'raw.h5ad','bytes':raw.stat().st_size,'sha256':full.sha(raw),'cells':6}]}
            baseline=root/'full'; full.run_unit(spec,root,baseline)
            def selections(path):
                with gzip.open(path/'samples.jsonl.gz','rt') as f:
                    return {json.dumps([s['context'],s['target']],sort_keys=True):s for s in map(json.loads,f)}
            expected=selections(baseline); got={}; rows=[]; receipts=[]
            for i in range(2):
                folder=root/f'p{i}'; part.run_unit({**spec,'partition':{'part':i,'parts':2}},root,folder)
                r=pd.read_csv(folder/'rows.csv'); rows.append(r); receipts.append(json.loads((folder/'complete.json').read_text()))
                selected=selections(folder); self.assertFalse(set(selected)&set(got)); got.update(selected)
                samples.run({'unit':'fixture','spec':spec,'bank_input_path':str(folder),
                             'bank_receipt_sha256':full.sha(folder/'complete.json')},root,root/f's{i}')
                baseline_rows=pd.read_csv(baseline/'rows.csv')
                columns=[*full.BIO,'target']
                positions={tuple(v):j for j,v in enumerate(baseline_rows[columns].itertuples(index=False,name=None))}
                indexes=[positions[tuple(v)] for v in r[columns].itertuples(index=False,name=None)]
                for name in ('count_sum','mean_proportion','variance_proportion','zero_fraction','mask'):
                    with np.load(baseline/(name+'.npz')) as a, np.load(folder/(name+'.npz')) as b:
                        np.testing.assert_array_equal(a['value'][indexes],b['value'])
            self.assertEqual(got,expected)
            self.assertEqual(sum(r['cells_in'] for r in receipts),6)
            self.assertEqual(sum(r['zero_depth_excluded'] for r in receipts),1)
            self.assertEqual(len({r['partition']['all_keys_sha256'] for r in receipts}),1)
            self.assertEqual(pd.concat(rows).n.sum(),5)


if __name__=='__main__': unittest.main()
