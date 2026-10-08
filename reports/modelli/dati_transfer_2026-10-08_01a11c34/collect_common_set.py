"""Collect small pinned vectors, then freeze a complete production or T mean set."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from retrieve_common import main as retrieve
from percorso import DATA,HERE,now,pin,read,sha,write_new


def main(regime,revision):
    prod=regime=='production';sources={};missing=[];objects={}
    recipes={name:('alltargets','01a11c34-r3' if prod else '01a11c34-tj2private',name)
        for name in ('hepg2_nadig','jurkat_nadig','rpe1','kolf_chromatin','kolf_metabolic','kolf_pan_genome','kolf_strong','orion_hct116','orion_hek293t')}
    recipes['k562_essential']=('alltargets','01a11c34-r3' if prod else '01a11c34-tj1','k562_essential')
    recipes['h1']=('joint','01a11c34-j2p' if prod else '01a11c34-j2t','h1')
    recipes['hipsci_targeted_19']=('joint','01a11c34-j2p' if prod else '01a11c34-j2t','hipsci_targeted_19')
    recipes['xu2023']=('alltargets','01a11c34-r4private' if prod else '01a11c34-tj1','xu2023')
    recipes['tian2021_crispri']=('alltargets','01a11c34-r3' if prod else '01a11c34-tj1','tian2021_crispri')
    recipes['cd4_mix']=('common_cd4','01a11c34-r1',regime)
    for name,args in recipes.items():
        tag=(('hipsci' if name=='hipsci_targeted_19' else name)+'_'+regime+'_r1')
        evidence_path=HERE/'common_inputs'/(tag+'.json')
        if not evidence_path.exists():
            if len(list((HERE/args[0]/args[1]/args[2]).glob('completion_*/verification.json')))!=1:
                missing.append(name);continue
            retrieve(*args,tag)
        record=read(evidence_path)
        if not record['sha256_verified'] or record['regime']!=regime:raise ValueError('wrong common regime')
        objects[name]=record['output'];sources[name]=dict(object=record['output'],evidence=pin(evidence_path),split=record['split'])
    bulk=read(HERE/'k562_bulk_common_r1.json');objects['k562']=bulk['outputs'][regime]['file']
    sources['k562']=dict(object=objects['k562'],evidence=pin(HERE/'k562_bulk_common_r1.json'),split='target-local bulk effects; hidden rule applied before reduction')
    if missing:
        print('Remaining verified vector gaps:',','.join(missing));return
    expected=set(read(HERE/'release_t1_r1.json')['voted'])
    if set(objects)!=expected:raise ValueError('missing mean source')
    genes=pd.read_csv(DATA/'raw/controls/gene_names.csv').iloc[:,0].astype(str).tolist();arrays={};masks={};support={}
    for name,record in objects.items():
        path=Path(record['path'])
        if sha(path)!=record['sha256']:raise ValueError('common identity changed')
        with np.load(path,allow_pickle=False) as z:
            if z['genes'].astype(str).tolist()!=genes:raise ValueError('common gene axis changed')
            arrays[name]=z['common'];masks[name]=z['mask'];support[name]=z['contributing_targets']
        if arrays[name].shape!=(len(genes),) or not np.isfinite(arrays[name]).all() or masks[name].dtype!=bool:
            raise ValueError('invalid common/mask')
        if not np.array_equal(masks[name],support[name]>0) or (arrays[name][~masks[name]]!=0).any():raise ValueError('unsupported common is not masked')
    folder=DATA/'processed/dati_transfer_2026-10-08_01a11c34/common_sets'/revision;folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/'common.npz',genes=np.asarray(genes),**arrays)
    np.savez_compressed(folder/'support.npz',genes=np.asarray(genes),**support)
    write_new(HERE/('common_release_'+revision+'.json'),dict(utc=now(),regime=regime,sources=sources,
        common=pin(folder/'common.npz'),support=pin(folder/'support.npz'),
        policy='one equal-target masked mean per T1 source; CD4 first mixes conditions per target; no panel fallback',
        fold_safety='For C/J, remove entire held lineage sources before prediction. T/J must use this T set, never production means.',
        claims_complete_corpus=False,not_a_score=True,actual_arrays_independently_rehashed=True))
    print('Frozen complete common set:',regime,len(sources))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('regime',choices=['production','T']);p.add_argument('revision')
    a=p.parse_args();main(a.regime,a.revision)
