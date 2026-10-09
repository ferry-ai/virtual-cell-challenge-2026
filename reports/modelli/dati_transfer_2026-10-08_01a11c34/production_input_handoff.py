"""Inventory existing production inputs; never issue locators or launch work."""
import csv
from collections import Counter
from pathlib import Path
from percorso import HERE, ROOT, read, pin, write_new, now


def main():
    contract = read(HERE / 'panel_anchor_requests_production_r1.json')
    fold = contract['folds']['production']
    view = read(fold['view']['path'])
    assert pin(fold['view']['path'])['sha256'] == fold['view']['sha256']
    with Path(contract['panel']['path']).open(newline='') as stream:
        panel = {r['target_gene'] for r in csv.DictReader(stream)}
    chunks = {c['sha256']: c for c in view['chunks']
              if fold['contexts'][c['context_id']]['role'] == 'training'
              and any(t in panel and t != 'TMEM104' for t in c['targets'])}
    access = read(HERE / 'ammi_private_access_with_ntc_r1.json')
    mounts = read(access['mount_plan']['path'])
    locators = read(access['private_locators']['path'])
    visibility = {s['ref']: s['private'] for s in mounts['sources']}
    visibility.update({s['source']: s['private'] for s in
                       read(HERE / 'production_source_visibility_r1.json')['sources']})
    visibility.update({o['source']: True for o in locators['origins']})
    anchors = read(HERE / 'production_anchors_verified_r1.json')
    official = read(HERE / 'official_ntc_verified_r1.json')
    ntc = read(HERE / 'ntc_ready_manifest_r2.json')
    records = []

    def add(role, source, file, item, local_metadata=False):
        records.append(dict(role=role, source=source, file=file,
            sha256=item['sha256'], bytes=item['bytes'],
            private=visibility[source], local_metadata=local_metadata,
            existing_pilot_locator=item['sha256'] in locators['files']))

    for chunk in chunks.values():
        add('response_chunk', chunk['producer'], chunk['producer_file'], chunk)
    needed = {c['anchor_id'] for c in fold['contexts'].values()} | {fold['outer_query_anchor']}
    visibility[anchors['slug']] = anchors['remote_identity']['is_private']
    for key in sorted(needed):
        a = anchors['anchors'][key]
        add('production_anchor', anchors['slug'], a['remote_path'], a['effects'])
    add('anchor_completion', anchors['slug'], 'anchors/complete.json', anchors['completion'], True)
    visibility[official['slug']] = official['remote_identity']['is_private']
    for group, parts in [('training_ntc', ntc['parts']), ('official_ntc', official['parts'])]:
        for key, part in parts.items():
            source = part.get('job', official['slug'])
            visibility[source] = True
            for name, item in part['files'].items():
                add(group, source, item['remote_path'], item)
            add(group + '_completion', source,
                part.get('completion_remote', 'ntc/' + key + '/complete.json'), part['completion'], True)
    unique = {r['sha256']: r for r in records}

    def summarize(rows):
        rows = list(rows)
        return dict(files=len(rows), bytes=sum(r['bytes'] for r in rows),
                    by_source={s: dict(files=sum(r['source'] == s for r in rows),
                        bytes=sum(r['bytes'] for r in rows if r['source'] == s))
                        for s in sorted({r['source'] for r in rows})})

    accounts = {}
    for owner in ['davideferrante11', 'davidmaisterx']:
        native = [r for r in unique.values() if not r['private'] or r['source'].split('/')[0] == owner]
        cross = [r for r in unique.values() if r not in native]
        accounts[owner] = dict(native_by_ownership_or_public_visibility=summarize(native),
            cross_account_private=summarize(cross),
            cross_account_payload_excluding_packaged_metadata=summarize(r for r in cross if not r['local_metadata']),
            cross_account_with_existing_pilot_locator=summarize(r for r in cross if r['existing_pilot_locator']),
            cross_account_without_existing_pilot_locator=summarize(r for r in cross if not r['existing_pilot_locator']),
            required_kernel_sources=sorted({r['source'] for r in native}),
            cross_account_production_consent_verified=False,
            runtime_mount_and_numeric_hash_checks_still_required=True)
    context_rows = {k: dict(lineage=c['lineage'], panel_targets=len(set(c['panel_targets_available']) - {'TMEM104'}))
                    for k, c in fold['contexts'].items()}
    result = dict(utc=now(), status='METADATA_INVENTORY_ONLY_NOT_LAUNCH_AUTHORIZATION',
        selection_builder=pin(ROOT / 'reports/analisi/modelli_esterni_01a11c35_2026-10-08/build_ammi_runtime_v4.py'),
        inputs={name: pin(HERE / name) for name in [
            'panel_anchor_requests_production_r1.json', 'production_anchors_verified_r1.json',
            'official_ntc_verified_r1.json', 'ntc_ready_manifest_r2.json',
            'ammi_ntc_runtime_contract_r3.json', 'ntc_df11_terminal_verified_r1.json',
            'production_source_visibility_r1.json', 'ammi_private_access_authorization_r1.json']},
        view=fold['view'], coverage=dict(admitted_view_shape=view['response_shape'],
            selected_chunks=len(chunks), selected_chunk_bytes=sum(c['bytes'] for c in chunks.values()),
            training_contexts=len(context_rows), supervised_contexts_before_feature_filter=sum(c['panel_targets'] > 0 for c in context_rows.values()),
            contexts=context_rows, no_panel_supervision=fold['missing_panel_contexts'],
            anchors=sorted(needed), training_ntc_parts=len(ntc['parts']),
            ntc_candidates_before_global_merge=ntc['candidates_before_global_merge'],
            official_contexts=['A', 'B', 'C'], official_ntc_cells=official['cells'],
            complete_D053=False, actual_fit_coverage='must be measured by production runtime'),
        files=records, unique_required=summarize(unique.values()), accounts=accounts,
        existing_locator_receipt=pin(HERE / 'ammi_private_access_with_ntc_r1.json'),
        notes=[
            'No locator values are copied. Existing pilot locators do not authorize production use.',
            'Native classification is based on verified visibility and ownership, not a new mounted-runtime test.',
            'Completion JSONs already exist locally and can be embedded; payload subtotal excludes these.',
            'Full chunk compressed bytes differ from the projected view mmap allocation.',
            'ESM assets and code are inherited from the pinned MODELLI builder; this inventory addresses corpus/NTC/anchors.',
            'Production requires frozen pilot contrasts/decision and exact production transfer authorization.',
            'No new extraction, cloud launch, private download or locator issuance performed.'
        ])
    write_new(HERE / 'production_input_handoff_r1.json', result)
    print(__import__('json').dumps(dict(coverage={k:v for k,v in result['coverage'].items() if k!='contexts'},
        totals={owner:{key: {k:v for k,v in val.items() if k!='by_source'} for key,val in a.items() if isinstance(val,dict)}
                for owner,a in accounts.items()})))


if __name__ == '__main__':
    main()
