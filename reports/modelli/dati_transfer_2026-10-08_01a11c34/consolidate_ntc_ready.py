"""Consolidate verified parts while keeping unfinished coverage explicit."""
from collections import Counter
import csv
import io
import json
import argparse
from build_ammi_runtime_contract import payload
from percorso import HERE,read,pin,sha,write_new,now

p=argparse.ArgumentParser(__doc__);p.add_argument('--df11-report');p.add_argument('--out',default='ntc_ready_manifest_r1.json');args=p.parse_args()
contract=read(HERE/'ammi_ntc_runtime_contract_r3.json');parts={};evidence=[]
names=['ntc_mx_partial_verified_r1.json','ntc_mx_r6a_verified_r1.json','ntc_mx_r6b_verified_r1.json',
       'ntc_mx_r6c_partial_verified_r1.json','ntc_mx_r7a_verified_r1.json']
if args.df11_report:names.append(args.df11_report)
for name in names:
    doc=read(HERE/name);evidence.append(pin(HERE/name))
    if doc['status']!='PASS_METADATA_AND_CODE':raise ValueError('unverified producer')
    for part,record in doc['parts'].items():
        if part in parts:raise ValueError('duplicate completed part')
        expected=contract['parts'][part]
        if expected['plan_sha256']!=record['plan_sha256']:raise ValueError('part plan differs')
        if expected['producer_job']!=doc['slug']:raise ValueError('producer identity differs')
        completion=read(record['completion']['path'])
        if sha(record['completion']['path'])!=record['completion']['sha256']:raise ValueError('receipt changed')
        if completion['code']!=expected['producer_code']:raise ValueError('producer code differs')
        parts[part]={**expected,**record, 'completion_remote':'ntc/'+part+'/complete.json',
                     'numeric_arrays_rehash_required_before_use':True}
for name,ids in [('ntc_mx_restored_verified_r1.json',read(HERE/'ntc_mx_partial_verified_r1.json')['parts']),
                 ('ntc_mx_r6c_restored_verified_r1.json',read(HERE/'ntc_mx_r6c_partial_verified_r1.json')['parts'])]:
    doc=read(HERE/name)
    if doc['status']!='PASS' or set(doc['parts'])!=set(ids):raise ValueError('restoration incomplete')
    evidence.append(pin(HERE/name))
    for part in ids:parts[part]['restoration_receipt']=pin(HERE/name)
job=read(HERE/'neural_inputs_cloud_prepared_r7.json')['jobs'][0];members=payload(job)
population={}
for item in json.loads(members['job.json'])['parts']:
    plan=json.loads(members[item['plan']]);part=plan['part_id'];doc=read(parts[part]['completion']['path'])
    rows=list(csv.DictReader(io.StringIO(members[item['rows']].decode())))
    admitted=sum(c['expected_cells'] for c in plan['controls'])
    excluded=sum(int(rows[c['bank_row']].get('zero_depth_excluded') or 0) for c in plan['controls'])
    actual=doc['population_audit']
    if (actual['raw_NTC'],actual['admitted_NTC'],actual['bank_zero_depth_excluded'])!=(admitted+excluded,admitted,excluded):
        raise ValueError('frozen bank eligibility differs')
    population[part]=actual
contexts=Counter()
for record in parts.values():contexts.update(record['contexts'])
pending=sorted(set(contract['parts'])-set(parts))
write_new(HERE/args.out,dict(utc=now(),status=f'PARTS_{len(parts)}_OF_30_METADATA_AND_CODE_VERIFIED',
    contract=pin(HERE/'ammi_ntc_runtime_contract_r3.json'),parts=parts,pending_parts=pending,
    contexts=dict(contexts),candidates_before_global_merge=sum(contexts.values()),
    unique_contexts=len(contexts),evidence=evidence,frozen_bank_population_verified=population,
    source_feature_masks_preserved=True,normalization_reader=contract['reader'],
    raw_RNA_downloaded=False,consumer_hash_verification_required=True,complete_D053=False,
    folds={f:dict(ready=sorted(set(s['ntc_expected_parts'])&set(parts)),
        pending=sorted(set(s['ntc_expected_parts'])-set(parts)),
        all_required_parts_complete=set(s['ntc_expected_parts'])<=set(parts),
        ready_for_training=False,remaining_gate='destination access and consumer full file hash checks') for f,s in contract['folds'].items()}))
print(json.dumps(dict(parts=len(parts),contexts=len(contexts),candidates=sum(contexts.values()),pending=len(pending))))
