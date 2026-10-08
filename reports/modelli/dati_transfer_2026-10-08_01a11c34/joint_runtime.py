"""Fold-first, explicit multi-bank source reconstruction for T2."""
import json
import os
from pathlib import Path
import shutil
import time
import numpy as np
import pandas as pd
from alltarget_runtime import sha,write,locate,open_mmap
import estimator
import fold_bank
from joint_rows import joint


def main(*, input_root=Path('/kaggle/input'), scratch_root=Path('/kaggle/temp'), ram_available=None):
    start=time.monotonic();p=json.loads(Path('params.json').read_text())
    for name,pin in p['embedded'].items():
        if Path(name).stat().st_size!=pin['bytes'] or sha(name)!=pin['sha256']:raise ValueError('embedded mismatch')
    fold_bank.validate_split(p['split'])
    if p['recipe'] != estimator.CALL:raise ValueError('estimator recipe changed')
    if ram_available is None:
        ram_available=next(int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    resources=dict(cpu=os.cpu_count(),disk_free_bytes=shutil.disk_usage(Path.cwd()).free,
        ram_available_bytes=ram_available)
    write('resources.json',resources)
    if resources['ram_available_bytes']<2<<30:raise ValueError('RAM below budget')
    genes=pd.read_csv('gene_names.csv').iloc[:,0].astype(str).tolist()
    scratch=Path(scratch_root)/p['job_id'];scratch.mkdir(parents=True,exist_ok=False)
    banks={};selection={}
    for unit,spec in p['units'].items():
        files={k:locate(Path(input_root),v) for k,v in spec['bank']['files'].items()}
        rows=pd.read_csv(files['rows.csv'],keep_default_na=False)
        complete=json.loads(files['complete.json'].read_text())
        if len(rows)!=complete['rows'] or int(rows.n.sum())!=complete['cells_used']:raise ValueError('population mismatch')
        mapping={t:dict(target=t,components=[t],evidence=spec['mapping_evidence']) for t in spec['resolved_labels']}
        frame,selection[unit]=fold_bank.select_rows(rows,mapping,p['split'],unit)
        x=open_mmap(files['count_sum.npz'],scratch/(unit+'_counts.npy'))
        m=open_mmap(files['mask.npz'],scratch/(unit+'_masks.npy'))
        if x.shape!=m.shape or x.shape!=(len(rows),len(genes)):raise ValueError('bank shape mismatch')
        banks[unit]=dict(frame=frame,counts=x,masks=m)
    # No masks, pooled controls, means or shrinkage were learned before selection.
    frame,x,m,pooling=joint(p['policy'],banks,genes)
    result=fold_bank.derive(frame,x,m,genes,estimator.effects_from_pseudobulk,estimator.CALL,
        Path('effects'),chunk_targets=p['chunk_targets'])
    result.update(unit=p['policy'],split=p['split'],pooling=pooling,selection=selection,
        params_sha256=sha('params.json'),axis_sha256=sha('gene_names.csv'),recipe=estimator.CALL,
        bank={u:s['bank'] for u,s in p['units'].items()},model_fit=False,claims_complete_corpus=False,
        sampled_cells_read=0,bank_cells=sum(s['bank_cells'] for s in selection.values()),
        seconds=time.monotonic()-start,
        outputs={str(f):dict(bytes=f.stat().st_size,sha256=sha(f)) for f in Path('effects').rglob('*') if f.is_file()})
    write('effect_release.json',result)
    write('complete.json',dict(status='derived_joint',receipt_sha256=sha('effect_release.json'),
        policy=p['policy'],targets=sum(len(c['targets_derived']) for c in result['contexts']),
        contexts=len(result['contexts']),model_fit=False))
    print(json.dumps(dict(policy=p['policy'],seconds=result['seconds'],pooling=pooling)),flush=True)


if __name__=='__main__':main()
