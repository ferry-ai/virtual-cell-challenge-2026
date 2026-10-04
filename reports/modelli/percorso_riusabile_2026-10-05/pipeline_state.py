"""Reconcile catalogue and existing cloud outputs without rebuilding or copying arrays.

This is a metadata supervisor, not a launcher or a scientific eligibility classifier.
Every catalogue record survives, including duplicates and unresolved candidates.
"""
import argparse
import ast
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CAMPAIGN = HERE.parent / 'ibrido_esecuzione_2026-10-04'
CATALOGUE = REPO / 'reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r4/catalogo.json'
COVERAGE = REPO / 'reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/copertura_cd4_r2.json'
CONFIG = {'davideferrante11': '.kaggle-davideferrante11', 'davidmaisterx': '.kaggle', 'davideferante': '.kaggle-codex'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def frozen_code(launch):
    path = CAMPAIGN/'stages'/launch['slug'].split('/')[1]/'run.py'
    source = path.read_text(encoding='utf-8')
    # launch.py hashes source text before Windows write_text expands LF to CRLF.
    if hashlib.sha256(source.encode()).hexdigest() != launch['code_sha256']:
        raise ValueError('frozen launcher changed')
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'P' for t in node.targets):
            payload = ast.literal_eval(node.value)
            return {k: payload[k]['sha256'] for k in ('bank.py', 'preparation.py')}
    raise ValueError('missing frozen source payload')


def catalogue_records(catalogue):
    records = []
    for section, entries in catalogue.items():
        for item in entries:
            source_id = item['id'] if isinstance(item, dict) else item[0]
            records.append({'record_id': section + '/' + source_id, 'source_id': source_id,
                            'catalogue_section': section, 'source_record_sha256': identity(item),
                            'role': 'unresolved', 'integration': 'not_reconciled',
                            'exclusion': None})
    if len({r['record_id'] for r in records}) != len(records):
        raise ValueError('duplicate catalogue record identity')
    return records


def command(job, args, timeout=30):
    owner = job.split('/')[0]
    try:
        p = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), 'kernels', *args, job],
                           env={**os.environ, 'KAGGLE_CONFIG_DIR': str(Path.home()/CONFIG[owner])},
                           capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
        return {'returncode': p.returncode, 'text': (p.stdout+p.stderr).strip()}
    except subprocess.TimeoutExpired as e:
        raw = e.stdout or b''
        return {'returncode': None, 'timeout': True,
                'text': raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw}


def complete_receipts(owner, job, out):
    """Download only small completion manifests, never bank arrays or raw shards."""
    import requests
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest, ApiGetKernelRequest
    api = KaggleApi()
    api.authenticate()
    request = ApiGetKernelRequest()
    request.user_name = owner
    request.kernel_slug = job.split('/')[1]
    with api.build_kaggle_client() as client:
        saved = client.kernels.kernels_api_client.get_kernel(request)
    version = saved.metadata.current_version_number
    if version <= 0 or not saved.metadata.is_private:
        raise ValueError('expected a saved private notebook version')
    provenance = {'kernel_id': saved.metadata.id, 'version': version,
                  'private': saved.metadata.is_private,
                  'version_ref': job+'/versions/'+str(version),
                  'saved_source_sha256': hashlib.sha256(saved.blob.source.encode()).hexdigest()}
    token = None
    receipts = {}
    remote_files = {}
    while True:
        req = ApiListKernelSessionOutputRequest()
        req.user_name = owner
        req.kernel_slug = job.split('/')[1]
        req.page_size = 100
        if token:
            req.page_token = token
        with api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.list_kernel_session_output(req)
        for item in response.files or []:
            name = item.file_name
            remote_files[name] = True
            if name.startswith('bank/') and name.endswith('/complete.json'):
                # A metadata response unexpectedly exceeding 1 MiB is rejected before parsing.
                with requests.get(item.url, stream=True, timeout=(20, 30)) as r:
                    r.raise_for_status()
                    chunks = bytearray()
                    for chunk in r.iter_content(65536):
                        chunks.extend(chunk)
                        if len(chunks) > 1 << 20:
                            raise ValueError('oversized completion metadata')
                value = json.loads(chunks)
                if Path(name).parts != ('bank', value['unit'], 'complete.json'):
                    raise ValueError('unexpected unit path')
                target = out / owner / job.split('/')[1] / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as f:
                    f.write(chunks)
                receipts[value['unit']] = (value, target.relative_to(REPO).as_posix(), sha(target))
        token = response.next_page_token
        if not token:
            break
    with api.build_kaggle_client() as client:
        after = client.kernels.kernels_api_client.get_kernel(request)
    if (after.metadata.current_version_number != version
        or after.blob.source != saved.blob.source):
        raise ValueError('saved version changed while inspecting outputs')
    provenance['version_stable_during_output_read'] = True
    return receipts, remote_files, provenance


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--remote', action='store_true')
    args = p.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    records = catalogue_records(json.loads(CATALOGUE.read_text()))
    coverage = json.loads(COVERAGE.read_text())['units']
    launches = {}
    for line in (CAMPAIGN/'launches.jsonl').read_text().splitlines():
        r = json.loads(line)
        if r.get('accepted') and 'vcc-bank-cd4-' in r['slug'] and r['slug'].endswith('-r2'):
            if r['slug'] in launches:
                raise ValueError('ambiguous accepted launch')
            launches[r['slug']] = r
    statuses = dict(zip(launches, concurrent.futures.ThreadPoolExecutor(6).map(
        lambda j: command(j, ['status']), launches))) if args.remote else {}
    units = {}
    jobs = []
    for job, launch in launches.items():
        code_identity = frozen_code(launch)
        status = statuses.get(job, {'text': 'not_checked'})
        completed = status.get('returncode') == 0 and 'KernelWorkerStatus.COMPLETE' in status['text']
        running = status.get('returncode') == 0 and 'KernelWorkerStatus.RUNNING' in status['text']
        metadata, remote_files, provenance = ({}, {}, {})
        if completed:
            metadata, remote_files, provenance = complete_receipts(launch['owner'], job, args.out/'receipts')
            if provenance['saved_source_sha256'] != launch['code_sha256']:
                raise ValueError('saved notebook code differs from accepted launch')
        jobs.append({'job': job, 'status': status, 'expected_units': [s['name'] for s in launch['params']['units']]})
        for spec in launch['params']['units']:
            name = spec['name']
            if name in units:
                raise ValueError('unit assigned twice')
            archived = coverage[name]
            raw_receipt = REPO / archived['receipt']
            if sha(raw_receipt) != archived['sha256'] or archived['sha256'] != spec['receipt_sha256']:
                raise ValueError('raw source receipt changed')
            bank = {'state': 'running' if running else 'unverified', 'kernel': job,
                    'relative_path': 'bank/'+name, 'files': {}, 'consumer_access': 'not_verified',
                    'saved_version': provenance}
            if name in metadata:
                receipt, path, digest = metadata[name]
                if (not receipt['complete'] or receipt['source_verification'] != spec['receipt_sha256']
                    or receipt['cells_in'] != spec['cells']
                    or receipt['cells_used'] + receipt['zero_depth_excluded'] != spec['cells']):
                    raise ValueError('bank lineage/cell reconciliation failed: '+name)
                if not all('bank/'+name+'/'+f in remote_files for f in receipt['files']):
                    raise ValueError('bank output missing files: '+name)
                bank.update(state='remote_complete_manifest_checked', receipt=path, receipt_sha256=digest,
                            files=receipt['files'], cells_used=receipt['cells_used'], rows=receipt['rows'])
            elif completed:
                raise ValueError('completed job missing unit receipt: '+name)
            units[name] = {'line_group': 'CD4T', 'source_id': 'cd4_'+name,
                           'raw': {'state': 'verified', 'receipt': archived['receipt'],
                                   'sha256': archived['sha256'], 'cells': spec['cells'],
                                   'kernel_sources': [launch['owner']+'/'+part['job'].replace('_','-') for part in spec['parts']]},
                           'derivation_key': identity({'code': code_identity, 'unit': spec}),
                           'derivation_code': code_identity,
                           'bank': bank, 'samples': {'state': 'locators_only', 'levels': [32,64,128]},
                           'trainer': {'state': 'not_integrated', 'exposure_receipt': None}}
    if set(units) != set(coverage):
        raise ValueError('CD4 unit coverage differs from verified ingestion')
    for record in records:
        if record['source_id'].startswith('cd4_') and record['source_id'][4:] in units:
            record['unit_ref'] = record['source_id'][4:]
            record['integration'] = 'donor_bank_pending_trainer'
    result = {'schema_version': 1, 'utc': datetime.now(timezone.utc).isoformat(),
              'catalogue': {'path': CATALOGUE.relative_to(REPO).as_posix(), 'sha256': sha(CATALOGUE),
                            'records': records, 'note': 'Records are not distinct datasets; roles/aliases need reconciliation.'},
              'units': units, 'jobs': jobs, 'extended_training_ready': False,
              'blockers': ['Reconcile every catalogue record and every eligible biological context.',
                           'Finish pending bank units and verify mounted hashes on consumer runtime.',
                           'Materialize/reuse sampled cell matrices with raw shard lineage.',
                           'Integrate bank and samples into trainer with fold-safe masks and exposure receipts.'],
              'reuse_policy': 'Reuse matching derivation_key and file hashes; no automatic rebuild, download, or launch.',
              'previous_fit': '18 aggregate pilot fits; not donor bank training; evaluation pending.'}
    (args.out/'state.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    print(json.dumps({'units': len(units), 'remote_banks_complete': sum(u['bank']['state'].startswith('remote_complete') for u in units.values()),
                      'catalogue_records_preserved': len(records), 'extended_training_ready': False}))


if __name__ == '__main__':
    main()
