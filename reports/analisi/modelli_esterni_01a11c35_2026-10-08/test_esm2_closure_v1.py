"""Mask and single-amplitude tests for the frozen ESM2 fallback contract."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from esm2_closure_adapter_v1 import fallback
from pie_adapter import sha256


class ClosureTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def file(self,name,values,mask):
        p=self.root/name
        np.savez_compressed(p,targets=['t1','t2'],genes=['g1','g2'],lfc=np.array(values,np.float32),observed=np.array(mask,bool))
        return dict(path=str(p),bytes=p.stat().st_size,sha256=sha256(p))
    def test_full_support_copies_t0_byte_for_byte(self):
        a=self.file('a.npz',[[2,3],[4,5]],[[1,1],[1,1]])
        b=self.file('b.npz',[[9,8],[7,6]],[[1,1],[1,1]])
        result=fallback(a,b,self.root/'out.npz',1.576)
        self.assertTrue(result['byte_parity_t0']);self.assertEqual(result['changed_pairs'],0)
    def test_pair_fallback_keeps_cis_and_applies_gain_once(self):
        a=self.file('a.npz',[[20,0],[4,5]],[[1,0],[1,1]])
        b=self.file('b.npz',[[9,8],[7,6]],[[1,1],[1,1]])
        result=fallback(a,b,self.root/'out.npz',1.576)
        with np.load(self.root/'out.npz') as source:
            np.testing.assert_array_equal(source['lfc'],np.array([[20,8*1.576],[4,5]],np.float32))
        self.assertEqual(result['fallback_pairs'],1);self.assertEqual(result['full_row_fallback_targets'],0)
        self.assertFalse(result['cis_reapplied']);self.assertFalse(result['emission_scale_applied'])


if __name__=='__main__':unittest.main()
