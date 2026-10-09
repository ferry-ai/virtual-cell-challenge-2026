"""Describe only inputs unavailable natively to the intended private pilot account."""
from collections import defaultdict
from percorso import HERE,ROOT,DATA,read,pin,write_new,now

deps_path=ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08/ammi_input_dependencies_compact_r4.json'
deps=read(deps_path);audit=read(HERE/'ammi_access_audit_r2.json')
account=next(a for a in audit['accounts'] if a['owner']=='davidmaisterx')
access={(a['kind'],a['ref']):a for a in account['sources']}
files={};native=defaultdict(int)
def add(kind,ref,name,size,digest,role,folds):
    if access[(kind,ref)]['native_admissible']:
        native[ref]+=size;return
    key=(kind,ref,name)
    if key in files:
        if files[key]['sha256']!=digest or files[key]['bytes']!=size:raise ValueError('conflicting pin')
        files[key]['folds']=sorted(set(files[key]['folds'])|set(folds));return
    files[key]=dict(source_kind=kind,source=ref,file=name,bytes=size,sha256=digest,role=role,folds=list(folds))
for fold,spec in deps['folds'].items():
    for c in spec['chunks']:add('kernel',c['producer'],c['producer_file'],c['bytes'],c['sha256'],'response_chunk',[fold])
anchors=read(HERE/'ammi_anchors_verified_r1.json');contract=read(HERE/'panel_anchor_requests_r1.json')
for fold,spec in contract['folds'].items():
    ids={r['anchor_id'] for r in spec['contexts'].values()}|{spec['outer_query_anchor'],spec['inner_query_anchor']}
    for ident in ids:
        a=anchors['anchors'][ident];add('kernel',anchors['slug'],a['remote_path'],a['effects']['bytes'],a['effects']['sha256'],'pilot_anchor',[fold])
    doc=read(HERE/('ammi_inner_truth_'+fold+'_r1.json'))
    for t in doc['tables'].values():add(t['kind'],t['ref'],t.get('suffix',t.get('file')),t['bytes'],t['sha256'],'inner_truth',[fold])
p=anchors['completion'];add('kernel',anchors['slug'],'anchors/complete.json',p['bytes'],p['sha256'],'anchor_receipt',list(contract['folds']))
ntc=read(HERE/'ammi_ntc_runtime_contract_r3.json')
pending={part:{k:v[k] for k in ('job','producer_job','plan_sha256','contexts','part_role','denominator_policy')}
    for part,v in ntc['parts'].items() if v['job'].startswith('davideferrante11/') and any(part in s['ntc_expected_parts'] for s in ntc['folds'].values())}
by_source={};by_fold={}
for row in files.values():
    entry=by_source.setdefault(row['source'],dict(bytes=0,files=0,roles=set()))
    entry['bytes']+=row['bytes'];entry['files']+=1;entry['roles'].add(row['role'])
for entry in by_source.values():entry['roles']=sorted(entry['roles'])
for fold in deps['folds']:
    subset=[r for r in files.values() if fold in r['folds']]
    by_fold[fold]=dict(files=len(subset),known_bytes=sum(r['bytes'] for r in subset),
        pending_NTC_parts=sorted(p for p in pending if p in ntc['folds'][fold]['ntc_expected_parts']))
full=DATA/'processed/dati_transfer_2026-10-08_01a11c34/ammi_private_access_r1/plan.json'
write_new(full,dict(utc=now(),destination_account='davidmaisterx',private_only=True,
    files=list(files.values()),pending_NTC_parts=pending,source_access_audit=pin(HERE/'ammi_access_audit_r2.json'),
    features=deps['features'],consumer_dependencies=pin(deps_path),
    use='four private GPU pilot fits C-K562/C-iPSC cells/none seed17',
    runtime_policy='one response chunk staged and hashed at a time, removed after use; NTC CSR mmap; no dense global matrix',
    signed_links_policy='temporary bearer capabilities outside repository/logs; never public; not issued yet',
    production_inputs_excluded=True,public_or_natively_accessible_sources_not_transferred=sorted(native)))
summary=dict(utc=now(),status='PLAN_PARTIAL_PENDING_DF11_NTC_COMPLETION',plan=pin(full),
    destination_account='davidmaisterx',sources=by_source,folds=by_fold,
    unique_known_files=len(files),unique_known_bytes=sum(r['bytes'] for r in files.values()),
    pending_NTC_parts=sorted(pending),pending_NTC_bytes=None,
    already_natively_accessible_producers=sorted(native),
    new_publication=False,source_visibility_changes=False,transfer_executed=False,
    separate_transfer_consent_recorded=False,
    note='No action inferred from access failure: package and exact output pins must be ready before any transfer approval or execution.')
write_new(HERE/'ammi_private_access_plan_r1.json',summary)
print(__import__('json').dumps(dict(known_files=len(files),known_bytes=summary['unique_known_bytes'],pending_NTC_parts=len(pending),sources=by_source)))
