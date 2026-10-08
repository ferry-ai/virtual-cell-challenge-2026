"""Reproduce T1, consume every pinned KO context, and export the frozen T3 arm."""
from collections import defaultdict
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time
import numpy as np
from extended_transfer_core import pool_contexts,combine
from private_download_v2 import download_verified

WORK=Path('/kaggle/working')
INPUT=Path('/kaggle/input')
TEMP=Path('/kaggle/temp')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def resolve_chunk(spec,locators):
    candidates=[p for p in INPUT.rglob(Path(spec['file']).name) if p.is_file() and p.stat().st_size==spec['bytes']]
    for path in candidates:
        if digest(path)==spec['sha256']: return path,'native_mount'
    key=spec['producer']+'/'+spec['file'];locator=locators.get(key)
    if not locator or any(locator[k]!=spec[k] for k in ('bytes','sha256')):
        raise ValueError('missing frozen KO chunk: '+key)
    folder=TEMP/'private_ko';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(spec['sha256']+'.npz')
    if path.exists():
        if path.stat().st_size!=spec['bytes'] or digest(path)!=spec['sha256']:raise ValueError('invalid KO cache')
        return path,'private_cache'
    download_verified(locator['url'],path,spec['bytes'],spec['sha256'])
    return path,'private_download'


def fit(mark):
    start=time.monotonic()
    import driver as t1
    p=json.loads((WORK/'extended_params.json').read_text())
    plan=json.loads((WORK/'extended_protocol.json').read_text())
    if digest(WORK/'extended_protocol.json')!=p['protocol']['sha256']:
        raise ValueError('T3 protocol changed')
    mark('T1_null_reproduction')
    t1.main()
    for context,pin in p['t1_effects'].items():
        if digest(WORK/'effects'/('effects_'+context+'.npz'))!=pin['sha256']:
            raise ValueError('T1 null parity failed')
    (WORK/'effects').rename(WORK/'effects_t1')
    release=json.loads((WORK/'release.json').read_text())
    model=t1._find_mix(release);resolved=t1._resolve(release,model)
    loader=importlib.util.spec_from_file_location('t3_stage100',WORK/'repo/scripts/100_build_context_effects.py')
    stage=importlib.util.module_from_spec(loader);loader.loader.exec_module(stage)
    cache=t1._cache_dir('cache_t3_core',resolved,sorted(resolved))
    tables=[stage.load_table(cache,name,'shrunk') for name in sorted(resolved)]
    recipe=json.loads((WORK/'recipe_release.json').read_text())
    with np.load(WORK/'effects_t1/effects_A.npz',allow_pickle=False) as z:
        panel=z['targets'].astype(str).tolist();genes=z['genes'].astype(str);baseline=z['lfc'].copy()
    core,core_w=stage.mix(tables,panel,weights=recipe['contexts']['A']['weights'],gamma=1.,reliability_scale=100.)
    shape=core.shape;index={t:i for i,t in enumerate(panel)}
    locators=json.loads((WORK/'private_ko_locators.json').read_text())['files']
    grouped=defaultdict(list);audit=[];read_chunks=[];seen=set()
    mark('KO_context_assembly',chunks=len(plan['chunks']))
    for source in plan['sources']:
        for c in source['contexts']:
            value=np.zeros(shape,dtype=np.float64);mask=np.zeros(shape,dtype=bool);cells=np.zeros(shape[0])
            group_key=(c['identity']['study'],c['identity']['line_group'])
            context_seen=set();profile_cells={}
            for key in c['relevant_chunks']:
                if key in seen:raise ValueError('duplicate KO chunk')
                seen.add(key);spec=plan['chunks'][key];path,route=resolve_chunk(spec,locators)
                with np.load(path,allow_pickle=False) as z:
                    ts=z['targets'].astype(str).tolist()
                    if z['genes'].astype(str).tolist()!=genes.tolist() or ts!=spec['targets']:
                        raise ValueError('KO axes or row inventory differs')
                    if json.loads(str(z['meta']))!=c['identity']:raise ValueError('KO biological identity differs')
                    e=z['shrunk'];m=z['mask'];raw=z['raw'];se=z['se'];n=z['n_cells']
                    if m.dtype!=bool or m.shape!=(len(ts),len(genes)) or not np.array_equal(m,np.isfinite(e)):
                        raise ValueError('KO observed mask differs')
                    if not np.isfinite(raw[m]).all() or not np.isfinite(se[m]).all() or np.any(se[m]<0):
                        raise ValueError('KO raw/SE contract differs')
                    if not np.isfinite(n).all() or np.any(n<10):raise ValueError('KO cell eligibility differs')
                    for row,target in enumerate(ts):
                        if target not in index:continue
                        if target in context_seen:raise ValueError('duplicate context-target')
                        context_seen.add(target);i=index[target]
                        value[i]=np.where(m[row],e[row],0);mask[i]=m[row];cells[i]=n[row]
                        profile_cells[target]=int(n[row])
                read_chunks.append(dict(key=key,sha256=spec['sha256'],bytes=spec['bytes'],route=route))
            if context_seen!=set(c['panel_targets']):raise ValueError('missing KO panel context profiles')
            grouped[group_key].append((value,mask,cells))
            audit.append(dict(unit=source['unit'],identity=c['identity'],donors=c['donors'],
                controls_cells=c['controls_cells'],targets=sorted(context_seen),target_cells=profile_cells,
                measured_pairs=int(mask.sum()),nonzero_pairs=int(np.count_nonzero(value[mask]))))
    if seen!=set(plan['chunks']) or len(audit)!=plan['counts']['ko_contexts']:
        raise ValueError('incomplete KO consumption')
    aggregate=WORK/'ko_tables';aggregate.mkdir()
    groups=[];group_receipts=[]
    for number,(key,contexts) in enumerate(sorted(grouped.items())):
        value,rel=pool_contexts(contexts,shape)
        groups.append((value,rel))
        path=aggregate/('study%02d.npz'%number)
        np.savez_compressed(path,targets=np.asarray(panel),genes=genes,shrunk=value.astype(np.float32),
                            observed=rel>0,reliability=rel,meta=np.asarray(json.dumps(dict(study=key[0],line_group=key[1]))))
        group_receipts.append(dict(study=key[0],line_group=key[1],contexts=len(contexts),
            file=path.relative_to(WORK).as_posix(),sha256=digest(path),bytes=path.stat().st_size,
            targets=[panel[i] for i in np.flatnonzero((rel>0).any(axis=1))],fixed_weight=.25))
    if len(groups)!=plan['counts']['ko_study_lineage_votes']:raise ValueError('KO study vote count differs')
    combined,weights,ko_den=combine(core,core_w,groups,ko_weight=.25)
    eff=combined*1.576;observed=weights>0
    import pandas as pd
    pairs=stage.config.repo_file(recipe['cis']['pairs'])
    cis_model=stage.cis_prior(pd.read_csv(pairs),panel)
    coords=stage.load_coordinates(WORK/'data/external/annotation/gene_coordinates_gencode_v50.tsv')
    stage.add_cis(eff,observed,panel,genes,cis_model,coords,5000,2.)
    eff=eff.astype(np.float32)
    outside=np.array([t not in plan['panel_targets'] for t in panel])
    if not np.array_equal(eff[outside],baseline[outside]):raise ValueError('changed targets outside KO support')
    if not np.isfinite(eff).all() or np.any(eff[~observed]!=0):raise ValueError('final T3 numeric contract differs')
    changed=[panel[i] for i in np.flatnonzero(np.any(eff!=baseline,axis=1))]
    if not changed:raise ValueError('KO arm made no prediction contribution')
    out=WORK/'effects';out.mkdir();effects={}
    for context in ('A','B','C'):
        path=out/('effects_'+context+'.npz')
        np.savez_compressed(path,targets=np.asarray(panel),genes=genes,lfc=eff,observed=observed)
        effects[context]=dict(path=str(path),bytes=path.stat().st_size,sha256=digest(path))
    t1._write(WORK/'recipe_t3.json',dict(protocol=p['protocol'],core_recipe=recipe,policy=plan['policy']))
    receipt=dict(status='T3_effects_ready',utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        protocol=p['protocol'],t1_null_parity=True,crispri_sources=sorted(resolved),
        ko_contexts=audit,ko_study_votes=group_receipts,chunks=read_chunks,effects=effects,
        changed_targets=changed,changed_outside_ko=False,measured_pairs=int(observed.sum()),
        max_ko_fraction=float(np.max(np.divide(ko_den,weights,out=np.zeros_like(weights),where=weights>0))),
        seconds=time.monotonic()-start,not_a_score=True,claims_complete_D053=False,
        controls_unchanged=True,amplitude_and_cis_applied_once=True,emitter_not_yet_applied=True)
    t1._write(WORK/'t3_consumption.json',receipt)
    t1._write(WORK/'t3_complete.json',dict(status='effects_ready',receipt_sha256=digest(WORK/'t3_consumption.json')))
    shutil.rmtree(cache)
    mark('T3_effects_ready',changed_targets=len(changed),groups=len(groups),seconds=receipt['seconds'])
    return effects
