import sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'hipsci_adapter_r3'))
import qc

class DiagnosticTests(unittest.TestCase):
    def test_native_target_and_unknown_gene_are_distinct(self):
        rows=pd.DataFrame(dict(target=['NTC','A','OFFAXIS','B'],donor_or_clone=['d']*4,condition=['day3']*4,n=[20,20,20,3]))
        values=np.array([[200,200],[40,360],[90,310],[5,20]],float)
        records=qc.diagnose(values,rows,['A','C'],np.ones(2,bool),['A','B'])
        by={r['target']:r for r in records}
        self.assertLess(by['A']['raw'],0)
        self.assertEqual(by['OFFAXIS']['state'],'own_transcript_not_measured')
        self.assertEqual(by['B']['state'],'below_min_cells')
        self.assertFalse(qc.summarize(records)['automatic_context_exclusion'])
    def test_unmeasured_own_gene_does_not_become_zero(self):
        rows=pd.DataFrame(dict(target=['NTC','A'],donor_or_clone=['d']*2,condition=['day3']*2,n=[20,20]))
        result=qc.diagnose(np.array([[0,200],[0,100]],float),rows,['A','C'],np.array([False,True]),['A'])
        self.assertEqual(result[0]['state'],'own_transcript_not_measured')
        self.assertNotIn('raw',result[0])

if __name__=='__main__':unittest.main()
