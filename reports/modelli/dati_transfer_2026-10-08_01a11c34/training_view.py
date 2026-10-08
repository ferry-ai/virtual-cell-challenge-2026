"""Freeze an explicit, partial, CRISPRi training view from verified receipts.

This reads metadata only. A downstream consumer must rehash each array, check
axes/masks and record actual fit consumption. K562 GWPS shards require joint
count pooling and are deliberately unresolved here, never treated as replicates.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import pandas as pd
from percorso import DATA,HERE,ROOT,now,pin,read,sha,write_new


def build(receipts,output,held_groups=()):
    contexts=[];excluded=[];splits=[];provenance=[];hidden_universe=set()
    axis=DATA/'raw/controls/gene_names.csv';genes=pd.read_csv(axis).iloc[:,0].astype(str).tolist()
    for path in receipts:
        path=Path(path);verification=read(path/'verification.json');receipt=read(path/'effect_release.json')
        if sha(path/'effect_release.json')!=verification['receipt']['sha256']:
            raise ValueError('receipt changed')
        proof=read(path.parent/'prepared.json');params=read(ROOT/proof['stage']/'params.json')
        if receipt['params_sha256']!=proof['params']['sha256'] or receipt['split']!=params['split']:
            raise ValueError('params/split changed')
        if receipt['axis_sha256']!=sha(axis):raise ValueError('gene axis changed')
        split=receipt['split'];splits.append(split)
        hidden_universe.update(split['hidden_targets'])
        if split['regime'] in {'T','J'}:
            labels=params.get('resolved_labels')
            if labels is None:labels=[t for u in params['units'].values() for t in u['resolved_labels']]
            hidden_universe.update(t for t in labels if int(hashlib.sha256(t.encode()).hexdigest(),16)%5==0)
        provenance.append(dict(unit=receipt['unit'],producer=proof['slug'],receipt=pin(path/'effect_release.json'),
            verification=pin(path/'verification.json'),bank=receipt['bank'],split=split))
        for index,c in enumerate(receipt['contexts']):
            identity=c['identity'];reason=None
            if identity['modality']!='CRISPRi':reason='separate_mechanism_arm'
            elif identity['line_group'] in held_groups:reason='held_lineage_before_training'
            elif receipt['unit'] in {'k562_gwps_a','k562_gwps_b'}:reason='joint_count_pooling_required_same_experiment'
            elif c['status']!='derived':reason=c['status']
            if reason:
                excluded.append(dict(unit=receipt['unit'],identity=identity,reason=reason));continue
            cid=receipt['unit']+':'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:16]
            contexts.append(dict(id=cid,identity=identity,receipt=c,parent=receipt,proof=proof))
    if not contexts:raise ValueError('no admitted CRISPRi context')
    if any(s!=splits[0] for s in splits):raise ValueError('do not mix production and T/J derivations')
    effective_split=splits[0]
    if held_groups:
        if len(held_groups)!=1:raise ValueError('use one registered lineage fold per manifest')
        regime='J' if splits[0]['regime']=='T' else 'C'
        foldpath=ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/splits_v1'/f'{regime}-{held_groups[0]}.json'
        effective_split=read(foldpath)
    splitpath=Path(output).with_name(Path(output).stem+'_split.json');write_new(splitpath,effective_split)
    # Equal mass per canonical experiment, then context, then target. H1 train/val
    # partitions belong to the same experiment; duplicated controls never become rows.
    def experiment(identity):
        s=identity['study'];return 'h1_vcc2025' if s in {'h1_vcc2025_train','h1_vcc2025_val'} else s
    counts=Counter(experiment(c['identity']) for c in contexts)
    chunks=[];expected={}
    for c in contexts:
        r=c['receipt'];n=len(r['targets_derived']);expected[c['id']]=n
        weight=1.0/(len(counts)*counts[experiment(c['identity'])]*n)
        offset=0
        for chunk in r['chunks']:
            targets=r['targets_derived'][offset:offset+chunk['targets']];offset+=chunk['targets']
            if set(targets)&hidden_universe:raise ValueError('hidden target reached training view')
            name='effects/'+chunk['file'];object_pin=c['parent']['outputs'][name]
            chunks.append(dict(path='UNRESOLVED_MOUNT/'+c['proof']['slug']+'/'+name,
                sha256=object_pin['sha256'],bytes=object_pin['bytes'],producer=c['proof']['slug'],
                producer_file=name,context_id=c['id'],context_group=c['identity']['line_group'],
                identity=c['identity'],targets=targets,weights=[weight]*len(targets),protected=False))
        if offset!=n:raise ValueError('chunk/target count mismatch')
    releasepath=Path(output).with_name(Path(output).stem+'_inputs.json')
    write_new(releasepath,dict(schema='training-input-release/1',utc=now(),provenance=provenance,
        biological_policy='CD4 donors and HIPSCI clones remain explicit contexts; H1 partitions and K562 storage blocks are jointly reconstructed',
        claims_complete_corpus=False,base_campaign=pin(HERE/'alltargets/01a11c34-r3/inventory.json')))
    spec=dict(schema='external-ridge-chunks/1',utc=now(),genes=genes,axis=pin(axis),modality='CRISPRi',
        regime=effective_split['regime'],split_manifest_sha256=sha(splitpath),split_manifest=pin(splitpath),
        release_sha256=sha(releasepath),release=pin(releasepath),protocol_status='agreed',
        effect_field='shrunk',quantity='natural-log fold change',
        normalization='pseudobulk library fractions over admitted context measured genes; pseudo=.5; z shrink k=4; phi=.2; min_expected=1',
        amplitude_applied=False,cis_applied=False,emitter_applied=False,
        row_weight_policy='equal experiment mass, equal context mass within experiment, equal target mass within context',
        validation_review=dict(status='pending independent comparative validation',manifest=pin(ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/manifest_fold_v1.json')),
        excluded_contexts=sorted(set(held_groups)|set(splits[0]['held_groups'])),
        excluded_targets=sorted(hidden_universe),upstream_split=splits[0],effective_split=effective_split,
        expected_rows_by_context=expected,chunks=chunks,provenance=provenance,excluded=excluded,
        missing_data_policy='NaN outside boolean mask; never a zero response',
        claims_complete_corpus=False,model_fit=False,arrays_independently_rehashed=False,
        state='frozen metadata contract; resolve pinned mounts before staging; partial corpus',
        response_shape=[sum(expected.values()),len(genes)],mmap_bytes=sum(expected.values())*len(genes)*5)
    write_new(output,spec)
    print(json.dumps(dict(shape=spec['response_shape'],contexts=len(expected),chunks=len(chunks),mmap_bytes=spec['mmap_bytes'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('out',type=Path);p.add_argument('receipts',nargs='+',type=Path);p.add_argument('--held-groups',nargs='*',default=[])
    a=p.parse_args();build(a.receipts,a.out,a.held_groups)
