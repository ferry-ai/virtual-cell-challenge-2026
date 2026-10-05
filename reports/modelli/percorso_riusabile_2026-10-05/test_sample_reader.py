import gzip
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sample_reader import SampleReader,sha


class ReaderTests(unittest.TestCase):
    def fixture(self,root):
        rows = pd.DataFrame({'study':['study']*3,'context':['CD4']*3,'donor_or_clone':['D1']*3,
            'condition':['Rest']*3,'modality':['CRISPRi']*3,'chemistry':['Flex']*3,
            'line_group':['CD4T']*3,'target':['NTC','G1','G2'],'n':[1,1,1]})
        rows.to_csv(root/'bank_rows.csv',index=False)
        np.savez_compressed(root/'mask.npz',value=np.ones((3,3),bool))
        sp.save_npz(root/'shard_00000.npz',sp.csr_matrix(np.eye(3,dtype=np.uint32)))
        with gzip.open(root/'shard_00000.jsonl.gz','wt') as f:
            for i in range(3):
                f.write(json.dumps({'bank_row':i,'cell_key':str(i),'stratum':['L','B',str(i)],
                                    'probabilities':{'32':1,'64':1,'128':1}})+'\n')
        files = {f.name:{'bytes':f.stat().st_size,'sha256':sha(f),'cells':3} for f in root.iterdir()}
        receipt = root/'complete.json'
        receipt.write_text(json.dumps({'complete':True,'unit':'D1_Rest','genes':3,
                                      'bank_receipt_sha256':'bank','files':files}))
        return sha(receipt)

    def test_hidden_target_and_actual_loss_are_separate_from_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);digest=self.fixture(root)
            reader=SampleReader(root,digest,'bank',hidden_targets=['G2'])
            batches=list(reader.batches(1))
            self.assertEqual([b['metadata'].iloc[0].target for b in batches],['NTC','G1'])
            self.assertEqual(reader.exposure()['unique_cells_with_loss'],0)
            for batch in batches:
                reader.acknowledge(batch['batch_id'],[float(batch['metadata'].iloc[0].target!='NTC')])
            e=reader.exposure()
            self.assertEqual(e['unique_cells_with_loss'],1)
            self.assertEqual(e['unique_cells_yielded'],2)
            self.assertEqual(e['physical_rows_decompressed'],3)
            self.assertEqual(e['missing_targets'],[])
            self.assertEqual(e['unacknowledged_batches'],0)

    def test_held_line_does_not_open_count_matrices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);digest=self.fixture(root)
            (root/'shard_00000.npz').write_bytes(b'corrupted but must never be opened')
            reader=SampleReader(root,digest,'bank',held_groups=['CD4T'])
            self.assertEqual(list(reader.batches()),[])
            self.assertEqual(reader.exposure()['physical_rows_decompressed'],0)

    def test_changed_samples_fail_before_yield(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);digest=self.fixture(root)
            reader=SampleReader(root,digest,'bank')
            (root/'shard_00000.npz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact changed'):
                list(reader.batches())


if __name__=='__main__':
    unittest.main()
