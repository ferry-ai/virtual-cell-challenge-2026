"""Prepare authorized account-specific routes without transferring RNA locally.

Only output-list API calls issue locators; exact NPZ hashes remain enforced by
the destination runtime resolver. Sensitive locator contents never enter Git.
"""
import argparse
from collections import defaultdict
import copy
import json
from pathlib import Path
import subprocess
import sys
from percorso import DATA, HERE, pin, read, sha, write_new, now


def required_files(view, source_names):
    grouped = defaultdict(dict)
    for c in view['chunks']:
        if c['producer'] in source_names:
            value = {k:c[k] for k in ('sha256', 'bytes')}
            if grouped[c['producer']].setdefault(c['producer_file'], value) != value:
                raise ValueError('conflicting chunk pin')
    if set(grouped) != set(source_names):
        raise ValueError('source absent from frozen view')
    return dict(grouped)


def transform_routes(base, old_locators, view, missing, issued, owner):
    """Pure route transformation: original chunks, weights and split stay intact."""
    required = required_files(view, missing)
    additions = {p+'/'+name: data for p, files in required.items() for name, data in files.items()}
    if set(issued) != set(additions):
        raise ValueError('issued locator inventory differs')
    for key, expected in additions.items():
        if any(issued[key].get(k) != v for k,v in expected.items()):
            raise ValueError('issued locator pin differs')
        if not issued[key].get('url', '').startswith('https://'):
            raise ValueError('non-HTTPS locator')
    result = copy.deepcopy(base)
    if not set(missing).issubset(result['kernel_sources']):
        raise ValueError('missing source was not a prior native mount')
    result['kernel_sources'] = [p for p in result['kernel_sources'] if p not in missing]
    for producer, files in required.items():
        source = result['sources'][producer]
        if source['chunks'] != len(files) or source['bytes'] != sum(v['bytes'] for v in files.values()):
            raise ValueError('base source inventory differs')
        source.update(route='authenticated_output_download', private=True)
    locators = copy.deepcopy(old_locators)
    if set(locators['files']) & set(additions):
        raise ValueError('duplicate locator path')
    locators['files'].update(issued)
    locators.update(runtime_owner=owner, utc=now(), never_log_or_commit=True, private=True)
    expected = {c['producer']+'/'+c['producer_file']: c for c in view['chunks']}
    for key, entry in locators['files'].items():
        if key not in expected or any(entry[k] != expected[key][k] for k in ('bytes','sha256')):
            raise ValueError('locator outside frozen view')
    return result, locators


def prepare(plan_path, fold, revision, authorization_path):
    plan = read(plan_path); spec = plan['folds'][fold]; auth = read(authorization_path)
    if auth['plan_sha256'] != sha(plan_path) or not auth.get('human_message_id') or not auth.get('human_answer'):
        raise ValueError('verified specific authorization missing')
    expected_scope = {k:spec[k] for k in ('destination','additional_chunks','additional_bytes')}
    if auth['authorized_folds'][fold] != expected_scope:
        raise ValueError('authorization scope differs')
    for record in (spec['release'], spec['view'], spec['prepared'], spec['access_evidence']):
        if sha(record['path']) != record['sha256']:
            raise ValueError('frozen access plan input changed')
    view = read(spec['view']['path']); required = required_files(view, spec['sources'])
    if sum(len(files) for files in required.values()) != spec['additional_chunks'] or sum(
            v['bytes'] for files in required.values() for v in files.values()) != spec['additional_bytes']:
        raise ValueError('planned chunk budget differs')
    base_record = read(HERE/f'fold_runtime_access_{fold}_r1.json')['runtime_inputs']
    if sha(base_record['path']) != base_record['sha256']:
        raise ValueError('original access record changed')
    base = read(base_record['path'])
    if base['view'] != spec['view'] or sha(base['private_locators']['path']) != base['private_locators']['sha256']:
        raise ValueError('original view or locator file changed')
    old_locators = read(base['private_locators']['path'])
    stage = DATA/'processed/dati_transfer_2026-10-08_01a11c34/runtime_access'/revision
    stage.mkdir(exist_ok=False)
    issued = {}
    for producer, files in sorted(required.items()):
        if producer.split('/')[0] != 'davideferrante11':
            raise ValueError('unexpected source owner')
        prefix = producer.replace('/', '__')
        request = stage/(prefix+'.request.json'); output = stage/(prefix+'.private.json')
        write_new(request, files)
        run = subprocess.run([sys.executable, str(HERE/'prepare_runtime_access.py'), 'issue',
            'davideferrante11', producer, str(request), str(output)], capture_output=True, text=True,
            encoding='utf-8', timeout=300)
        if run.returncode:
            # Never forward an SDK exception or subprocess stream containing a URL.
            raise RuntimeError('private output listing failed for '+producer)
        document = read(output)
        if document['producer'] != producer or document['login_owner'] != 'davideferrante11':
            raise ValueError('issued owner identity differs')
        issued.update({producer+'/'+n:v for n,v in document['files'].items()})
        print(json.dumps(dict(producer=producer, chunks=len(files), locator_listing_complete=True)), flush=True)
    result, locators = transform_routes(base, old_locators, view, set(required), issued, spec['destination'])
    locators.update(authorization=pin(authorization_path), access_plan=pin(plan_path))
    locator_path = stage/'private_locators.json'; write_new(locator_path, locators)
    result.update(utc=now(), runtime_owner=spec['destination'], private_locators=pin(locator_path),
                  authorization=pin(authorization_path), access_plan=pin(plan_path))
    input_path = stage/'runtime_inputs.json'; write_new(input_path, result)
    total = sum(v['bytes'] for v in locators['files'].values())
    if total != spec['additional_bytes'] + spec['already_authorized_private_bytes']:
        raise ValueError('total private access bytes differ')
    report = dict(utc=now(), fold=fold, runtime_owner=spec['destination'], private_only=True,
        view=spec['view'], runtime_inputs=pin(input_path), access_plan=pin(plan_path),
        authorization=pin(authorization_path), native_mounts=len(result['kernel_sources']),
        private_chunks=len(locators['files']), private_bytes=total,
        additional_chunks=spec['additional_chunks'], additional_bytes=spec['additional_bytes'],
        source_visibility_changed=False, local_rna_downloaded_bytes=0,
        runtime_chunk_hashes_verified=False, locators_are_not_data_access_verification=True,
        new_compute_started=False)
    write_new(HERE/f'cross_account_access_{revision}.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--fold', choices=['C-iPSC','J-iPSC'], required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--authorization', type=Path, required=True)
    a = p.parse_args()
    try:
        prepare(a.plan, a.fold, a.revision, a.authorization)
    except Exception as exc:
        print('Cross-account access preparation failed: '+type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
