"""Freeze T0 panel anchors with outer/inner/row-lineage exclusions."""
import copy
import csv
import hashlib
import json
from pathlib import Path
from percorso import HERE, ROOT, DATA, read, pin, sha, now, write_new

VALID=ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08'


def main():
    manifest_path=VALID/'manifest_fold_v1.json'; manifest=read(manifest_path)
    release_path=ROOT/'reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json'
    release=read(release_path)
    recipe_path=ROOT/'reports/invii/trial_2026-10-06/t36_recipe_extbank.json'
    if sha(recipe_path)!=manifest['arms']['T0']['recipe_sha256_production']:
        raise ValueError('T0 production recipe changed')
    recipe=read(recipe_path); sources=set(manifest['arms']['T0']['sources'])
    for context in recipe['contexts'].values():
        if set(context['weights'])!=sources or set(context['weights'].values())!={1.}:
            raise ValueError('T0 source weights differ')
    context_example=next(iter(recipe['contexts'].values()))
    if any(c!=context_example for c in recipe['contexts'].values()):
        raise ValueError('T0 context recipes differ')
    source_groups={}
    group_alias={}
    for lineage,spec in manifest['lineages'].items():
        for group in spec['registry_groups']:group_alias[group]=lineage
        for source in set(spec['tables']) & sources:
            if source in source_groups:raise ValueError('source belongs to multiple lineages')
            source_groups[source]=lineage
    if set(source_groups)!=sources:raise ValueError('T0 source lineage missing')
    panel_path=DATA/'raw/controls/pert_counts.csv'
    if sha(panel_path)!=manifest['panel']['file_sha256']:raise ValueError('panel changed')
    with panel_path.open(newline='') as f:panel=[r['target_gene'] for r in csv.DictReader(f)]
    plans,folds={},{}
    def anchor(excluded):
        key=tuple(sorted(set(excluded)))
        ident='anchor_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:12]
        if ident not in plans:
            admitted=sorted(s for s in sources if source_groups[s] not in key)
            if not admitted:raise ValueError('empty anchor source set')
            one=copy.deepcopy(recipe)
            one['name']=ident
            one['why']='AMMI panel pilot: frozen T0 with explicit outer/inner/row lineage exclusions'
            one['contexts']={ident:dict(amplitude=context_example['amplitude'],weights={s:1. for s in admitted})}
            out=HERE/'panel_anchors/r1/recipes'/(ident+'.json')
            write_new(out,one)
            plans[ident]=dict(id=ident,excluded_lineages=list(key),sources=admitted,recipe=pin(out),
                source_pins={s:release['voted'][s] for s in admitted},
                expected_cache_sha256={s+'.npz':release['voted'][s]['sha256'] for s in admitted})
        return ident
    for fold,outer,inner in [('C-K562','K562','CD4T'),('C-iPSC','iPSC','K562')]:
        release_view=read(HERE/('training_release_'+fold+'_r1.json'))['view']
        if sha(release_view['path'])!=release_view['sha256']:raise ValueError('frozen view changed')
        view=read(release_view['path'])
        contexts={}
        for chunk in view['chunks']:
            lineage=group_alias[chunk['context_group']]
            if lineage==outer:raise ValueError('outer response leaked into frozen view')
            c=contexts.setdefault(chunk['context_id'],dict(lineage=lineage,targets=set()))
            c['targets'].update(set(chunk['targets']) & set(panel))
        query=anchor([outer,inner])
        for cid,c in contexts.items():
            c['role']='inner_guard' if c['lineage']==inner else 'training'
            c['anchor_id']=query if c['role']=='inner_guard' else anchor([outer,inner,c['lineage']])
            c['panel_targets_available']=sorted(c.pop('targets'))
            c['panel_target_count']=len(c['panel_targets_available'])
        folds[fold]=dict(view=release_view,outer=outer,inner=inner,contexts=contexts,
            inner_query_anchor=query,outer_query_anchor=query,
            no_final_refit=True,outer_only_T0_is_separate_comparator=True,
            missing_panel_contexts=[c for c,r in contexts.items() if not r['panel_target_count']])
    report=dict(schema='AMMI-panel-anchor-requests/1',utc=now(),
        status='FROZEN_REQUESTS_NOT_NUMERIC_OUTPUTS',
        protocol=pin(ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08/PROTOCOLLO_AMMI_r2.md'),
        validation_manifest=pin(manifest_path),canonical_release=pin(release_path),
        production_recipe=pin(recipe_path),panel=pin(panel_path),axis=manifest['axis'],
        source_lineages=source_groups,requests=list(plans.values()),folds=folds,
        stage100=pin(ROOT/'scripts/100_build_context_effects.py'),
        invariants=['same common=panel, amplitude, cis, mask and lnFC definition as T0',
            'outer and inner excluded before every statistic; training also excludes row lineage',
            'same inner-excluded anchor for inner and outer queries; no final refit',
            'numeric parity and stage100 actual-consumption manifest required before training'],
        existing_outer_only_references=[pin(VALID/('banco/livello_b_'+f+'_r1/effetti.json')) for f in ('k562','ipsc')],
        new_cloud_job_launched=False,numeric_anchors_ready=False)
    write_new(HERE/'panel_anchor_requests_r1.json',report)
    print(json.dumps(dict(requests=len(plans),folds={k:dict(contexts=len(v['contexts']),
        training=sum(r['role']=='training' for r in v['contexts'].values()),
        missing_panel_contexts=v['missing_panel_contexts']) for k,v in folds.items()})))


if __name__=='__main__':main()
