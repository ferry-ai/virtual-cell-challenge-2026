import hashlib
import json
import shutil
import time
from pathlib import Path
import numpy as np
import pandas as pd
import psutil
import adapter
import estimator
import policy


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):
            h.update(b)
    return h.hexdigest()


def main():
    p=json.loads(Path('params.json').read_text())
    if p['recipe']!=adapter.CALL:
        raise ValueError('recipe differs from frozen original')
    resources=dict(ram_available=psutil.virtual_memory().available,
                   disk_free=shutil.disk_usage('/kaggle/working').free)
    Path('resources.json').write_text(json.dumps(resources))
    if resources['ram_available'] < 8<<30 or resources['disk_free'] < 2<<30:
        raise RuntimeError('insufficient runtime resources')
    verified={}
    root=Path('/kaggle/input')
    for name,pin in p['bank_files'].items():
        matches=[f for f in root.rglob(name) if f.as_posix().endswith('/bank/hipsci_targeted_19/'+name)]
        if len(matches)!=1:
            raise ValueError('ambiguous or missing bank file: '+name)
        f=matches[0]
        if f.stat().st_size!=pin['bytes'] or sha(f)!=pin['sha256']:
            raise ValueError('changed bank file: '+name)
        verified[name]=str(f)
    for name,pin in p['embedded_inputs'].items():
        if Path(name).stat().st_size!=pin['bytes'] or sha(name)!=pin['sha256']:
            raise ValueError('changed embedded input: '+name)
    genes=pd.read_csv('gene_names.csv').iloc[:,0].astype(str).to_list()
    if genes!=p['genes']:
        raise ValueError('producer/consumer axis symbols differ')
    panel=p['panel']['targets']
    if hashlib.sha256('\n'.join(panel).encode()).hexdigest()!=p['panel']['panel_sha256']:
        raise ValueError('panel changed')
    rows=pd.read_csv(verified['rows.csv'],keep_default_na=False)
    receipt=json.loads(Path(verified['complete.json']).read_text())
    if len(rows)!=receipt['rows'] or int(rows.n.sum())!=receipt['cells_used']:
        raise ValueError('population coverage changed')
    # Metadata classification precedes estimation; matrices remain in the cloud.
    policy.metadata_plan(rows,panel)
    with np.load(verified['count_sum.npz'],allow_pickle=False) as z:
        counts=z['value']
    with np.load(verified['mask.npz'],allow_pickle=False) as z:
        masks=z['value']
    blocks,lineage=policy.prepare(rows,counts,masks,genes,panel)
    result=adapter.estimate_joint(blocks,panel,estimator.effects_from_pseudobulk)
    measured=blocks[0]['mask']
    usable=np.asarray(result['control_mean'])>=1e-6
    columns=np.flatnonzero(measured)[usable]
    arrays={k:np.full((len(result['targets']),len(genes)),np.nan,np.float32)
            for k in ('raw','shrunk','se')}
    for k in arrays:
        arrays[k][:,columns]=result[k][:,usable]
    if not result['targets']:
        raise ValueError('no usable panel targets')
    out=Path('hipsci_targeted_19.npz')
    np.savez_compressed(out,genes=np.asarray(genes),targets=np.asarray(result['targets']),
                        n_cells=result['n_cells'],meta=np.asarray(json.dumps(dict(source='hipsci_targeted_19',recipe=adapter.CALL))),**arrays)
    proof=dict(state='derived_production_fragment',full_training=False,
        production_hidden_targets=[],not_heldout_validation=True, input_files=verified,
        input_hashes=p['bank_files'],axis_sha256=p['embedded_inputs']['gene_names.csv']['sha256'],
        panel_sha256=p['panel']['panel_sha256'],params_sha256=sha('params.json'),
        source=p['producer'],lineage=lineage,source_vote='one; donors pooled before shrink',
        contexts=[dict(context=b['context'],bank_rows=b['bank_rows']) for b in blocks],
        recipe=adapter.CALL,targets=result['targets'],n_cells=result['n_cells'].tolist(),
        output=dict(path=str(out),bytes=out.stat().st_size,sha256=sha(out)),
        matrix_hash_verified_in_consumer=True,mixer_consumed=False)
    Path('fit_receipt.json').write_text(json.dumps(proof,indent=1)+'\n')
    print(json.dumps(dict(state=proof['state'],contexts=len(blocks),targets=len(result['targets']))),flush=True)


if __name__=='__main__':
    main()
