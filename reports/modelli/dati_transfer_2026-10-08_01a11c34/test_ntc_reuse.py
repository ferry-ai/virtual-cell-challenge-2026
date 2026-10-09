"""Small checks of cache identity and metadata-only native-depth recovery."""
import copy
from pathlib import Path
import tempfile
import unittest
import h5py
from ntc_reuse_catalog import cache_identity, decision
from ntc_depth_metadata import recover_depth
from ntc_cells import BIO, STRATA


class ReuseTests(unittest.TestCase):
    def test_cache_is_location_independent_but_science_sensitive(self):
        plan = dict(sources=[dict(sha256='a', file='old.h5ad')], rows=dict(sha256='b',path='old.csv'),
            controls=[dict(context_id='c',expected_cells=2)], genes=['G1'],seed='s',cells_per_stratum=64,
            stratum_columns=list(STRATA),preserve_columns=list(BIO),denominator='depth_native')
        code = {'ntc_cells.py':'reader1','run_ntc_extraction.py':'extractor1'}
        key = cache_identity(plan,code)
        moved = copy.deepcopy(plan); moved['sources'][0]['file']='new.h5ad'; moved['rows']['path']='new.csv'
        self.assertEqual(key,cache_identity(moved,code))
        for field,value in [('seed','s2'),('cells_per_stratum',32),('genes',['G2']),('denominator','aligned_sum')]:
            changed=copy.deepcopy(plan); changed[field]=value
            self.assertNotEqual(key,cache_identity(changed,code))
        self.assertNotEqual(key,cache_identity(plan,{**code,'ntc_cells.py':'reader2'}))

    def test_ready_and_running_never_request_new_extraction(self):
        self.assertEqual(decision(dict(status='COMPLETE_METADATA_VERIFIED'),True),'REUSE_AFTER_CONSUMER_HASH_CHECK')
        self.assertEqual(decision(None,True),'AWAIT_ACTIVE_PRODUCER')
        self.assertEqual(decision(None,False),'NEEDS_TRIAGE_NO_AUTOMATIC_EXTRACTION')
        with self.assertRaises(ValueError): decision(dict(status='PARTIAL'),False)

    def test_depth_recovered_without_any_X_dataset(self):
        with tempfile.TemporaryDirectory() as temp:
            with h5py.File(Path(temp)/'metadata.h5','w') as h5:
                obs=h5.create_group('obs')
                for field in (*BIO,*STRATA): obs.create_dataset(field,data=['v','v'],dtype=h5py.string_dtype())
                obs.create_dataset('cell_key',data=['control','perturbed'],dtype=h5py.string_dtype())
                obs.create_dataset('control_kind',data=['NTC','OTHER'],dtype=h5py.string_dtype())
                obs.create_dataset('depth_native',data=[99.,120.])
                bank={**{k:'v' for k in BIO},'target':'NTC'}
                selected=[dict(source_row=0,bank_row=0,cell_key='control',stratum=['v']*3)]
                args=dict(expected_source_sha256='verified',verified_source_sha256='verified')
                result=recover_depth(h5,selected,[bank],**args)
                self.assertEqual(result['cells'][0]['depth_native'],99.)
                self.assertFalse(result['RNA_matrix_opened']); self.assertNotIn('X',h5)
                bad=copy.deepcopy(selected);bad[0]['source_row']=1;bad[0]['cell_key']='perturbed'
                with self.assertRaises(ValueError):recover_depth(h5,bad,[bank],**args)
                with self.assertRaises(ValueError):recover_depth(h5,selected*2,[bank],**args)
                with self.assertRaises(ValueError):recover_depth(h5,selected,[bank],**{**args,'verified_source_sha256':'other'})


if __name__=='__main__':unittest.main()
