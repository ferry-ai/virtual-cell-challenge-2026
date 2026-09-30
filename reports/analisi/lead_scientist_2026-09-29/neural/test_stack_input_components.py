import unittest
import numpy as np
import audit_stack_input_components as audit


class LossComponentsTest(unittest.TestCase):
    def test_distinguishes_vocabulary_from_common_axis_exclusion(self):
        result,cells=audit.population(np.array([[2,3,5],[4,1,0]]),['A','CONTEXT','OUTMODEL'],
            {'A'},{'A','CONTEXT'},{'A'},{'A'},'toy')
        record=result['loss_components']
        self.assertAlmostEqual(record['fraction_all_counts_outside_model'],5/15)
        self.assertAlmostEqual(record['fraction_all_counts_removed_only_by_other_axis'],4/15)
        self.assertAlmostEqual(record['fraction_model_mappable_counts_removed_only_by_other_axis'],.4)
        self.assertEqual(record['top20_removed_only_by_other_axis'][0]['gene'],'CONTEXT')
        np.testing.assert_allclose(cells.lost_fraction_exact,[.8,.2])


if __name__=='__main__':
    unittest.main()
