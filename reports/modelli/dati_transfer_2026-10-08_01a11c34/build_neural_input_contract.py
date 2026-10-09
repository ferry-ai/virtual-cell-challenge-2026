"""Inventory frozen neural inputs and control provenance, using metadata only.

No response or cellular array is opened; no new runtime, transfer or fit occurs.
Descriptor values remain unavailable until a dedicated control-only derivation.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from percorso import HERE, ROOT, DATA, BANK, read, sha, pin, now, write_new

REGIMES=('production','T','C-K562','C-iPSC','J-K562','J-iPSC')
FIELDS=('study','line_group','context','condition','modality','chemistry')

def checked(spec):
    path=Path(spec['path'])
    if sha(path)!=spec['sha256']:raise ValueError('metadata pin changed: '+path.name)
    return read(path)

def banks(value):
    return [value] if 'files' in value else list(value.values())

def normalize(row):
    result={key:row[key] for key in FIELDS}
    for key in ('condition','chemistry'):
        if result[key].upper() in ('','MISSING','UNASSIGNED'):
            result[key]='UNREPORTED@'+result['study']
    return result

def main():
    views={r:checked(read(HERE/('training_release_'+r+'_r1.json'))['view']) for r in REGIMES}
    production=views['production']; axis=production['axis']
    if sha(axis['path'])!=axis['sha256']:raise ValueError('gene axis changed')
    registry_path=BANK/'registro_fonti_r1.json';registry=read(registry_path)
    expected_path=ROOT/'reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json'
    if sha(expected_path)!='304e8a660d7f69952c62c2e6ccf3a990da48647a186e179db4584941b4b21a30':
        raise ValueError('canonical expected manifest changed')
    expected=read(expected_path)['expected_storage_units']
    row_state=read(BANK/'rows_r1/state.json')
    row_index={r['sha256']:r for r in row_state['units'] if r['verified']}
    cache={}
    def controls(bank):
        digest=bank['files']['rows.csv']['sha256']
        if digest not in cache:
            record=row_index[digest];path=DATA/'processed/banca_canonica_2026-10-07'/record['path']
            if sha(path)!=digest:raise ValueError('control row metadata changed')
            with path.open(encoding='utf-8',newline='') as f:
                rows=list(csv.DictReader(f))
            cache[digest]=(pin(path),[(i,r) for i,r in enumerate(rows) if r['target']=='NTC' and int(float(r['n']))>0])
        return cache[digest]
    contexts={}
    for view,provenance in [(v,p) for v in (production,views['T']) for p in v['provenance']]:
        receipt=checked(provenance['receipt']);verification=checked(provenance['verification'])
        if verification['receipt']['sha256']!=provenance['receipt']['sha256']:
            raise ValueError('derivation receipt identity differs')
        for context in receipt['contexts']:
            cid=provenance['unit']+':'+hashlib.sha256(json.dumps(context['identity'],sort_keys=True).encode()).hexdigest()[:16]
            if cid not in view['expected_rows_by_context']:continue
            source_banks=banks(provenance['bank']);selections=[]
            joint=len(source_banks)>1
            for bank in source_banks:
                row_pin,ntc=controls(bank)
                aliases=provenance['split'].get('group_aliases',{})
                def matches(row):
                    identity=normalize(row)
                    identity['line_group']=aliases.get(identity['line_group'],identity['line_group'])
                    return identity==context['identity']
                selected=[(i,r) for i,r in ntc if joint or matches(r)]
                selections.append(dict(unit=bank['unit'],rows=row_pin,
                    selection='NTC only; joint canonicalization/dedup required' if joint else 'NTC and exact normalized biological identity',
                    bank_row_indices=[i for i,r in selected],
                    cells_before_joint_dedup=sum(int(float(r['n'])) for i,r in selected),
                    donors=sorted({r['donor_or_clone'] for i,r in selected})))
            observed=sum(s['cells_before_joint_dedup'] for s in selections)
            expected_controls=context['controls_cells']
            if not joint and observed!=expected_controls:
                raise ValueError('NTC metadata count differs: '+cid)
            if cid in contexts:
                if contexts[cid]['source_banks']!=source_banks or contexts[cid]['NTC_rows']!=selections:
                    raise ValueError('same context has different control provenance across folds')
                continue
            contexts[cid]=dict(identity=context['identity'],expected_control_cells=expected_controls,
                derivation_receipt=provenance['receipt'],verified_derivation=provenance['verification'],
                source_banks=source_banks,NTC_rows=selections,
                pooling='reuse pinned joint adapter; H1 controls once, K562 storage parts pooled' if joint else 'pool selected NTC rows within this context',
                joint_adapter_required=joint,control_descriptor='not_derived',
                numeric_control_arrays_rehashed_here=False,cellular_samples_consumed_by_ESM2=False)
    if set(contexts)!=(set(production['expected_rows_by_context'])|set(views['T']['expected_rows_by_context'])):
        raise ValueError('context coverage gap')
    folds={}
    for name,view in views.items():
        ids=sorted(view['expected_rows_by_context'])
        if not set(ids)<=set(contexts):raise ValueError('fold context absent from canonical controls')
        folds[name]=dict(release=pin(HERE/('training_release_'+name+'_r1.json')),
            training_context_ids=ids,excluded_targets_count=len(view['excluded_targets']),
            split=view['split_manifest'],held_context_groups=view['excluded_contexts'],
            response_shape=view['response_shape'],response_mask_policy=view['missing_data_policy'],
            fit_transform_on='training contexts only; no held responses or fitted statistics',
            query_controls='held controls only if admitted by frozen validation protocol; H1 test remains closed')
    roles={}
    def sample_receipts(node):
        found=[]
        if isinstance(node,dict):
            if isinstance(node.get('receipt'),str) and node.get('receipt_sha256'):
                path=ROOT/node['receipt']
                if not path.is_file() or sha(path)!=node['receipt_sha256']:
                    raise ValueError('sample receipt missing or changed')
                receipt=read(path)
                found.append(dict(receipt=pin(path),kernel=node.get('kernel'),
                    relative_path=node.get('relative_path'),saved_version=node.get('saved_version'),
                    files=receipt.get('files'),levels=receipt.get('levels'),
                    cell_metadata_policy='select exact NTC label and context from shard metadata before RNA reads; verify array and metadata hash together',
                    numeric_shards_rehashed_here=False,remote_access_now='not_checked'))
            else:
                for child in node.values():found.extend(sample_receipts(child))
        elif isinstance(node,list):
            for child in node:found.extend(sample_receipts(child))
        return found
    consumed={b['unit'] for c in contexts.values() for b in c['source_banks']}
    for unit,record in registry['units'].items():
        raw=expected.get(unit,{})
        roles[unit]=dict(study=record['study'],line_groups=record['line_group'],modalities=record['modality'],
            contexts=record['contexts'],donors_or_clones=record['donors_or_clones'],
            bank_cells=record['cells'],bank_metadata=raw.get('bank'),
            samples_metadata=raw.get('samples'),sample_levels=record.get('samples_levels'),
            sample_receipts=sample_receipts(raw.get('samples')),
            sample_bytes=record.get('samples_bytes'),
            samples_access_current='not verified from next training runtime',
            sample_arrays_rehashed_here=False,sample_cells_used_by_ESM2=0,
            current_role='supervision via admitted aggregate effects' if unit in consumed else 'outside frozen CRISPRi view; explicit gap or separate mechanism',
            exclusions=[x for x in production['excluded'] if x['unit']==unit])
    report=dict(schema='neural-context-input-contract/1',utc=now(),status='METADATA_VERIFIED_NUMERIC_DESCRIPTORS_PENDING',
        owner='DATI-TRANSFER',model_owner='MODELLI-ESTERNI',axis=axis,genes=len(production['genes']),
        frozen_view=read(HERE/'training_release_production_r1.json')['view'],
        canonical_registry=pin(registry_path),canonical_storage=pin(expected_path),
        contexts=contexts,folds=folds,bank_units=roles,
        descriptor_contract=dict(required_outputs=['context_id','control_count_sum','n_control_cells','control_mean_counts','control_observed_mask','source_sha256'],
            scope='aggregate controls for provenance and mean-profile ablation; not a substitute for the requested encoder of individual NTC cells',
            raw_unit='non-negative raw UMI counts; no perturbed cells',
            pooling='sum NTC count sums and divide by deduplicated n; retain count sums and n as primary outputs',
            mask='intersection of selected NTC masks only; never response-derived; missing is not zero',
            normalization='raw aggregate first; a log1p library-normalized descriptor requires model protocol freeze before fit',
            forbidden=['target responses in descriptors','global PCA/scaling fitted before fold','H1 test','silent missing-context omission'],
            emission_transforms_applied=False),
        access=dict(evidence='bank inputs pinned and used by verified derivation jobs; metadata rehashed here',
            new_destination_access='must be checked on selected runtime before numeric derivation',
            new_transfers_authorized_by_this_file=False),
        summary=dict(contexts=len(contexts),bank_units=len(roles),raw_NTC_metadata_files_rehashed=len(cache),
            production_contexts=len(production['expected_rows_by_context']),
            context_alias_note='production and T retain their frozen context IDs; HEK293T/HEK293 group alias yields two IDs for one biological context',
            joint_contexts=sum(c['joint_adapter_required'] for c in contexts.values()),
            numeric_control_descriptors_ready=0,cellular_arrays_read=0,complete_D053=False))
    write_new(HERE/'neural_input_contract_r1.json',report)
    print(json.dumps(report['summary']))

if __name__=='__main__':main()
