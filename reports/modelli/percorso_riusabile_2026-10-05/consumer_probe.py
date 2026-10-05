"""Cloud storage/reader integration check; no fit, anchors, or model evaluation."""
import json
import os
from pathlib import Path
import time
import numpy as np
import psutil
from sample_reader import SampleReader, sha
from population_reader import PopulationReader


def main():
    started=time.time();p=json.loads(Path('params.json').read_text())
    env={'cpus':os.cpu_count(),'ram_available':psutil.virtual_memory().available}
    print(json.dumps(env),flush=True)
    if env['ram_available'] < 8 << 30:
        raise RuntimeError('insufficient memory for bank reader')
    roots={}
    for kind,key in [('bank','bank_sha256'),('samples','sample_sha256')]:
        found=[f.parent for f in Path('/kaggle/input').rglob('complete.json')
               if f.parent.name==p['unit'] and f.parent.parent.name==kind and sha(f)==p[key]]
        if len(found)!=1:
            raise ValueError('missing/ambiguous mounted '+kind)
        roots[kind]=found[0]
    # Integrity-only traversal; it creates no scientific training/validation split.
    population=PopulationReader(roots['bank'],p['bank_sha256'])
    samples=SampleReader(roots['samples'],p['sample_sha256'],p['bank_sha256'],level=64)
    population.require_sample_link(samples)
    populations=0
    for batch in population.batches():
        populations+=len(batch['bank_rows'])
    row_cells=np.zeros(len(samples.rows),dtype=np.int64)
    for batch in samples.batches(128):
        x=batch['counts'];mask=batch['mask']
        if not np.isfinite(x.data).all() or (x.data<0).any() or (np.asarray(x.sum(1)).ravel()<=0).any():
            raise ValueError('invalid consumed cell counts')
        coo=x.tocoo()
        if not mask[coo.row,coo.col].all():
            raise ValueError('counts outside measured axis')
        np.add.at(row_cells,batch['bank_rows'],1)
        samples.acknowledge(batch['batch_id'],None)
        if batch['batch_id']%500==0:
            print(json.dumps({'batches':batch['batch_id']+1,'cells':int(row_cells.sum()),'seconds':round(time.time()-started)}),flush=True)
    exposure=samples.exposure()
    if (exposure['unique_cells_yielded']!=samples.receipt['levels']['64'] or exposure['missing_targets']
        or exposure['unacknowledged_batches'] or (row_cells==0).any() or (row_cells>samples.rows.n.to_numpy()).any()
        or populations!=len(samples.rows)-int((samples.rows.target=='NTC').sum())):
        raise ValueError('reader coverage mismatch')
    result={'complete':True,'kind':'storage_reader_integration_only','unit':p['unit'],
            'bank_sha256':p['bank_sha256'],'sample_sha256':p['sample_sha256'],
            'population_rows':populations,'sample_rows_covered':int((row_cells>0).sum()),
            'control_cells_read':int(row_cells[samples.rows.target=='NTC'].sum()),
            'sample_exposure':exposure,'bank_files_verified':sorted(population.verified),
            'environment':env,'seconds':round(time.time()-started),
            'training_used':False,'gene_names_bound':False,'extended_training_ready':False}
    Path('consumer_complete.json').write_text(json.dumps(result,indent=1))
    print(json.dumps({k:v for k,v in result.items() if k!='sample_exposure'}),flush=True)


if __name__=='__main__':
    main()
