"""Reconcile catalogo_r4 with the pinned r7 manifest. Does not assign scientific roles."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from pins import (CATALOGUE, EMISSION, FORBIDDEN_DATASET, HIPSCI_LEDGERS, HIPSCI_STATE,
                  MANIFEST, MANIFEST_SHA256, REPO, SPLIT)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_manifest():
    observed = sha256_file(MANIFEST)
    if observed != MANIFEST_SHA256:
        raise ValueError('r7 manifest hash mismatch')
    return json.loads(MANIFEST.read_text(encoding='utf-8')), observed


def catalogue_items():
    payload = json.loads(CATALOGUE.read_text(encoding='utf-8'))
    items = []
    for section, entries in payload.items():
        for item in entries:
            source_id = item['id'] if isinstance(item, dict) else item[0]
            items.append((section, source_id, item))
    return payload, items


def _tags(section, item):
    if not isinstance(item, dict):
        return ['non_dict_record', 'aggregate_only'] if section == 'aggregate_only' else ['non_dict_record']
    tags = []
    state = str(item.get('state', ''))
    if 'adapter' in item and item.get('adapter') in (None, '', '—', '-'):
        tags.append('open_adapter')
    elif 'adapter' not in item:
        tags.append('adapter_field_absent')
    if 'adattator' in state.lower():
        tags.append('adapter_required_by_state')
    if 'guide' in state and 'nessuna' in state:
        tags.append('missing_guides')
    if 'NTC' in state and 'fuori dal training' in state:
        tags.append('scarce_controls_stated')
    if section == 'aggregate_only':
        tags.append('aggregate_only')
    if 'training' in state:
        tags.append('pilot_mention')
    return tags


def _ledger(path):
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    owners = Counter(row['slug'].split('/')[0] for row in rows)
    differs = []
    for row in rows:
        planned = row.get('original_planned_slug')
        if planned and planned != row['slug']:
            differs.append({'actual': row['slug'], 'planned': planned})
    return {'path': str(path.relative_to(REPO)), 'n': len(rows),
            'accepted': sum(bool(row.get('accepted')) for row in rows),
            'owners': dict(owners), 'planned_slug_differs': differs,
            'actual_slugs': [row['slug'] for row in rows]}


def _hipsci():
    state = json.loads(HIPSCI_STATE.read_text(encoding='utf-8'))
    jobs = state.get('jobs', {})
    verified = [name for name, job in jobs.items()
                if job.get('state') == 'remote_complete_manifest_checked'
                and (job.get('samples') or {}).get('state') == 'remote_complete_manifest_checked'
                and 'count_sum.npz' in (job.get('bank') or {}).get('files', {})]
    units = [{'unit': name, 'expected_parts': unit.get('expected_parts'),
              'verified_parts': unit.get('verified_parts'), 'state': unit.get('state')}
             for name, unit in state.get('units', {}).items()]
    return {'state_path': str(HIPSCI_STATE.relative_to(REPO)),
            'training_ready': state.get('training_ready'),
            'jobs': len(jobs), 'bank_and_samples_verified': len(verified),
            'verified_slugs': verified, 'units': units,
            'consumer_hashes_verified_false': sum(
                not (jobs[name].get('samples') or {}).get('consumer_hashes_verified', False) for name in verified),
            'union_complete': bool(units) and all(
                unit['state'] == 'complete' and unit['verified_parts'] == unit['expected_parts'] for unit in units),
            'ledgers': [_ledger(path) for path in HIPSCI_LEDGERS]}


def _units(manifest):
    counts = Counter()
    consumer = Counter()
    named = []
    for name, info in manifest['units'].items():
        if not isinstance(info, dict) or 'bank' not in info:
            named.append({'unit': name, 'parsed': False})
            continue
        bank = info['bank']
        samples = info.get('samples', {})
        counts['bank:' + str(bank.get('state'))] += 1
        counts['samples:' + str(samples.get('state'))] += 1
        consumer[str(bank.get('consumer_access', samples.get('consumer_access', 'absent')))] += 1
        named.append({'unit': name, 'bank_state': bank.get('state'), 'samples_state': samples.get('state'),
                      'consumer_access': bank.get('consumer_access', samples.get('consumer_access')),
                      'kernel': bank.get('kernel'), 'version_ref': (bank.get('saved_version') or {}).get('version_ref'),
                      'receipt_sha256': bank.get('receipt_sha256')})
    return {'n': len(named), 'counts': dict(counts), 'consumer_access': dict(consumer), 'units': named}


def _find_dataset(node, key):
    if isinstance(node, dict):
        found = node.get(key)
        if isinstance(found, dict) and 'dataset' in found:
            return found
        for value in node.values():
            nested = _find_dataset(value, key)
            if nested:
                return nested
    elif isinstance(node, list):
        for value in node:
            nested = _find_dataset(value, key)
            if nested:
                return nested
    return {}


def write_protocol(path):
    from pins import AMPLITUDE, GAMMA, ORIGINAL_SOURCES, RELIABILITY_SCALE
    payload = {
        'registered_before_results': True,
        'claim': 'decision rule registered before any expanded-bank score',
        'question': 'Does adding eligible sources to the frozen t25 linear transfer change the paired local score under identical t28 emission?',
        'factor': 'source membership only',
        'unchanged': {
            'original_sources': list(ORIGINAL_SOURCES),
            'weight_per_source': 1.0,
            'amplitude': AMPLITUDE,
            'gamma': GAMMA,
            'reliability_scale': RELIABILITY_SCALE,
            'effect': 'shrunk',
            'estimator_for_new_sources': 'effects_from_pseudobulk min_expected 1, constant pseudocount 0.5, matched donor controls, count_sum',
            'emission': dict(EMISSION),
            'split': dict(SPLIT),
        },
        'design': {
            'cells_per_target': 400,
            'paired_seeds': 'generator seed 20260912, indices 0-4',
            'regimes': ['C', 'J'],
            'held_group_controls': 'excluded from the fit',
            'hidden_targets_and_compound_components': 'excluded from every fitting source and derivative',
        },
        'reading': {
            'resolved': 'abs(mean of paired deltas) > 2 * sd / sqrt(5)',
            'members': 'six local scaled members, and the same without Jaccard',
            'favorable_line': 'six-member delta resolved positive, without-Jaccard delta resolved positive, PDS not resolved negative, and the expanded arm local score >= 0.100',
            'early_stop': 'on the first completed held line, a resolved negative expanded_J - original_J stops the remaining lines',
            'loss_is_not_a_decision_metric': True,
            's010': 'more sources are not assumed to be better; a failed rule does not drop the source from the corpus',
            'not_a_vcc_score': True,
            'does_not_promote_a_model': True,
        },
    }
    path.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    return payload


def build_admission():
    manifest, manifest_sha = load_manifest()
    catalogue_sha = sha256_file(CATALOGUE)
    declared = manifest['catalogue_records']['sha256']
    if catalogue_sha != declared:
        raise ValueError('catalogue file hash differs from r7')
    _, items = catalogue_items()
    pinned = manifest['catalogue_records']['records']
    by_id = {row['record_id']: row for row in pinned}
    if len(by_id) != len(pinned):
        raise ValueError('duplicate catalogue record in r7')
    records = []
    for section, source_id, item in items:
        record_id = section + '/' + source_id
        pinned_row = by_id.get(record_id)
        if pinned_row is None:
            raise ValueError('catalogue record missing from r7: ' + record_id)
        if pinned_row['source_record_sha256'] != identity(item):
            raise ValueError('catalogue record hash mismatch: ' + record_id)
        records.append({
            'record_id': record_id,
            'role': pinned_row.get('role'),
            'integration': pinned_row.get('integration'),
            'unit_ref': pinned_row.get('unit_ref'),
            'transfer_source_id': pinned_row.get('transfer_source_id'),
            'exclusion': pinned_row.get('exclusion'),
            'modality': item.get('modality') if isinstance(item, dict) else None,
            'adapter': item.get('adapter') if isinstance(item, dict) else None,
            'catalogue_state': item.get('state') if isinstance(item, dict) else item[-1],
            'tags': _tags(section, item),
        })
    if {row['record_id'] for row in records} != set(by_id):
        raise ValueError('r7 has catalogue records that are not in catalogo_r4')
    hipsci = _hipsci()
    units = _units(manifest)
    unresolved = [row['record_id'] for row in records if row['role'] == 'unresolved']
    open_adapter = [row['record_id'] for row in records
                    if 'open_adapter' in row['tags'] or 'adapter_required_by_state' in row['tags']]
    no_alias = [row['record_id'] for row in records if row['unit_ref'] and not row['transfer_source_id']]
    blockers = []
    if manifest.get('training_ready') is not True:
        blockers.append('r7 training_ready is false')
    if unresolved:
        blockers.append('unresolved roles: ' + str(len(unresolved)) + ' of ' + str(len(records)))
    if open_adapter:
        blockers.append('open adapters: ' + str(len(open_adapter)))
    if no_alias:
        blockers.append('unit_ref without explicit transfer_source_id: ' + str(len(no_alias)))
    if not any(row.get('transfer_source_id') for row in records):
        blockers.append('no catalogue record has an explicit transfer_source_id')
    if hipsci['bank_and_samples_verified'] != 24 or not hipsci['union_complete']:
        detail = ', '.join(unit['unit'] + ' ' + str(unit['verified_parts']) + '/' + str(unit['expected_parts'])
                           + ' ' + str(unit['state']) for unit in hipsci['units'])
        blockers.append('HIPSCI bank+samples verified ' + str(hipsci['bank_and_samples_verified'])
                        + '/24 (' + detail + '); unions incomplete; no new HIPSCI launch from this session')
    if hipsci['consumer_hashes_verified_false']:
        blockers.append('HIPSCI consumer_hashes_verified is false on verified parts')
    ipsc = _find_dataset(manifest, 'private_sample_input')
    if ipsc.get('private') is True:
        blockers.append('iPSC sample input ' + ipsc.get('dataset', '') + ' is private; cross-account mount is not in r7')
    norman = manifest['units'].get('norman2019', {})
    norman_kernel = (norman.get('bank') or {}).get('kernel', '')
    blockers.append('Norman bank receipt is on producer ' + norman_kernel
                    + '; ERROR kernel_source is not treated as data loss and is not mounted from here')
    if FORBIDDEN_DATASET not in json.dumps(manifest.get('legacy_classification', {})):
        blockers.append('forbidden-dataset guard missing from r7')
    blockers.append('source roles and QC are not certified by a closed bank or sample receipt')
    blockers.append('Tahoe is not a catalogo_r4 record and is not authorized by this reconciliation')
    return {
        'utc': datetime.now(timezone.utc).isoformat(),
        'manifest_sha256': manifest_sha,
        'catalogue_sha256': catalogue_sha,
        'fit_admitted': False,
        'blockers': blockers,
        'n_records': len(records),
        'unresolved_roles': len(unresolved),
        'open_adapter_ids': open_adapter,
        'unit_ref_without_transfer_source_id': no_alias,
        'modality_counts': dict(Counter(row['modality'] or 'unspecified' for row in records)),
        'tag_counts': dict(Counter(tag for row in records for tag in row['tags'])),
        'records': records,
        'units': units,
        'hipsci': hipsci,
        'ipsc_private_sample_input': {
            'dataset': ipsc.get('dataset'), 'private': ipsc.get('private'),
            'producer_kernel': (ipsc.get('source') or {}).get('kernel'),
            'receipt_sha256': (ipsc.get('source') or {}).get('receipt_sha256'),
        },
        'forbidden_dataset': FORBIDDEN_DATASET,
        'fit_inputs': [],
        'required_context_ids': [row['record_id'] for row in records],
        'loaded_context_ids': [],
        'expanded_source_names': [],
        'emission': dict(EMISSION),
        'split': dict(SPLIT),
        'hidden_targets': [],
        'claim': 'observed storage reconciliation; not a QC adjudication and not a fit',
    }


def main():
    from pathlib import Path
    here = Path(__file__).resolve().parent
    protocol = here / 'protocol.json'
    admission_path = here / 'admission.json'
    if protocol.exists() or admission_path.exists():
        raise SystemExit('protocol.json or admission.json already exists')
    write_protocol(protocol)
    admission = build_admission()
    admission_path.write_text(json.dumps(admission, indent=1), encoding='utf-8')
    print(json.dumps({'fit_admitted': admission['fit_admitted'], 'n_records': admission['n_records'],
                      'blockers': admission['blockers'],
                      'hipsci_verified': admission['hipsci']['bank_and_samples_verified']}, indent=1))


if __name__ == '__main__':
    main()
