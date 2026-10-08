"""Pinned per-unit cloud consumer. Extract NPY members to disk, then memory-map.

Produces all eligible single-target effects in separate biological contexts.
This is an effect-learning input release, not a trained cellular predictor.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import zipfile
import numpy as np
import pandas as pd
import fold_bank
import estimator


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):
            h.update(block)
    return h.hexdigest()


def write(path, obj):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(obj,f,indent=1,allow_nan=False); f.write('\n')


def locate(root, pin):
    hits=[p for p in root.rglob('*') if p.is_file() and p.stat().st_size == pin['bytes']]
    for p in hits:
        if sha(p)==pin['sha256']:
            return p
    raise ValueError('pinned bank object missing: '+pin['sha256'])


def open_mmap(npz, dest):
    with zipfile.ZipFile(npz) as z:
        if 'value.npy' not in z.namelist():
            raise ValueError('bank NPZ has no value.npy')
        member=z.getinfo('value.npy')
        if shutil.disk_usage(dest.parent).free < member.file_size + (2<<30):
            raise ValueError('insufficient measured scratch disk')
        with z.open(member) as source, dest.open('xb') as target:
            shutil.copyfileobj(source,target,1<<20)
    return np.load(dest,mmap_mode='r',allow_pickle=False)


def main():
    start=time.monotonic()
    p=json.loads(Path('params.json').read_text())
    fold_bank.validate_split(p['split'])
    for name,pin in p['embedded'].items():
        if Path(name).stat().st_size != pin['bytes'] or sha(name)!=pin['sha256']:
            raise ValueError('embedded identity changed: '+name)
    if p['recipe'] != estimator.CALL:
        raise ValueError('estimator recipe changed')
    ram=next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    resources=dict(utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        ram_available_bytes=ram,disk_free_bytes=shutil.disk_usage('/kaggle/working').free,cpu=os.cpu_count())
    write('resources.json',resources)
    if ram < (2<<30):
        raise ValueError('insufficient measured RAM')
    root=Path('/kaggle/input')
    files={k:locate(root,pin) for k,pin in p['bank']['files'].items()}
    rows=pd.read_csv(files['rows.csv'],keep_default_na=False)
    receipt=json.loads(files['complete.json'].read_text())
    if len(rows)!=receipt['rows'] or int(rows.n.sum())!=receipt['cells_used']:
        raise ValueError('bank population mismatch')
    genes=pd.read_csv('gene_names.csv').iloc[:,0].astype(str).to_list()
    mappings={name:dict(target=name,components=[name],evidence=p['mapping_evidence']) for name in p['resolved_labels']}
    mappings.update(p.get('explicit_crosswalk',{}))
    frame,selection=fold_bank.select_rows(rows,mappings,p['split'],p['unit'])
    write('selection.json',selection)
    write('runtime_preflight.json',dict(input_files={k:str(v) for k,v in files.items()},
        input_pins=p['bank']['files'],params_sha256=sha('params.json'),resources=resources,
        admitted_rows=len(frame),split=p['split'],learned_statistics_started=False))
    scratch=Path('/kaggle/temp') / p['job_id']
    scratch.mkdir(parents=True,exist_ok=False)
    counts=open_mmap(files['count_sum.npz'],scratch/'counts.npy')
    masks=open_mmap(files['mask.npz'],scratch/'masks.npy')
    if counts.shape!=(len(rows),len(genes)) or masks.shape!=counts.shape:
        raise ValueError('axis/rows mismatch')
    result=fold_bank.derive(frame,counts,masks,genes,estimator.effects_from_pseudobulk,
        estimator.CALL,Path('effects'),chunk_targets=p['chunk_targets'])
    result.update(unit=p['unit'],split=p['split'],params_sha256=sha('params.json'),
        mapping_evidence=p['mapping_evidence'],bank=p['bank'],selection_sha256=sha('selection.json'),
        selection_counts=selection['cells_by_role'],bank_cells=int(rows.n.sum()),
        axis_sha256=p['embedded']['gene_names.csv']['sha256'],sampled_cells_read=0,
        claims_complete_corpus=False,model_fit=False,not_a_score=True,seconds=time.monotonic()-start,
        outputs={str(q):dict(bytes=q.stat().st_size,sha256=sha(q)) for q in Path('effects').rglob('*') if q.is_file()})
    write('effect_release.json',result)
    write('complete.json',dict(status='derived',unit=p['unit'],receipt_sha256=sha('effect_release.json'),
        targets=sum(len(c['targets_derived']) for c in result['contexts']),
        contexts=len(result['contexts']),model_fit=False))
    print(json.dumps(dict(state='derived',unit=p['unit'],seconds=result['seconds'])),flush=True)


if __name__=='__main__':
    main()
