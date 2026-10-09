"""Adversarial small fixtures for the NTC-only input path."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import h5py
import numpy as np
import scipy.sparse as sp
from ntc_cells import BIO, selection, extract, normalized_batch, merge_candidates, sha


class NTCCellsTests(unittest.TestCase):
    def test_anndata_nullable_string_roundtrip_and_mapping(self):
        import anndata as ad
        import pandas as pd
        from ntc_cells import column, gene_mapping
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'nullable.h5ad'
            frame=pd.DataFrame(dict(symbol=pd.array(['G1','G2',None],dtype='string'),
                official_index=[0,1,-1],measured=[True,True,True],mapping=['unique']*3))
            data=ad.AnnData(sp.csr_matrix((1,3)),var=frame)
            with ad.settings.override(allow_write_nullable_strings=True):
                data.write_h5ad(path,convert_strings_to_categoricals=False)
            with h5py.File(path,'r') as h:
                self.assertEqual(set(h['var/symbol']),{'values','mask'})
                self.assertEqual(column(h['var'],'symbol').tolist(),['G1','G2','MISSING'])
                mapped,mask=gene_mapping(h,['G1','G2'])
                self.assertEqual(mapped.tolist(),[0,1,-1])
                self.assertTrue(mask.all())
            with h5py.File(path,'r+') as h:h['var/symbol/mask'][0]=True
            with h5py.File(path,'r') as h:
                with self.assertRaisesRegex(ValueError,'frozen axis'):gene_mapping(h,['G1','G2'])

    def test_nullable_nested_categories_and_bad_masks(self):
        from ntc_cells import column
        with tempfile.TemporaryDirectory() as d:
            with h5py.File(Path(d)/'test.h5','w') as h:
                group=h.create_group('symbol');cats=group.create_group('categories')
                cats.create_dataset('values',data=['G1','G2'],dtype=h5py.string_dtype())
                cats.create_dataset('mask',data=[False,False])
                group.create_dataset('codes',data=[1,0,-1])
                self.assertEqual(column(h,'symbol').tolist(),['G2','G1','MISSING'])
                group['codes'][0]=-2
                with self.assertRaisesRegex(ValueError,'code out of bounds'):column(h,'symbol')
                group['codes'][0]=1
                del cats['mask'];cats.create_dataset('mask',data=[0,1])
                with self.assertRaisesRegex(ValueError,'nullable mask'):column(h,'symbol')

    def fixture(self, root):
        identity = dict(study='s', context='ctx', donor_or_clone='D1', condition='Rest',
                        modality='CRISPRi', chemistry='Flex')
        rows = root/'rows.csv'
        with rows.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=[*BIO,'target','n'])
            writer.writeheader(); writer.writerow({**identity,'target':'NTC','n':6})
        raw=root/'raw.h5ad'
        x=np.array([[2,0,7,91],[5,0,3,92],[6,0,0,94],
                    [4,0,1,95],[7,0,2,91],[8,0,1,91],
                    [100,99,0,0],[77,88,0,0]],dtype=np.uint32)
        with h5py.File(raw,'w') as h:
            sparse=sp.csr_matrix(x); group=h.create_group('X');group.attrs['shape']=x.shape
            for key in ('data','indices','indptr'):group.create_dataset(key,data=getattr(sparse,key))
            obs=h.create_group('obs')
            string=h5py.string_dtype()
            for key,value in identity.items():obs.create_dataset(key,data=[value]*8,dtype=string)
            obs.create_dataset('cell_key',data=[f'cell{i}' for i in range(8)],dtype=string)
            obs.create_dataset('control_kind',data=['NTC']*6+['targeted']*2,dtype=string)
            obs.create_dataset('library',data=['L1']*3+['L2']*3+['L1']*2,dtype=string)
            obs.create_dataset('batch',data=['batch']*8,dtype=string)
            obs.create_dataset('guides',data=['ntc']*6+['g1','g2'],dtype=string)
            obs.create_dataset('depth_native',data=x.sum(1))
            var=h.create_group('var')
            var.create_dataset('official_index',data=[0,1,2,-1])
            var.create_dataset('symbol',data=['G1','G2','G3','OUTSIDE'],dtype=string)
            var.create_dataset('mapping',data=['unique']*4,dtype=string)
            var.create_dataset('measured',data=[True,True,False,True])
        source=dict(file=raw.name,bytes=raw.stat().st_size,sha256=sha(raw),cells=8)
        plan=dict(part_id='part',genes=['G1','G2','G3'],sources=[source],seed='test',
            cells_per_stratum=2,rows=dict(bytes=rows.stat().st_size,sha256=sha(rows)),
            controls=[dict(bank_row=0,context_id='canonical',expected_cells=6)])
        return plan,{source['sha256']:str(raw)},rows,raw

    def repin(self,plan,raw):
        plan['sources'][0].update(bytes=raw.stat().st_size,sha256=sha(raw))
        return {plan['sources'][0]['sha256']:str(raw)}

    def test_native_depth_measured_zero_and_unmeasured_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d));chosen=selection(p,loc,rows)
            self.assertEqual(len(chosen),4)
            self.assertEqual({tuple(r['stratum'])[0] for r in chosen},{'L1','L2'})
            b=extract(p,loc,chosen); x,m=normalized_batch(b,np.arange(4))
            np.testing.assert_allclose(x[:,0],np.log1p(b['counts'].toarray()[:,0]*100),rtol=1e-6)
            self.assertTrue(m[:,1].all());self.assertFalse(m[:,2].any())
            self.assertTrue((x[:,1:]==0).all())
            self.assertEqual(b['perturbed_RNA_rows_read'],0)

    def test_perturbed_values_do_not_change_selection_or_features(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d));chosen=selection(p,loc,rows)
            before=extract(p,loc,chosen)
            with h5py.File(raw,'r+') as h:
                ptr=h['X/indptr'][:]; h['X/data'][ptr[6]:]=999999
                h['obs/depth_native'][6:]=1
            loc=self.repin(p,raw);after_chosen=selection(p,loc,rows)
            self.assertEqual([r['cell_key'] for r in chosen],[r['cell_key'] for r in after_chosen])
            after=extract(p,loc,after_chosen)
            np.testing.assert_array_equal(before['counts'].toarray(),after['counts'].toarray())
            np.testing.assert_array_equal(before['native_depth'],after['native_depth'])

    def test_bad_hash_fails_before_metadata_read(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d));raw.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'pinned input changed'):selection(p,loc,rows)

    def test_missing_context_cells_are_not_silently_omitted(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d));p['controls'][0]['expected_cells']=7
            with self.assertRaisesRegex(ValueError,'population differs'):selection(p,loc,rows)

    def test_no_aligned_depth_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d))
            with h5py.File(raw,'r+') as h:del h['obs/depth_native']
            loc=self.repin(p,raw);chosen=selection(p,loc,rows)
            with self.assertRaisesRegex(ValueError,'depth_native'):extract(p,loc,chosen)

    def test_duplicate_control_and_axis_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d))
            with h5py.File(raw,'r+') as h:h['obs/cell_key'][1]='cell0'
            loc=self.repin(p,raw)
            with self.assertRaisesRegex(ValueError,'duplicate NTC'):selection(p,loc,rows)
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d));chosen=selection(p,loc,rows)
            p['genes'][0]='WRONG'
            with self.assertRaisesRegex(ValueError,'frozen axis'):extract(p,loc,chosen)

    def test_merge_disjoint_parts_equals_global_bottom_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p,loc,rows,raw=self.fixture(Path(d));chosen=selection(p,loc,rows)
            for r in chosen:r['part_id']='a'
            second=copy.deepcopy(chosen)
            for r in second:r.update(part_id='b',cell_key='b'+r['cell_key'],priority='0'*64)
            merged=merge_candidates(chosen+second,cap=2)
            self.assertEqual(len(merged),4)
            self.assertTrue(all(r['cell_key'].startswith('b') for r in merged))
            self.assertTrue(all(r['stratum_population']==6 for r in merged))
            with self.assertRaisesRegex(ValueError,'duplicate candidates'):
                merge_candidates(chosen+chosen)

    def test_runner_writes_reloadable_arrays_and_refuses_overwrite(self):
        from run_ntc_extraction import run
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p,loc,rows,raw=self.fixture(root)
            genes=root/'genes.json';genes.write_text(json.dumps(p.pop('genes')))
            p.update(genes_file=genes.name,genes_sha256=sha(genes))
            plan=root/'plan.json';plan.write_text(json.dumps(p))
            locations=root/'locations.json';locations.write_text(json.dumps(loc))
            out=root/'ntc'/'missing-parent'/'out'
            # Tiny fixture tests the serialization contract independently of
            # competing applications on this laptop. Cloud resources stay gated.
            with patch('run_ntc_extraction.available_memory',return_value=2<<30), \
                 patch('run_ntc_extraction.shutil.disk_usage') as disk:
                disk.return_value.free=2<<30
                receipt=run(plan,sha(plan),locations,rows,out)
                disk.assert_called_once_with(root)
            self.assertEqual(receipt['NTC_cells_read'],4)
            self.assertEqual(receipt['cells_consumed_by_trainer'],0)
            self.assertEqual(sp.load_npz(out/'counts.npz').shape,(4,3))
            with np.load(out/'axes_depth_mask.npz',allow_pickle=False) as arrays:
                np.testing.assert_array_equal(arrays['genes'],json.loads(genes.read_text()))
            with self.assertRaises(FileExistsError):run(plan,sha(plan),locations,rows,out)

    def test_worker_initializes_empty_runtime_and_shared_gene_axis(self):
        from ntc_campaign_worker import main
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);work=root/'working';work.mkdir()
            inputs=root/'input';inputs.mkdir()
            p,loc,rows,raw=self.fixture(inputs)
            genes=work/'genes.json';genes.write_text(json.dumps(p.pop('genes')))
            p.update(genes_file=genes.name,genes_sha256=sha(genes))
            plan=work/'plan.json';plan.write_text(json.dumps(p))
            (work/'job.json').write_text(json.dumps(dict(parts=[dict(
                plan=plan.name,plan_sha256=sha(plan),rows=str(rows))])))
            with patch('run_ntc_extraction.available_memory',return_value=2<<30):
                main(work,inputs)
            done=json.loads((work/'campaign_complete.json').read_text())
            self.assertEqual(done['status'],'COMPLETE')
            self.assertEqual(done['parts'][0]['cells'],4)
            self.assertEqual(sp.load_npz(work/'ntc/part/counts.npz').shape,(4,3))


if __name__=='__main__':unittest.main()
