"""Explicit per-part producer pins and fold dependencies; no completion claim."""
import hashlib
import json
import ast
import argparse
from build_ammi_runtime_contract import payload
from percorso import HERE,read,pin,write_new,now

p=argparse.ArgumentParser(__doc__);p.add_argument('--revision',default='r2');p.add_argument('--recovery-prepared');args=p.parse_args()
old=read(HERE/'ammi_ntc_runtime_contract_r1.json');parts=old['parts']
jobs=read(HERE/'neural_inputs_cloud_prepared_r5.json')['jobs']+read(HERE/'neural_inputs_cloud_prepared_r6.json')['jobs']
if args.recovery_prepared:jobs+=read(HERE/args.recovery_prepared)['jobs']
for job in jobs:
    members=payload(job)
    for item in json.loads(members['job.json'])['parts']:
        plan=json.loads(members[item['plan']]);part=plan['part_id']
        if parts[part]['plan_sha256']!=item['plan_sha256']:raise ValueError('plan changed during recovery')
        parts[part].update(job=job['slug'],producer_job=job['slug'],producer_code={
            n:hashlib.sha256(members[n]).hexdigest() for n in ('run_ntc_extraction.py','ntc_cells.py')},
            part_role='training',denominator_policy='ingestion_depth_native')
partial=read(HERE/'ntc_mx_partial_verified_r1.json')
original=next(j for j in read(HERE/'neural_inputs_cloud_prepared_r4.json')['jobs'] if j['slug']==partial['slug'])
members=payload(original)
for part in partial['parts']:
    parts[part].update(job='davidmaisterx/dt-ntc-inputs-01a11c34-r6a',producer_job=partial['slug'],
        producer_code={n:hashlib.sha256(members[n]).hexdigest() for n in ('run_ntc_extraction.py','ntc_cells.py')},
        part_role='training',denominator_policy='ingestion_depth_native',
        relocation_requires_receipt='restored_complete.json',producer_completion=partial['parts'][part]['completion'])
if args.recovery_prepared:
    recovered=read(HERE/args.recovery_prepared)
    earlier=read(recovered['partial_verified']['path'])
    original=next(j for j in read(HERE/'neural_inputs_cloud_prepared_r6.json')['jobs'] if j['slug']==earlier['slug'])
    members=payload(original)
    for part in earlier['parts']:
        parts[part].update(job=recovered['jobs'][0]['slug'],producer_job=earlier['slug'],
            producer_code={n:hashlib.sha256(members[n]).hexdigest() for n in ('run_ntc_extraction.py','ntc_cells.py')},
            part_role='training',denominator_policy='ingestion_depth_native',
            relocation_requires_receipt='restored_complete.json',producer_completion=earlier['parts'][part]['completion'])
anchors=read(HERE/'panel_anchor_requests_r1.json');folds={}
for fold,spec in anchors['folds'].items():
    required={c for c,r in spec['contexts'].items() if r['panel_target_count'] or r['role']=='inner_guard'}
    required.update(c for c,l in old['ntc_context_lineages'].items() if l==spec['outer'])
    chosen={p:r['plan_sha256'] for p,r in parts.items() if set(r['contexts'])&required}
    covered={c for p in chosen for c in parts[p]['contexts']}
    if not required<=covered:raise ValueError('fold NTC context missing')
    folds[fold]=dict(required_contexts=sorted(required),ntc_expected_parts=chosen,
        unused_zero_panel_training_contexts=sorted(set(spec['contexts'])-required),
        storage_parts_may_also_contain_nontraining_contexts=sorted(covered-required),
        all_catalog_extractions_preserved=True)
baseline=payload(read(HERE/'neural_inputs_cloud_prepared_r6.json')['jobs'][0])['ntc_cells.py']
def body(code,name):return ast.dump(next(x for x in ast.parse(code).body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
for name in ('normalized_batch','merge_candidates'):
    if body(baseline,name)!=body((HERE/'ntc_cells.py').read_bytes(),name):raise ValueError('normalization/merge changed')
reader=HERE/'ntc_normalization_r1/ntc_cells.py';reader.parent.mkdir(exist_ok=True)
if reader.exists():
    if reader.read_bytes()!=baseline:raise ValueError('frozen normalization reader changed')
else:
    with reader.open('xb') as f:f.write(baseline)
old.update(utc=now(),status='EXPECTED_PARTS_NOT_COMPLETION',parts=parts,folds=folds,
    reader=pin(reader),normalization_and_merge_AST_unchanged=True,previous=pin(HERE/'ammi_ntc_runtime_contract_r1.json'))
write_new(HERE/('ammi_ntc_runtime_contract_'+args.revision+'.json'),old)
print(json.dumps({k:dict(parts=len(v['ntc_expected_parts']),contexts=len(v['required_contexts'])) for k,v in folds.items()}))
