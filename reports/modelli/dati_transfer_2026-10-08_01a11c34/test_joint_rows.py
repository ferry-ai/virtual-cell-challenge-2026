import unittest
import numpy as np
import pandas as pd
from joint_rows import joint,UNITS


def bank(study,donor,context,condition='Rest',control=(8,5,4)):
    records=[dict(study=study,line_group='X',context=context,donor_or_clone=donor,
        condition=condition,modality='CRISPRi',chemistry='x',target=t,n=20,bank_row=i)
        for i,t in enumerate(['non-targeting','A'])]
    return dict(frame=pd.DataFrame(records),counts=np.array([control,[2,7,8]]),masks=np.ones((2,3),bool))


class Joint(unittest.TestCase):
    def test_h1_duplicate_controls_and_disjoint_targets(self):
        banks={u:bank(u,'UNREPORTED@'+u,'H1',condition='UNREPORTED@'+u) for u in UNITS['h1']}
        banks['h1_val']['frame'].loc[1,'target']='B'
        f,x,m,r=joint('h1',banks,['a','b','c'])
        self.assertEqual(len(f),3);self.assertEqual(r['duplicate_control_rows_dropped'],1)
        self.assertEqual(r['admitted_cells_after_dedup'],60)
        banks['h1_val']['counts'][0,0]+=1
        with self.assertRaisesRegex(ValueError,'not identical'):joint('h1',banks,['a','b','c'])

    def test_storage_blocks_sum_counts_and_intersect_masks(self):
        banks={u:bank('k562','unknown','K562') for u in UNITS['k562_gwps']}
        banks['k562_gwps_b']['masks'][1,0]=False
        f,x,m,r=joint('k562_gwps',banks,['a','b','c'])
        np.testing.assert_array_equal(x[[1]],[[0,14,16]])
        np.testing.assert_array_equal(m[[1]],[[False,True,True]])
        self.assertEqual(f.iloc[1].n,40)

    def test_cd4_retains_four_donors_and_three_conditions(self):
        banks={u:bank('cd4',u.split('_')[0],u,condition=u.split('_')[1]) for u in UNITS['cd4']}
        f,x,m,r=joint('cd4',banks,['a','b','c'])
        self.assertEqual(len(f),24);self.assertEqual(f.context.nunique(),3)
        self.assertEqual(f.donor_or_clone.nunique(),4)
        np.testing.assert_array_equal(x[[0,2]],np.array([[8,5,4],[8,5,4]]))
        banks.pop('D4_Rest')
        with self.assertRaisesRegex(ValueError,'complete pooling'):joint('cd4',banks,['a','b','c'])

    def test_h1_overlap_cannot_be_silently_added(self):
        banks={u:bank(u,'UNREPORTED@'+u,'H1',condition='UNREPORTED@'+u) for u in UNITS['h1']}
        with self.assertRaisesRegex(ValueError,'overlapping'):joint('h1',banks,['a','b','c'])


if __name__=='__main__':unittest.main()
