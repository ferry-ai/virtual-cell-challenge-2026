"""Prepare single-lineage-exclusion anchors and exact full T0 query parity."""
import copy
import csv
import hashlib
import json
from build_ammi_runtime_contract import payload
from prepare_neural_inputs_cloud import save_job
from percorso import HERE, ROOT, read, pin, sha, now, write_new


def main():
    def save_record(path,value):
        if path.exists():
            previous=read(path)
            if 'utc' in value:value['utc']=previous['utc']
            if previous!=value:raise ValueError('existing frozen record differs: '+path.name)
        else:write_new(path,value)
    old=next(j for j in read(HERE/'neural_inputs_cloud_prepared_r4.json')['jobs'] if 'ammi-anchors' in j['slug'])
    old_members=payload(old);prior=json.loads(old_members['anchor_requests.json'])
    recipe_path=prior['production_recipe']['path'];recipe=read(recipe_path)
    if sha(recipe_path)!=prior['production_recipe']['sha256']:raise ValueError('production recipe changed')
    release=read(prior['canonical_release']['path']);sources=prior['source_lineages']
    manifest=read(prior['validation_manifest']['path'])
    aliases={g:l for l,v in manifest['lineages'].items() for g in v['registry_groups']}
    view_pin=read(HERE/'training_release_production_r1.json')['view']
    if sha(view_pin['path'])!=view_pin['sha256']:raise ValueError('production view changed')
    view=read(view_pin['path'])
    with open(prior['panel']['path'],newline='') as f:panel={r['target_gene'] for r in csv.DictReader(f)}
    contexts={}
    for chunk in view['chunks']:
        c=contexts.setdefault(chunk['context_id'],dict(role='training',lineage=aliases[chunk['context_group']],targets=set()))
        c['targets'].update(set(chunk['targets'])&panel)
    members={n:b for n,b in old_members.items() if n.startswith(('repo/','data/raw/controls/'))}
    members.update({n:(HERE/n).read_bytes() for n in ('panel_anchor_worker.py','ntc_cells.py','run_ntc_extraction.py')})
    requests=[];amplitude=next(iter(recipe['contexts'].values()))['amplitude']
    def request(ident,excluded,original=False):
        admitted=sorted(s for s,l in sources.items() if l not in excluded)
        value=copy.deepcopy(recipe)
        if not original:
            value['contexts']={ident:dict(amplitude=amplitude,weights={s:1. for s in admitted})}
        path=HERE/'production_anchors/r1/recipes'/(ident+'.json')
        save_record(path,value);members['recipes/'+ident+'.json']=path.read_bytes()
        return dict(id=ident,excluded_lineages=excluded,sources=admitted,recipe=pin(path),
            source_pins={s:release['voted'][s] for s in admitted},
            expected_cache_sha256={s+'.npz':release['voted'][s]['sha256'] for s in admitted})
    lineage_ids={}
    for lineage in sorted({c['lineage'] for c in contexts.values()}):
        ident='production_without_'+lineage
        requests.append(request(ident,[lineage]));lineage_ids[lineage]=ident
    query='production_query';requests.append(request(query,[]))
    for c in contexts.values():
        c.update(anchor_id=lineage_ids[c['lineage']],panel_targets_available=sorted(c.pop('targets')))
        c['panel_target_count']=len(c['panel_targets_available'])
    contract={k:prior[k] for k in ('validation_manifest','canonical_release','production_recipe','panel','axis','source_lineages','stage100','coordinates')}
    contract.update(schema='AMMI-production-anchor-requests/1',utc=now(),requests=requests,
        parity_requests=[request('A',[],original=True)],parity_pairs=[['A',query]],
        execution_protocol='production: training excludes only row lineage; queries full frozen T0; no independent truth guard',
        folds=dict(production=dict(mode='production',outer=None,inner=None,view=view_pin,contexts=contexts,
            outer_query_anchor=query,missing_panel_contexts=[c for c,r in contexts.items() if not r['panel_target_count']])),
        control_destination_labels=['A','B','C'],numeric_anchors_ready=False,complete_D053=False,
        mandate=pin(ROOT/'reports/analisi/lead_piano_2026-10-08/MANDATO_CHIUSURA_ESM2_AMMI_r1.md'))
    path=HERE/'panel_anchor_requests_production_r1.json';save_record(path,contract)
    members['anchor_requests.json']=json.dumps(contract).encode()
    old_meta=read(old['metadata']['path'])
    mounts=[dict(kind=kind,ref=r) for kind,key in [('kernel','kernel_sources'),('dataset','dataset_sources')] for r in old_meta[key]]
    job=save_job('davideferrante11/dt-ammi-production-01a11c34-r1',members,'panel_anchor_worker.py',mounts,'production_r1',True)
    prepared=HERE/'production_anchors_prepared_r1.json'
    write_new(prepared,dict(utc=now(),jobs=[job],contract=pin(path),private_CPU=True,
        previous_tested_worker='neural_inputs_cloud_prepared_r4.json; only protocol label and exact production parity-pair verification added'))
    auth=read(HERE/'neural_inputs_launch_authorization_r3.json')
    auth.update(recorded_utc=now(),jobs=[job['slug']],prepared=pin(prepared),
        request_text='Lead mandate closure ESM2 AMMI: prepare production row-lineage-excluded anchors and full T0 query',
        scope_note='Existing aggregate sources only; CPU private, no fitting, generation or submission')
    write_new(HERE/'production_anchors_authorization_r1.json',auth)
    print(json.dumps(dict(job=job['slug'],requests=len(requests),contexts=len(contexts),parity=1)))


if __name__=='__main__':main()
