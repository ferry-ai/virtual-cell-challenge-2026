"""Official query controls: full provided-native depth, frozen stratified hashes."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import h5py
import numpy as np
import scipy.sparse as sp
from ntc_cells import BIO,column,checked,sha
from run_ntc_extraction import available_memory


def extract(path,plan):
    checked(path,plan['source'])
    identity=plan['identity'];records=[];rows=[];depths=[]
    with h5py.File(path,'r') as h:
        obs=h['obs'];keys=column(obs,'_index').astype(str)
        guides=column(obs,'ntc_id').astype(str);targets=column(obs,'target_gene').astype(str)
        genes=column(h['var'],'_index').astype(str)
        if genes.tolist()!=plan['genes']:raise ValueError('official native axis differs')
        if len(keys)!=plan['source']['cells'] or len(set(keys))!=len(keys):raise ValueError('official cell identity differs')
        if not np.all(targets=='non-targeting') or np.any(guides=='MISSING'):
            raise ValueError('official input includes non-control or missing guide')
        if h['X'].attrs['encoding-type']!='csr_matrix':raise ValueError('official counts require CSR')
        populations=Counter(guides)
        for guide in sorted(populations):
            stratum=['MISSING','MISSING',guide]
            group=(plan['context_id'],tuple(identity[k] for k in BIO),tuple(stratum))
            candidates=[]
            for row in np.flatnonzero(guides==guide):
                priority=hashlib.sha256(json.dumps([plan['seed'],group,keys[row]],ensure_ascii=False,
                    separators=(',',':')).encode()).hexdigest()
                candidates.append((priority,keys[row],int(row)))
            chosen=sorted(candidates)[:plan['cells_per_stratum']]
            for priority,key,row in chosen:
                lo,hi=map(int,h['X/indptr'][row:row+2])
                data=h['X/data'][lo:hi].astype(np.float64);cols=h['X/indices'][lo:hi].astype(int)
                if not np.isfinite(data).all() or (data<0).any() or not np.equal(data,np.floor(data)).all():
                    raise ValueError('official raw counts invalid')
                if (cols<0).any() or (cols>=len(genes)).any() or data.sum()<=0:
                    raise ValueError('official native row invalid')
                # Full native source row, before any alignment or feature mask.
                depths.append(float(data.sum()))
                rows.append(sp.csr_matrix((data,(np.zeros(len(cols),int),cols)),shape=(1,len(genes))))
                records.append(dict(context_id=plan['context_id'],identity=identity,stratum=stratum,
                    cell_key=key,source_sha256=plan['source']['sha256'],source_row=row,priority=priority,
                    stratum_population=populations[guide],selected_in_stratum=len(chosen),
                    inclusion_probability=len(chosen)/populations[guide],part_id=plan['part_id']))
    return dict(counts=sp.vstack(rows,format='csr'),native_depth=np.asarray(depths),
        masks=np.ones((1,len(plan['genes'])),bool),mask_index=np.zeros(len(rows),int),metadata=records)


def main():
    work=Path('/kaggle/working');contract=json.loads((work/'official_contract.json').read_text())
    resources=dict(cpu_count=os.cpu_count(),available_RAM=available_memory(),disk_free=shutil.disk_usage(work).free)
    if min(resources['available_RAM'],resources['disk_free']) < 1<<30:raise ValueError('insufficient query resources')
    completed=[]
    for plan in contract['plans']:
        hits=list(Path('/kaggle/input').rglob(plan['source']['file']))
        if len(hits)!=1:raise ValueError('official source missing or ambiguous')
        bundle=extract(hits[0],plan);out=work/'ntc'/plan['part_id'];out.mkdir(parents=True,exist_ok=False)
        sp.save_npz(out/'counts.npz',bundle['counts'])
        np.savez_compressed(out/'axes_depth_mask.npz',genes=np.asarray(plan['genes']),
            native_depth=bundle['native_depth'],masks=bundle['masks'],mask_index=bundle['mask_index'])
        (out/'cells.json').write_text(json.dumps(bundle['metadata']),encoding='utf-8')
        files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in out.iterdir()}
        n=len(bundle['metadata']);doc=dict(status='COMPLETE',part_id=plan['part_id'],
            plan_sha256=plan['plan_sha256'],contexts={plan['context_id']:n},files=files,
            arrays_shape=[n,len(plan['genes'])],NTC_cells_read=n,perturbed_RNA_rows_read=0,
            cells_consumed_by_trainer=0,complete_D053=False,resources=resources,
            code={name:sha(work/name) for name in ('official_ntc_worker.py','ntc_cells.py')},
            source_files_verified=1,raw_sizes_measured={plan['source']['sha256']:hits[0].stat().st_size},
            native_depth='sum of complete official source X row before alignment; source provides no depth_native field',
            part_role='destination',denominator_policy='full_provided_official_X_before_alignment',
            feature_mask='all features on the complete provided official native axis',
            normalized_scale='log1p(counts * 10000 / native_depth)',storage_parts_need_global_reservoir_merge=True)
        (out/'complete.json').write_text(json.dumps(doc,indent=2))
        completed.append(dict(part_id=plan['part_id'],cells=n,contexts=doc['contexts']))
    (work/'campaign_complete.json').write_text(json.dumps(dict(status='COMPLETE',parts=completed),indent=2))


if __name__=='__main__':main()
