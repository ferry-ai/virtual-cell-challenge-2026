"""Reproduce frozen T1, then change only its common vectors to all-target T2."""
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np


def main():
    start=time.monotonic();work=Path('/kaggle/working');inputs=Path('/kaggle/input')
    params=json.loads((work/'assembly_params.json').read_text())
    # Imported only after the launcher has restored every frozen T1 runtime file.
    import driver as t1
    if t1._sha256(work/'params.json')!=params['t1_params_sha256']:raise ValueError('T1 parameters changed')
    t1.main()
    for context,digest in params['t1_effects'].items():
        if t1._sha256(work/'effects'/('effects_'+context+'.npz'))!=digest:raise ValueError('null branch does not reproduce T1')
    (work/'effects').rename(work/'effects_t1')
    recipe=json.loads((work/'recipe_release.json').read_text());release=json.loads((work/'release.json').read_text())
    genes=np.load(work/'effects_t1/effects_A.npz',allow_pickle=False)['genes'].astype(str)
    vectors={};support={};consumed={}
    for source,spec in params['common_sources'].items():
        path=work/spec['embedded_file'] if 'embedded_file' in spec else t1._by_content(spec['file'],source+' common')
        if path.stat().st_size!=spec['file']['bytes'] or t1._sha256(path)!=spec['file']['sha256']:raise ValueError('common vector identity changed')
        with np.load(path,allow_pickle=False) as z:
            if 'genes' in z.files and z['genes'].astype(str).tolist()!=genes.tolist():raise ValueError('common axis differs')
            value=z['common'];mask=z['mask'];count=z['contributing_targets']
        if value.shape!=genes.shape or mask.dtype!=bool or mask.shape!=genes.shape or not np.isfinite(value).all():raise ValueError('common contract mismatch')
        if not np.array_equal(mask,count>0) or (value[~mask]!=0).any():raise ValueError('common missingness mismatch')
        vectors[source]=value;support[source]=mask;consumed[source]=dict(spec,path=str(path),supported_genes=int(mask.sum()))
    if set(vectors)!=set(release['voted']):raise ValueError('incomplete T2 sources')
    model=t1._find_mix(release);resolved=t1._resolve(release,model)
    # A missing mean is never silently treated as a measured zero for a source vote.
    for source,(path,_) in resolved.items():
        with np.load(path,allow_pickle=False) as z:observed=np.isfinite(z['shrunk']).any(axis=0)
        if (observed & ~support[source]).any():raise ValueError('T2 common lacks a gene voted by T1: '+source)
    common=work/'data/t2_common_production.npz';np.savez_compressed(common,genes=genes,**vectors)
    recipe.update(name='dati-transfer-t2-01a11c34-r1',common='t2_common_production.npz',
        why='Same frozen T1 target tables, weights, amplitude and cis; equal-target training common vectors include off-panel perturbations.')
    recipe_path=work/'recipe_t2.json';recipe_path.write_text(json.dumps(recipe,indent=2)+'\n')
    manifest=t1._run_stage100(recipe_path,t1._cache_dir('cache_t2',resolved,sorted(resolved)),work/'effects')
    t1._read_check(manifest,resolved,sorted(resolved))
    shutil.rmtree(work/'cache_t2')
    deltas={}
    for context in ('A','B','C'):
        with np.load(work/'effects'/('effects_'+context+'.npz'),allow_pickle=False) as z,np.load(work/'effects_t1'/('effects_'+context+'.npz'),allow_pickle=False) as old:
            if not np.array_equal(z['observed'],old['observed']):raise ValueError('T2 changed response coverage')
            d=z['lfc'].astype(np.float64)-old['lfc'];deltas[context]=dict(max_abs=float(np.abs(d).max()),l2=float(np.linalg.norm(d)))
    receipt=dict(status='T2_effects_ready',t1_null_parity=True,assembly_params_sha256=t1._sha256(work/'assembly_params.json'),
        common_sources=consumed,common_sha256=t1._sha256(common),recipe_sha256=t1._sha256(recipe_path),
        sources_read=sorted(resolved),deltas_vs_T1=deltas,seconds=time.monotonic()-start,
        effects={c:dict(bytes=(work/'effects'/('effects_'+c+'.npz')).stat().st_size,sha256=t1._sha256(work/'effects'/('effects_'+c+'.npz'))) for c in ('A','B','C')},
        claims_complete_corpus=False,claims_predictive_improvement=False,not_a_score=True,
        units='ln fold change; amplitude 1.576 and cis applied; emitter not applied')
    t1._write(work/'t2_consumption.json',receipt)
    t1._write(work/'t2_complete.json',dict(status='effects_ready',receipt_sha256=t1._sha256(work/'t2_consumption.json')))
    print(json.dumps(dict(status=receipt['status'],sources=len(vectors),seconds=receipt['seconds'])))


if __name__=='__main__':main()
