import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'src'))
from vcc2026.multisource import effects_from_pseudobulk
import adapter,estimator,policy

class PolicyTest(unittest.TestCase):
    def data(self):
        rows=pd.DataFrame([dict(study='hipsci_targeted_19',context=d,donor_or_clone=d,
            condition='day3',modality='CRISPRi',chemistry='MISSING',line_group='iPSC',target=t,n=n)
            for d,t,n in [('d1','NTC',100),('d1','T',30),('d2','NTC',80),('d2','T',60),
                          ('d3','NTC',120),('d1','UNASSIGNED',500),('MISSING','NO_METADATA',1)]])
        x=np.array([[100.,900.],[80.,220.],[700.,100.],[450.,150.],[50.,1150.],[1.,499.],[0.,1.]])
        return rows,x,np.ones(x.shape,bool)

    def test_native_equivalence_and_preserved_roles(self):
        rows,x,mask=self.data()
        blocks,proof=policy.prepare(rows,x,mask,['g1','g2'],['T'])
        self.assertEqual(len(blocks),3)
        self.assertEqual(len(proof['roles']),7)
        self.assertEqual(proof['cells_by_role']['aux_unassigned'],500)
        self.assertEqual(proof['cells_by_role']['metadata_unresolved'],1)
        actual=adapter.estimate_joint(blocks,['T'],estimator.effects_from_pseudobulk)
        obs=pd.DataFrame(dict(target=rows.target.replace('NTC','non-targeting'),
            donor=rows.donor_or_clone,condition=rows.condition,n_cells=rows.n))
        expected=effects_from_pseudobulk(x,obs,['g1','g2'],targets=['T'],**adapter.CALL)
        for name in ('raw','shrunk','se','n_cells','control_mean'):
            np.testing.assert_array_equal(actual[name],getattr(expected,name))

    def test_unknown_scope_cannot_hide_different_study(self):
        rows,x,mask=self.data()
        rows.loc[0,'study']='other'
        with self.assertRaisesRegex(ValueError,'unexpected study'):
            policy.prepare(rows,x,mask,['g1','g2'],['T'])

if __name__=='__main__':
    unittest.main()
