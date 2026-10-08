"""Small end-to-end fixtures for cloud entry, source pooling and receipts."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

BANK=Path(__file__).resolve().parents[1]/'banca_canonica_2026-10-07'
spec=importlib.util.spec_from_file_location('estimator',BANK/'consumer/estimator.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E);sys.modules['estimator']=E
import joint_runtime as R
from joint_rows import UNITS


class Runtime(unittest.TestCase):
    def test_all_policies_start_without_scratch_parent_and_emit_pinned_outputs(self):
        for policy in ('h1','k562_gwps','cd4_Rest','cd4_Stim8hr','cd4_Stim48hr','hipsci_targeted_19'):
            with self.subTest(policy=policy),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);work=root/'work';work.mkdir();inputs=root/'inputs';inputs.mkdir()
                pd.DataFrame({'gene':['g'+str(i) for i in range(9)]}).to_csv(work/'gene_names.csv',index=False)
                units={};all_counts=[];all_obs=[]
                for i,unit in enumerate(sorted(UNITS[policy])):
                    context='H1' if policy=='h1' else unit if policy.startswith('cd4') else policy
                    donor='D'+str(i) if policy.startswith('cd4') else 'UNREPORTED@'+unit if policy=='h1' else 'd'
                    condition=unit.split('_')[1] if policy.startswith('cd4') else 'Rest'
                    target='B' if unit=='h1_val' else 'A'
                    records=[dict(study=unit if policy=='h1' else 'study',line_group='line',context=context,
                        donor_or_clone=donor,condition=condition,modality='CRISPRi',chemistry='assay',target=t,n=30)
                        for t in ('NTC',target)]
                    counts=np.array([[100,200,300,400,500,600,700,800,900],
                                     [500,80,200,800,90,500,300,1000,300]],float)
                    if policy=='k562_gwps':counts[1]*=(i+1)
                    dest=inputs/unit;dest.mkdir();pd.DataFrame(records).to_csv(dest/'rows.csv',index=False)
                    np.savez_compressed(dest/'count_sum.npz',value=counts)
                    np.savez_compressed(dest/'mask.npz',value=np.ones_like(counts,bool))
                    (dest/'complete.json').write_text(json.dumps(dict(rows=2,cells_used=60)))
                    units[unit]=dict(bank=dict(files={p.name:dict(bytes=p.stat().st_size,sha256=R.sha(p)) for p in dest.iterdir()}),
                        resolved_labels=[target],mapping_evidence='fixture identity')
                    all_counts.append(counts)
                params=dict(job_id='fixture',policy=policy,units=units,embedded={},chunk_targets=1,recipe=E.CALL,
                    split=dict(id='prod',regime='production',held_groups=[],hidden_targets=[],protected_units=['h1_test'],group_aliases={}))
                (work/'params.json').write_text(json.dumps(params));old=Path.cwd()
                try:
                    os.chdir(work);R.main(input_root=inputs,scratch_root=root/'absent'/'temp',ram_available=3<<30)
                finally:os.chdir(old)
                receipt=json.loads((work/'effect_release.json').read_text());done=json.loads((work/'complete.json').read_text())
                self.assertEqual(done['receipt_sha256'],R.sha(work/'effect_release.json'))
                self.assertEqual(done['contexts'],1);self.assertEqual(done['targets'],2 if policy=='h1' else 1)
                self.assertEqual(receipt['pooling']['duplicate_control_rows_dropped'],1 if policy=='h1' else 0)
                for name,pin in receipt['outputs'].items():self.assertEqual(pin['sha256'],R.sha(work/name))
                if policy=='k562_gwps':
                    # Direct sufficient-statistic oracle: sum disjoint blocks before estimating.
                    obs=pd.DataFrame(dict(target=['non-targeting','A'],donor=['d','d'],condition=['scope','scope'],n_cells=[60,60]))
                    direct=E.effects_from_pseudobulk(sum(all_counts),obs,['g'+str(i) for i in range(9)],targets=['A'],condition=None,**E.CALL)
                    with np.load(work/'effects/context000_chunk00000.npz') as z:
                        np.testing.assert_allclose(z['shrunk'],direct['shrunk'],rtol=1e-6,atol=1e-7,equal_nan=True)


if __name__=='__main__':unittest.main()
