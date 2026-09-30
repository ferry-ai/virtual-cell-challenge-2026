"""Synthetic checks only: no real folds, effects or scores are read."""
import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from cluster_pds import losses, pds, resampled_delta, cluster_counts, load_context


class ClusterPDSTest(unittest.TestCase):
    def test_recalculation_equals_expanded_duplicate_panel(self):
        rng = np.random.default_rng(12)
        truth, net, base = [rng.normal(size=(7,11)) for _ in range(3)]
        ln,lb = losses(net,truth),losses(base,truth)
        for w in (np.ones(7,int), np.array([0,2,1,3,0,4,1])):
            ix = np.repeat(np.arange(7),w)
            expanded = (pds(losses(net[ix],truth[ix]))-pds(losses(base[ix],truth[ix]))).mean()
            self.assertAlmostEqual(expanded, resampled_delta(ln,lb,w)[0],places=14)

    def test_zero_prediction_ties_stay_half(self):
        truth = np.arange(20).reshape(5,4)
        ln = losses(np.zeros_like(truth),truth)
        np.testing.assert_array_equal(pds(ln),np.full(5,.5))
        np.testing.assert_array_equal(resampled_delta(ln,ln,[0,1,3,2,0]),[0])

    def test_shared_target_uses_same_weight_in_every_context(self):
        union,w = cluster_counts({'a':['one','two','three'],'b':['four','one','two']},32,7)
        self.assertEqual(union,['four','one','three','two'])
        np.testing.assert_array_equal(w['a'][:,0],w['b'][:,1])
        np.testing.assert_array_equal(w['a'][:,1],w['b'][:,2])

    def test_invalid_panel_fails(self):
        a = np.eye(3)*.5
        with self.assertRaisesRegex(ValueError,'fewer than two'):
            resampled_delta(a,a,[0,1,0])
        with self.assertRaisesRegex(ValueError,'integers'):
            resampled_delta(a,a,[1,.5,1])

    def test_export_roundtrip_reconstructs_mask_truth_and_original_rank(self):
        rng = np.random.default_rng(9)
        raw = rng.normal(size=(3,14)).astype(np.float16)
        arrays = {'raw':raw, 'se':np.ones_like(raw), 'row_target':np.arange(3)}
        raw = raw.astype(np.float32)
        raw -= raw.mean(0).astype(np.float32)
        names = np.array(['NA','two','three'])
        official = np.array([f'g{x}' for x in range(16)])
        response = pd.DataFrame({'gene':official[1:-1],'axis_index':np.arange(1,15)})
        pred = {a:rng.normal(size=(3,14)).astype(np.float32) for a in ('net','transfer','blind')}
        full = {}
        rows = []
        for arm,x in pred.items():
            full[arm] = np.full((3,16),np.nan,np.float32)
            full[arm][:,1:15] = x
            # The own/cis mask is target-specific; the common scoring mask excludes their union.
            for i in range(3):
                full[arm][i,i+1] = np.nan
            ranks = pds(losses(x[:,3:],raw[:,3:]))
            rows.extend({'context':'test','arm':arm,'target':t,'rank':r,'common_genes':11}
                        for t,r in zip(names,ranks))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            np.savez_compressed(path/'pred_test.npz', targets=names, genes=official, **full)
            pd.DataFrame(rows).to_csv(path/'per_target.csv',index=False)
            ts,_,meta = load_context(path,{},'test',[0,1,2],path,(names,response,official),arrays)
            self.assertEqual(ts,names.tolist())
            self.assertEqual(meta['common_genes'],11)
            full['blind'][0,5] = np.nan
            np.savez_compressed(path/'pred_test.npz', targets=names, genes=official, **full)
            with self.assertRaisesRegex(ValueError,'masks differ'):
                load_context(path,{},'test',[0,1,2],path,(names,response,official),arrays)


if __name__ == '__main__':
    unittest.main()
