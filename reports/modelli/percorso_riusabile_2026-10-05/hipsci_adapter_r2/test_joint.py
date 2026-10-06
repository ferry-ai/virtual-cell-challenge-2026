import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'src'))
from vcc2026.multisource import effects_from_pseudobulk
from adapter import prepare, estimate_joint, CALL


class JointTest(unittest.TestCase):
    def inputs(self):
        rows = pd.DataFrame([
            dict(study='hipsci', context=d, donor_or_clone=d, condition='day3',
                 modality='CRISPRi', chemistry='known', target=t, line_group='iPSC', n=n)
            for d,t,n in [('d1','NTC',100),('d1','T',30),('d2','NTC',80),
                          ('d2','T',60),('d3','NTC',120)]])
        counts = np.array([[100.,900.],[80.,220.],[700.,100.],[450.,150.],[50.,1150.]])
        return rows, counts, np.ones(counts.shape,bool)

    def test_control_only_clone_and_exact_joint(self):
        rows, x, mask = self.inputs()
        blocks,_ = prepare(rows,x,mask,['g1','g2'],['T'],{'T':('T',('T',))},unit='hipsci')
        self.assertEqual(len(blocks),3)
        self.assertEqual(blocks[2]['targets'],[])
        actual=estimate_joint(blocks,['T'],effects_from_pseudobulk)
        obs=pd.DataFrame(dict(target=['non-targeting','T','non-targeting','T','non-targeting'],
            donor=['d1','d1','d2','d2','d3'],condition=['day3']*5,n_cells=rows.n))
        expected=effects_from_pseudobulk(x,obs,['g1','g2'],targets=['T'],**CALL)
        for name in ('raw','se','shrunk','n_cells','control_mean'):
            np.testing.assert_array_equal(getattr(actual,name),getattr(expected,name))
        wrong=effects_from_pseudobulk(x[:4],obs.iloc[:4],['g1','g2'],targets=['T'],**CALL)
        self.assertFalse(np.array_equal(actual.control_mean,wrong.control_mean))

    def test_no_unapproved_context_pooling(self):
        rows,x,mask=self.inputs()
        rows.loc[4,'chemistry']='other'
        blocks,_=prepare(rows,x,mask,['g1','g2'],['T'],{'T':('T',('T',))},unit='hipsci')
        with self.assertRaisesRegex(ValueError,'joint source mixes'):
            estimate_joint(blocks,['T'],effects_from_pseudobulk)


if __name__=='__main__':
    unittest.main()
