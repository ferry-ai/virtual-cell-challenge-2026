import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from population_reader import PopulationReader
from sample_reader import sha


class PopulationTests(unittest.TestCase):
    def test_full_mean_matched_controls_and_explicit_support_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rows=pd.DataFrame({'study':['s']*3,'context':['c']*3,'donor_or_clone':['D1']*3,
                'condition':['Rest']*3,'modality':['CRISPRi']*3,'chemistry':['Flex']*3,
                'line_group':['CD4T']*3,'target':['NTC','G1','G2'],'n':[100,10,20]})
            rows.to_csv(root/'rows.csv',index=False)
            np.savez_compressed(root/'mean_proportion.npz',value=np.array([[1,0,0],[.5,.5,0],[.2,.8,0]],np.float32))
            np.savez_compressed(root/'mask.npz',value=np.array([[True,True,False]]*3))
            np.savez_compressed(root/'sampled_controls.npz',**{'0':np.array([1,0,0])})
            files={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in root.iterdir()}
            receipt=root/'complete.json';receipt.write_text(json.dumps({'complete':True,'rows':3,'cells_used':130,'files':files}))
            digest=sha(receipt)
            reader=PopulationReader(root,digest,hidden_targets=['G2'])
            b=list(reader.batches())
            self.assertEqual(len(b),1)
            self.assertEqual(b[0]['metadata'].target.tolist(),['G1'])
            np.testing.assert_array_equal(b[0]['truth_mean'],[[.5,.5,0]])
            self.assertEqual(b[0]['positive_truth_outside_control_support'].tolist(),[1])
            self.assertEqual(b[0]['cells_control'].tolist(),[100])
            linked=SimpleNamespace(held=set(),hidden={'G2'},rows=reader.rows.copy(),
                receipt={'bank_receipt_sha256':digest,'files':files})
            reader.require_sample_link(linked)
            linked.hidden=set()
            with self.assertRaisesRegex(ValueError,'splits differ'):
                reader.require_sample_link(linked)
            (root/'mean_proportion.npz').write_bytes(b'not opened for held group')
            held=PopulationReader(root,digest,held_groups=['CD4T'])
            self.assertEqual(list(held.batches()),[])


if __name__=='__main__':
    unittest.main()
