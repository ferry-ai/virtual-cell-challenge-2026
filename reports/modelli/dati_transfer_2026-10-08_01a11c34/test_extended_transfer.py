"""Small tests of T3 weighting, singleton contribution, masks and no-change parity."""
import unittest
import numpy as np
from extended_transfer_core import pool_contexts,combine


class TransferTest(unittest.TestCase):
    def test_duplicate_context_does_not_multiply_vote(self):
        c=(np.array([[2.,9.]]),np.array([[True,False]]),np.array([100.]))
        one=pool_contexts([c],(1,2));two=pool_contexts([c,c],(1,2))
        for a,b in zip(one,two): np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(one[1],[[.5,0]])

    def test_singleton_is_not_erased_and_new_pair_is_supported(self):
        group=pool_contexts([(np.array([[2.,3.]]),np.ones((1,2),bool),np.array([100.]))],(1,2))
        effect,weight,ko=combine(np.array([[1.,0.]]),np.array([[1.,0.]]),[group])
        np.testing.assert_allclose(effect,[[1.25/1.125,3.]])
        np.testing.assert_allclose(weight,[[1.125,.125]])

    def test_unobserved_pairs_are_bitwise_unchanged(self):
        core=np.array([[np.pi,np.e],[1/3,2/7]])
        group=(np.ones((2,2)),np.array([[0.,.5],[0.,0.]]))
        effect,_,ko=combine(core,np.ones((2,2)),[group])
        np.testing.assert_array_equal(effect[ko==0],core[ko==0])

    def test_masked_nan_is_not_a_vote_for_zero(self):
        context=(np.array([[np.nan,4.]]),np.array([[False,True]]),np.array([100.]))
        value,rel=pool_contexts([context],(1,2))
        np.testing.assert_array_equal(value,[[0.,4.]])
        np.testing.assert_array_equal(rel,[[0.,.5]])

    def test_invalid_cells_refused(self):
        with self.assertRaises(ValueError):
            pool_contexts([(np.ones((1,1)),np.ones((1,1),bool),np.array([-1.]))],(1,1))


if __name__=='__main__':unittest.main()
