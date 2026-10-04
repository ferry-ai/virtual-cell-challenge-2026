"""Tiny real-file check of streaming moments and sampling, no cloud-size local work."""
import json, sys, tempfile
from pathlib import Path
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
from types import SimpleNamespace
try: import psutil
except ImportError:
    # Resource preflight is a cloud concern; this fixture allocates two 18,533-gene rows only.
    sys.modules['psutil']=SimpleNamespace(virtual_memory=lambda:SimpleNamespace(available=4<<30))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'ibrido_pseudobulk_2026-10-04'))
from bank import run_unit, sha

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);unit=root/'job/shards/cd4_D1_Rest';unit.mkdir(parents=True)
    x=np.array([[1,1,0,0],[10,0,0,0],[0,2,2,0],[1,3,0,0]],np.float32)
    obs=pd.DataFrame({'study':['fixture']*4,'context':['CD4T D1 Rest']*4,'donor_or_clone':['D1']*4,
        'condition':['Rest']*4,'modality':['CRISPRi']*4,'chemistry':['10x']*4,'library':['L']*4,
        'batch':['B']*4,'guides':['c','c','g','g'],'target':['NTC','NTC','T','T'],
        'control_kind':['NTC','NTC','none','none'],'cell_key':['a','b','c','d']},index=list('abcd'))
    var=pd.DataFrame({'official_index':np.arange(4),'mapping':['unique']*4,'measured':[True]*4},index=list('ABCD'))
    f=unit/'shard.h5ad';ad.AnnData(sp.csr_matrix(x),obs=obs,var=var).write_h5ad(f)
    m={'shards':[{'shard':'shard','bytes':f.stat().st_size,'cells':4}]};mp=unit/'manifest.json';mp.write_text(json.dumps(m))
    spec={'name':'D1_Rest','cells':4,'receipt_sha256':'fixture','parts':[{'job':'job','unit':'cd4_D1_Rest','unit_manifest_sha256':sha(mp)}]}
    run_unit(spec,root,root/'out')
    rows=pd.read_csv(root/'out/rows.csv');means=np.load(root/'out/mean_proportion.npz')['value'];i=rows.index[rows.target=='NTC'][0]
    np.testing.assert_allclose(means[i,:4],[.75,.25,0,0])
    with np.load(root/'out/sampled_controls.npz') as controls:
        np.testing.assert_allclose(controls[str(i)][:4],[.75,.25,0,0])
    assert json.loads((root/'out/complete.json').read_text())['cells_used']==4
print('PASS: real H5AD streaming; mean of cell proportions; nested sample controls; coverage')
