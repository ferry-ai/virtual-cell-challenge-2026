"""Index immutable NTC bundles by scientific input identity; no network or launches."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from percorso import HERE, DATA, read, pin, sha, write_new, now


def cache_identity(plan, producer_code):
    """Exclude storage paths, job names, fold names and training seeds."""
    scientific = dict(schema='ntc-cache-key/1',
        sources=sorted(s['sha256'] for s in plan['sources']),
        bank_rows_sha256=plan['rows']['sha256'],
        controls=plan['controls'], genes=plan['genes'],
        selection=dict(seed=plan['seed'], cap=plan['cells_per_stratum'],
            strata=plan['stratum_columns'], preserve=plan['preserve_columns']),
        denominator=plan['denominator'],
        producer_code={k:producer_code[k] for k in ('ntc_cells.py','run_ntc_extraction.py')})
    encoded = json.dumps(scientific, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def decision(cache_entry, active):
    if cache_entry is not None:
        if cache_entry['status'] != 'COMPLETE_METADATA_VERIFIED':
            raise ValueError('unverified cache entry')
        return 'REUSE_AFTER_CONSUMER_HASH_CHECK'
    return 'AWAIT_ACTIVE_PRODUCER' if active else 'NEEDS_TRIAGE_NO_AUTOMATIC_EXTRACTION'


def build(ready_path, out):
    ready = read(ready_path)
    source_plans = read(HERE/'ntc_extraction_plans_r2.json')
    contract_manifest = read(HERE/'neural_input_contract_manifest_r2.json')
    contract = read(contract_manifest['contract']['path'])
    assert pin(contract_manifest['contract']['path']) == contract_manifest['contract']
    job = read(HERE/'neural_inputs_cloud_prepared_r5.json')['jobs'][0]
    pending_code = {k:job['payload_files'][k]['sha256'] for k in ('ntc_cells.py','run_ntc_extraction.py')}
    heartbeat_path = DATA/'processed/dati_transfer_2026-10-08_01a11c34/df11_watch_r1/heartbeat.json'
    heartbeat = read(heartbeat_path)
    pending = set(ready['pending_parts'])
    assert pending <= set(read(HERE/'ntc_ready_manifest_r1.json')['pending_parts'])
    rows = []; cache = {}; raw_by_part = {}; samples_total = 0
    for item in source_plans['plans']:
        assert pin(item['plan']['path']) == item['plan']
        plan = read(item['plan']['path']); part = item['part_id']
        raw = {s['sha256'] for s in plan['sources']}; raw_by_part[part] = raw
        assert len(raw) == len(plan['sources'])
        old_samples = contract['bank_units'][item['unit']]['sample_receipts']
        sample_hashes = set(); sample_proofs = []; matrix_bytes = 0
        for s in old_samples:
            assert pin(s['receipt']['path']) == s['receipt']
            receipt = read(s['receipt']['path'])
            assert receipt['complete']
            sample_hashes.update(x['source_sha256'] for n,x in receipt['files'].items() if n.startswith('shard_'))
            matrix_bytes += sum(x['bytes'] for n,x in receipt['files'].items() if n.endswith('.npz') and n.startswith('shard_'))
            sample_proofs.append(dict(receipt=s['receipt'], kernel=s['kernel'], levels_all_targets=receipt['levels']))
        if part in pending: samples_total += matrix_bytes
        existing = ready['parts'].get(part)
        code = existing['producer_code'] if existing else pending_code
        key = cache_identity(plan, code)
        entry = None
        if existing:
            assert pin(existing['completion']['path']) == existing['completion']
            completion = read(existing['completion']['path'])
            assert completion['status'] == 'COMPLETE'
            assert completion['plan_sha256'] == existing['plan_sha256']
            assert completion['code'] == code
            for name, value in existing['files'].items():
                assert all(value[k] == completion['files'][name][k] for k in ('bytes','sha256'))
            entry = dict(status='COMPLETE_METADATA_VERIFIED', part_id=part, completion=existing['completion'],
                producer=existing['producer_job'], storage=existing['job'], files=existing['files'],
                expected_contexts=sorted(item['contexts']), producer_code=code,
                full_numeric_hash_verification_required_on_consumer=True)
            if key in cache: raise ValueError('duplicate semantic cache entry')
            cache[key] = entry
        row = dict(part_id=part, unit=item['unit'], cache_key=key,
            action=decision(entry, part in pending and heartbeat['state']=='RUNNING'),
            plan=item['plan'], raw_shards=len(raw), raw_bytes_known=item['raw_bytes_known'],
            raw_sizes_unknown=item['raw_file_sizes_unknown'], control_population=item['control_population'],
            existing_sample_receipts=sample_proofs, existing_sample_matrix_bytes_all_targets=matrix_bytes,
            raw_shards_already_linked_by_existing_samples=len(raw & sample_hashes),
            raw_shards_without_old_sample_link=len(raw - sample_hashes),
            old_sample_native_depth=False,
            old_sample_selection_identical=False,
            old_NTC_count_by_level_not_available_in_completion=True,
            active_producer=job['slug'] if part in pending else None)
        rows.append(row)
    pending_raw = Counter(s for p in pending for s in raw_by_part[p])
    complete_raw = set().union(*(raw_by_part[p] for p in ready['parts']))
    result = dict(utc=now(), schema='reusable-NTC-catalog/1',
        scope='metadata and receipt audit; arrays not downloaded or freshly rehashed',
        ready_manifest=pin(ready_path), extraction_plans=pin(HERE/'ntc_extraction_plans_r2.json'),
        keys_exclude=['runtime_location','job_slug','fit_id','training_seed'],
        keys_include=['source_hashes','bank_rows','control_identity','gene_axis','selection_seed_cap_strata',
            'native_depth_policy','reader_and_extractor_code'],
        cache=cache, parts=rows,
        summary=dict(ready_entries=len(cache), pending_parts=len(pending),
            pending_raw_shards=sum(pending_raw.values()), pending_unique_raw_shards=len(pending_raw),
            duplicated_raw_shards_within_pending=sum(v-1 for v in pending_raw.values()),
            pending_raw_shards_also_in_completed=len(set(pending_raw)&complete_raw),
            pending_existing_sample_matrix_bytes_all_targets=samples_total),
        pending_producer_heartbeat=heartbeat,
        scientific_selection_change_forbidden_without_explicit_amendment=True,
        transition=dict(collection='DATI watcher PID912',
            verified_sentinels=['ntc_df11_terminal_verified_r1.json','ntc_ready_manifest_r2.json'],
            private_locator_issuance_and_cells_training='MODELLI-ESTERNI',
            command_after_completion='ntc_reuse_catalog.py --ready ntc_ready_manifest_r2.json --out ntc_reuse_catalog_r2.json'),
        source_data_downloaded=False, remote_jobs_launched=0, active_job_changed=False)
    write_new(out,result)
    print(json.dumps(result['summary']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--ready',default='ntc_ready_manifest_r1.json')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    build(HERE/args.ready,HERE/args.out)
