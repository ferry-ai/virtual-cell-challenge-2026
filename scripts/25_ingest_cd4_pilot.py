"""Extract a small stratified CD4 raw-count pilot with a hard HTTP byte budget.

Output retains the source gene axis; missing VCC genes must remain masked later.
This is an ingestion smoke test, not enough data for model selection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import anndata as ad
import h5py
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, vstack
from vcc2026.remote_ranges import HTTPRangeReader

DEFAULT='https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/marson2025_data/D1_Rest.assigned_guide.h5ad'

def categorical(group,key):
    node=group[key]
    return node['categories'].asstr()[:],node['codes'][:]

def stratified_rows(indices,guide,lane,n,rng):
    """Round-robin across guide/lane strata, random within each stratum."""
    frame=pd.DataFrame({'row':indices,'guide':guide[indices],'lane':lane[indices]})
    groups=[rng.permutation(g.row.to_numpy()).tolist() for _,g in frame.groupby(['guide','lane'],sort=True)]
    rng.shuffle(groups)
    chosen=[]
    while groups and len(chosen)<n:
        next_groups=[]
        for group in groups:
            if len(chosen)==n: break
            chosen.append(group.pop())
            if group: next_groups.append(group)
        groups=next_groups
    return chosen

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default=DEFAULT)
    p.add_argument('--targets',nargs='+',required=True)
    p.add_argument('--cells-per-target',type=int,default=16)
    p.add_argument('--ntc',type=int,default=32)
    p.add_argument('--max-mib',type=int,default=128)
    p.add_argument('--seed',type=int,default=2026)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--guide-map',type=Path,default=Path('reports/candidate_verification/annotations/cd4_design.csv'))
    args=p.parse_args()
    if args.out.exists(): raise FileExistsError(args.out)
    if args.cells_per_target<1 or args.ntc<1: raise ValueError('Positive cell counts required')
    if len(args.targets)*args.cells_per_target+args.ntc>4096: raise ValueError('Pilot limited to 4096 cells; use aggregation for scale')
    design=pd.read_csv(args.guide_map)
    if design.sgrna_id.duplicated().any(): raise ValueError('Ambiguous curated map')
    mapping=design.set_index('sgrna_id').perturbed_gene_name.to_dict()
    rng=np.random.default_rng(args.seed)
    with HTTPRangeReader(args.url,max_bytes=args.max_mib*1024**2) as remote:
        with h5py.File(remote,'r') as f:
            gc,gcode=categorical(f['obs'],'guide_id')
            tc,tcode=categorical(f['obs'],'guide_type')
            lc,lcode=categorical(f['obs'],'lane_id')
            good=~f['obs/low_quality'][:]
            targeting=np.flatnonzero(tc=='targeting')
            ntc=np.flatnonzero(tc=='non-targeting')
            if len(targeting)!=1 or len(ntc)!=1: raise ValueError('Missing explicit guide type')
            selected=[]
            labels={}
            for target in args.targets+['non-targeting']:
                if target=='non-targeting':
                    eligible=good & (tcode==ntc[0]); n=args.ntc
                else:
                    ids=np.array([i for i,g in enumerate(gc) if mapping.get(g)==target])
                    eligible=good & (tcode==targeting[0]) & np.isin(gcode,ids); n=args.cells_per_target
                rows=stratified_rows(np.flatnonzero(eligible),gcode,lcode,n,rng)
                if not rows: raise ValueError(f'No eligible cells for {target}')
                selected.extend(rows)
                labels.update({i:target for i in rows})
            selected=sorted(set(selected))
            nvars=len(f['var/gene_name'])
            matrices=[]
            x=f['X']
            for row in selected:
                lo,hi=map(int,x['indptr'][row:row+2])
                data=x['data'][lo:hi]
                cols=x['indices'][lo:hi]
                if not (np.isfinite(data).all() and (data>=0).all() and (data==np.rint(data)).all()):
                    raise ValueError('Non-count expression detected')
                if data.max(initial=0)>np.iinfo(np.int32).max: raise ValueError('Count overflow')
                matrices.append(csr_matrix((data.astype(np.int32),cols,np.array([0,len(data)])),shape=(1,nvars)))
            obs=pd.DataFrame({'target_gene':[labels[i] for i in selected],
                              'guide_id':[gc[gcode[i]] if gcode[i]>=0 else '' for i in selected],
                              'lane_id':[lc[lcode[i]] if lcode[i]>=0 else '' for i in selected],
                              'source_row':selected},index=[f'cd4:{Path(args.url).name}:{i}' for i in selected])
            var=pd.DataFrame({'gene_name':f['var/gene_name'].asstr()[:]},index=f['var/gene_ids'].asstr()[:])
            if not var.index.is_unique: raise ValueError('Nonunique source gene IDs')
            result=ad.AnnData(X=vstack(matrices,format='csr'),obs=obs,var=var)
            result.uns['provenance']={'url':args.url,'seed':args.seed,'normalization':'none; raw integer counts',
                                      'guide_map_sha256':hashlib.sha256(args.guide_map.read_bytes()).hexdigest()}
        manifest={'url':args.url,'bytes_transferred':remote.transferred,'remote_size':remote.size,
                  'cells':result.n_obs,'genes':result.n_vars,'nnz':result.X.nnz,
                  'cell_counts':result.obs.target_gene.value_counts().to_dict(),'seed':args.seed}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    result.write_h5ad(args.out,compression='gzip')
    manifest['output_sha256']=hashlib.sha256(args.out.read_bytes()).hexdigest()
    manifest['output_bytes']=args.out.stat().st_size
    args.out.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
