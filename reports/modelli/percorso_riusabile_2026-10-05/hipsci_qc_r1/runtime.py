"""Hash-verified cloud diagnostics of the existing targeted HIPSCI count bank."""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
import pandas as pd
import psutil
import qc,estimator

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=json.loads(Path('params.json').read_text())
    assert p['recipe']==estimator.CALL
    resources=dict(ram_available=psutil.virtual_memory().available,disk_free=shutil.disk_usage('/kaggle/working').free)
    Path('resources.json').write_text(json.dumps(resources))
    if resources['ram_available']<8<<30 or resources['disk_free']<2<<30:raise ValueError('insufficient resources')
    files={}
    for name,pin in p['bank_files'].items():
        matches=[f for f in Path('/kaggle/input').rglob(name) if f.as_posix().endswith('/bank/hipsci_targeted_19/'+name)]
        if len(matches)!=1:raise ValueError('ambiguous bank '+name)
        f=matches[0]
        if f.stat().st_size!=pin['bytes'] or sha(f)!=pin['sha256']:raise ValueError('changed bank '+name)
        files[name]=str(f)
    for name,pin in p['embedded_inputs'].items():
        assert Path(name).stat().st_size==pin['bytes'] and sha(name)==pin['sha256']
    genes=pd.read_csv('gene_names.csv').iloc[:,0].astype(str).tolist()
    assert genes==p['genes']
    panel=p['panel']['targets']
    assert hashlib.sha256('\n'.join(panel).encode()).hexdigest()==p['panel']['panel_sha256']
    rows=pd.read_csv(files['rows.csv'],keep_default_na=False)
    receipt=json.loads(Path(files['complete.json']).read_text())
    assert len(rows)==receipt['rows'] and int(rows.n.sum())==receipt['cells_used']
    # No guide identity is inferred from expression overlap. Unassigned identities stay explicit.
    assigned=~rows.target.isin(['UNASSIGNED','NO_METADATA'])
    frame=rows.loc[assigned]
    assert set(frame.study)=={'hipsci_targeted_19'} and set(frame.modality)=={'CRISPRi'}
    assert set(frame.condition)=={'day3'} and set(frame.chemistry)=={'MISSING'}
    assert not frame.donor_or_clone.isin(['MISSING','UNASSIGNED','']).any()
    with np.load(files['count_sum.npz'],allow_pickle=False) as z:counts=z['value']
    with np.load(files['mask.npz'],allow_pickle=False) as z:masks=z['value']
    assert counts.shape==masks.shape==(len(rows),len(genes)) and masks.dtype==bool
    summaries=[]
    with Path('own_gene_records.jsonl').open('x') as out:
        for clone,group in frame.groupby('donor_or_clone',sort=True):
            ix=group.index.to_numpy()
            mask=masks[ix].all(axis=0)
            x=counts[ix]
            assert np.isfinite(x).all() and (x>=0).all() and (x[~masks[ix]]==0).all()
            assert set(group.context)=={clone} and (group.target=='NTC').any()
            records=qc.diagnose(x,group.reset_index(drop=True),genes,mask,panel)
            summaries.append(dict(clone=str(clone),ntc_cells=int(group.loc[group.target=='NTC','n'].sum()),
                                  assigned_cells=int(group.n.sum()),**qc.summarize(records)))
            for r in records:out.write(json.dumps(dict(clone=str(clone),**r),allow_nan=False)+'\n')
            print(json.dumps(dict(clone=str(clone),diagnostics_complete=True)),flush=True)
    assert len(summaries)==19
    proof=dict(state='diagnostic_complete_not_automatic_admission',input_files=files,input_hashes=p['bank_files'],
        axis_sha256=p['embedded_inputs']['gene_names.csv']['sha256'],panel_sha256=p['panel']['panel_sha256'],
        params_sha256=sha('params.json'),source=p['producer'],recipe=estimator.CALL,contexts=summaries,
        no_reingestion=True,no_context_exclusion=True,no_weights_changed=True,not_heldout_validation=True,
        output=dict(path='own_gene_records.jsonl',bytes=Path('own_gene_records.jsonl').stat().st_size,sha256=sha('own_gene_records.jsonl')))
    Path('qc_receipt.json').write_text(json.dumps(proof,indent=1,allow_nan=False)+'\n')

if __name__=='__main__':main()
