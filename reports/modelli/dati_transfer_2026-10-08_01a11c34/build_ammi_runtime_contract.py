"""Freeze exact NTC parts and proposed inner truth routing, without reading RNA."""
import ast
import base64
import json
from pathlib import Path
import zlib
from percorso import HERE, ROOT, DATA, now, read, pin, sha, write_new


def payload(job):
    if sha(job['code']['path'])!=job['code']['sha256']:raise ValueError('package changed')
    tree=ast.parse(Path(job['code']['path']).read_text())
    p=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(x,ast.Name) and x.id=='P' for x in n.targets))
    return {n:zlib.decompress(base64.b64decode(v['data'])) for n,v in p.items()}


def main():
    release_path=ROOT/'reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json'
    release=read(release_path);contract=read(HERE/'panel_anchor_requests_r1.json')
    validation=read(contract['validation_manifest']['path'])
    axis=pin(DATA/'raw/controls/gene_names.csv')
    if axis['sha256']!=release['axis_sha256']:raise ValueError('axis changed')
    view_record=read(HERE/'training_release_production_r1.json')['view']
    if sha(view_record['path'])!=view_record['sha256']:raise ValueError('view changed')
    aliases={group:lineage for lineage,v in validation['lineages'].items() for group in v['registry_groups']}
    view=read(view_record['path'])
    lineages={c['context_id']:aliases[c['context_group']] for c in view['chunks']}
    jobs=[j for j in read(HERE/'neural_inputs_cloud_prepared_r4.json')['jobs'] if j['slug'].startswith('davidmaisterx/')]
    jobs+=read(HERE/'neural_inputs_cloud_prepared_r5.json')['jobs']
    parts={};contexts=set()
    for job in jobs:
        members=payload(job);config=json.loads(members['job.json'])
        for item in config['parts']:
            p=json.loads(members[item['plan']]);part=p['part_id']
            if part in parts:raise ValueError('duplicate part')
            c=sorted({v['context_id'] for v in p['controls']});contexts.update(c)
            parts[part]=dict(plan_sha256=item['plan_sha256'],job=job['slug'],contexts=c,
                remote_dir='ntc/'+part,completion_remote='ntc/'+part+'/complete.json')
    if contexts!=set(lineages) or len(parts)!=30:raise ValueError('47 context / 30 part coverage differs')
    write_new(HERE/'ammi_ntc_runtime_contract_r1.json',dict(utc=now(),status='EXPECTED_PARTS_NOT_COMPLETION',
        parts=parts,ntc_expected_parts={k:v['plan_sha256'] for k,v in parts.items()},
        ntc_context_lineages=lineages,axis=axis,production_view=view_record,
        all_parts_required=True,global_stratum_reservoir_cap=64,
        normalized_scale='log1p(counts * 10000 / obs.depth_native)',
        access_from_davidmaisterx='native mx outputs; df11 private outputs need an explicit private transfer mechanism',
        numeric_completion_ready=False,all_contexts_count_as_training=False,complete_D053=False))
    for fold_name,fold in contract['folds'].items():
        tables={};routes=[]
        for cid,record in sorted(fold['contexts'].items()):
            if record['role']!='inner_guard':continue
            unit=cid.split(':')[0]
            if fold['inner']=='CD4T':
                condition=unit.split('_',1)[1];table='cd4_'+condition
                spec=release['mix']['cd4_parts'][table]
                source=dict(kind='kernel',ref=release['mix']['kernel'],
                    suffix='cache/'+table+'.npz',**spec)
                role='primary' if condition=='Rest' else 'secondary_condition'
                alignment='same condition; truth pools donors, NTC donor stays distinct; not independent repeated truths'
            else:
                table='k562';entry=release['voted'][table]
                source=dict(kind='dataset',ref=entry['dataset'],file=entry['file'],
                    bytes=entry['bytes'],sha256=entry['sha256'])
                role='cross_assay_pending_independent_review'
                alignment='historical bulk truth versus '+unit+' single-cell NTC; NOT matched samples'
            tables[table]=source
            routes.append(dict(context_id=cid,lineage=fold['inner'],table=table,role=role,
                alignment=alignment,panel_targets_in_training_view=record['panel_target_count']))
        report=dict(utc=now(),fold=fold_name,inner_lineage=fold['inner'],outer_lineage=fold['outer'],
            status='PROPOSED_ROUTING_REQUIRES_VALIDAZIONE',review_status='pending',
            canonical_release=pin(release_path),validation_manifest=contract['validation_manifest'],
            axis=axis,axis_is_external_to_legacy_npz=True,tables=tables,routes=routes,
            pooling='none in DATI outputs; preserve/export each context; no post-result choice',
            primary_statistic='must be frozen by MODEL/VALID before fit; do not count pooled truth reuse as replication',
            outer_truth_included=False,h1_test_included=False,arrays_read=False,
            private_access_from_davidmaisterx_verified=False)
        write_new(HERE/('ammi_inner_truth_'+fold_name+'_r1.json'),report)
    print(json.dumps(dict(parts=30,contexts=47,routing_status='pending independent review',axis_sha256=axis['sha256'])))


if __name__=='__main__':main()
