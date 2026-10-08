"""Check the scientific averaging order, missingness and split invariance."""
import unittest
import json
import os
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from common_stream import mixed_common,single_common,sha
import cd4_common_runtime


def stream(items):
    for target,value,n in items:
        value=np.array(value,float);yield target,value,np.isfinite(value),n


class Common(unittest.TestCase):
    def test_mix_targets_before_mean_not_mean_conditions(self):
        a=[('A',[1,np.nan,4],100),('B',[9,2,np.nan],100)]
        b=[('A',[5,6,np.nan],300),('C',[3,np.nan,8],100)]
        result,receipt=mixed_common([stream(a),stream(b)],3)
        oracle=np.array([((.5*1+.75*5)/1.25+9+3)/3,(6+2)/2,(4+8)/2])
        np.testing.assert_allclose(result['common'],oracle)
        np.testing.assert_array_equal(result['contributing_targets'],[3,2,2])
        self.assertEqual(receipt['targets'],3)
        condition_mean=(np.nanmean(np.array([x[1] for x in a]),axis=0)+np.nanmean(np.array([x[1] for x in b]),axis=0))/2
        self.assertGreater(np.linalg.norm(result['common']-condition_mean),.1)

    def test_one_stream_equal_target_mean_and_missing_zero_mask(self):
        entries=[('A',[2,np.nan],20),('B',[4,np.nan],1000)]
        a,_=single_common(stream(entries),2);b,_=mixed_common([stream(entries)],2)
        np.testing.assert_allclose(a['common'],[3,0]);np.testing.assert_array_equal(a['mask'],[True,False])
        np.testing.assert_allclose(a['common'],b['common'])

    def test_cloud_entry_verifies_frozen_chunks_and_writes_complete_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'input';inputs.mkdir();work=root/'work';work.mkdir()
            genes=['g1','g2'];pd.DataFrame({'gene':genes}).to_csv(work/'gene_names.csv',index=False)
            split=dict(regime='production',hidden_targets=[]);conditions=[]
            for i in range(3):
                path=inputs/(str(i)+'.npz');values=np.array([[i+1,np.nan]],np.float32)
                np.savez_compressed(path,genes=genes,targets=['A'],shrunk=values,mask=np.isfinite(values),n_cells=[100])
                conditions.append(dict(split=split,chunks=[dict(bytes=path.stat().st_size,sha256=sha(path))]))
            (work/'params.json').write_text(json.dumps(dict(embedded={},split=split,conditions=conditions)))
            previous=Path.cwd()
            try:
                os.chdir(work);cd4_common_runtime.main(input_root=inputs,ram_available=1<<30)
            finally:os.chdir(previous)
            done=json.loads((work/'complete.json').read_text());receipt=json.loads((work/'common_receipt.json').read_text())
            self.assertEqual(done['receipt_sha256'],sha(work/'common_receipt.json'))
            self.assertEqual(receipt['output']['sha256'],sha(work/'cd4_mix_common.npz'))
            with np.load(work/'cd4_mix_common.npz') as z:
                np.testing.assert_array_equal(z['common'],[2,0]);np.testing.assert_array_equal(z['mask'],[True,False])


if __name__=='__main__':unittest.main()
