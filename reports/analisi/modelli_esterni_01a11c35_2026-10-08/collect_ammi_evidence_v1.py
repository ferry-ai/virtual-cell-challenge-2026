"""Collect AMMI metadata only; binary integrity and scientific readout stay pending."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

import requests


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def metadata_name(name, slug):
    """No logs, code bundles, RNA, NTC arrays, predictions or model binaries."""
    if name == 'ammi_failure.json':
        return name
    path = PurePosixPath(name)
    if len(path.parts) != 2 or path.parts[0] != slug:
        return None
    fixed = {'complete.json', 'failure.json', 'preflight.json', 'input_audit.json',
             'training_receipt.json', 'epoch1_before_guard.json', 'epoch2_before_guard.json',
             'zero_residual_parity.receipt.json'}
    if path.name in fixed or re.fullmatch(r'query_\d{3}_(native|swapped)(\.receipt|_failed)?\.json', path.name):
        return path.name
    return None


def validate(folder, prepared, inventory):
    """Check producer metadata, never mislabel claimed remote hashes as verified."""
    folder = Path(folder)
    complete = read(folder/'complete.json')
    training = read(folder/'training_receipt.json')
    preflight = read(folder/'preflight.json')
    template_path = Path(prepared['template']['path'])
    if digest(template_path) != prepared['template']['sha256']:
        raise ValueError('prepared template changed')
    template = read(template_path)
    if (complete['status'] != 'COMPLETE' or complete['fold'] != prepared['fold']
            or complete['mode'] != prepared['mode'] or complete['seed'] != 17
            or complete['device'] != 'cuda' or complete.get('no_outer_truth_read') is not True):
        raise ValueError('completed fit identity or isolation differs')
    runtime_sha = complete['manifest_sha256']
    if (preflight['manifest_sha256'] != runtime_sha or training['input_receipt_sha256'] != runtime_sha
            or training['device'] != 'cuda' or training['fixture'] is not False
            or training['context_mode'] != prepared['mode'] or training['seed'] != 17
            or digest(folder/'training_receipt.json') != complete['training_receipt_sha256']):
        raise ValueError('training receipt identity differs')
    if [e['epoch'] for e in training['epochs']] != [1, 2] or any(e['guard'].get('pass') is not True for e in training['epochs']):
        raise ValueError('two completed guarded epochs required')
    parity = read(folder/'zero_residual_parity.receipt.json')
    if (parity.get('zero_residual') is not True or parity.get('byte_parity') is not True
            or parity['output_sha256'] != parity['anchor_sha256']):
        raise ValueError('zero residual byte parity absent')
    queries = set(template['queries'])
    exports = {}; result = []
    prefix = prepared['slug'].split('/')[1] + '/'
    for item in complete['exports']:
        key = item['context_id'], item['intervention']
        if key in exports or key[0] not in queries or key[1] not in ('native', 'swapped'):
            raise ValueError('duplicate or unexpected query export')
        if (not re.fullmatch(r'query_\d{3}_'+key[1]+r'\.npz', item['file'])
                or prefix+item['file'] not in inventory):
            raise ValueError('declared export absent from remote inventory')
        claim = item['receipt']
        if (claim['quantity'] != 'ln_fold_change' or claim['emission_scale_applied'] is not False
                or claim['anchor_sha256'] != parity['anchor_sha256']):
            raise ValueError('export anchor/scale differs')
        sidecar = read(folder/Path(item['file']).with_suffix('.receipt.json'))
        if sidecar != claim:
            raise ValueError('export receipt differs from completion')
        exports[key] = item
        result.append(dict(context_id=key[0], intervention=key[1],
            control_context_id=item['control_context_id'], source=prepared['slug'],
            file=prefix+item['file'], bytes=claim['bytes'], sha256=claim['output_sha256'],
            binary_hash_verified=False))
    if {c for c, arm in exports if arm == 'native'} != queries:
        raise ValueError('native query coverage incomplete')
    failed = complete['diagnostic_failures']
    failed_contexts = [f['context_id'] for f in failed]
    swapped = {c for c, arm in exports if arm == 'swapped'}
    if prepared['mode'] == 'cells':
        if (len(set(failed_contexts)) != len(failed_contexts) or set(failed_contexts) & swapped
                or set(failed_contexts) | swapped != queries
                or any(f.get('status') != 'GUARD_FAILED_DIAGNOSTIC_ONLY'
                       or f.get('native_export_preserved') is not True for f in failed)):
            raise ValueError('swapped coverage or diagnostic failure record differs')
    elif swapped or failed:
        raise ValueError('none arm must not invent a swapped intervention')
    checkpoint = complete['checkpoint']
    if prefix+PurePosixPath(checkpoint['path']).name not in inventory:
        raise ValueError('final checkpoint absent')
    return dict(status='METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING', exports=result,
        checkpoint=checkpoint, remote_runtime_manifest_sha256=runtime_sha,
        remote_code_verified=False, scientific_benefit_verified=False,
        swapped_diagnostic_failures=failed, complete_D053=False)


def collect(prepared_path, out, receipt):
    prepared = read(prepared_path); out = Path(out); receipt = Path(receipt)
    if out.exists() or receipt.exists():
        raise FileExistsError('fresh metadata destination required')
    owner, slug = prepared['slug'].split('/')
    if owner != 'davidmaisterx' or prepared.get('private') is not True:
        raise ValueError('authorized private pilot destination required')
    for key in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN'):
        os.environ.pop(key, None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/'.kaggle')
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    service = KaggleApi(); service.authenticate()
    state = str(service.kernels_status(prepared['slug']).status).split('.')[-1]
    if state not in ('COMPLETE', 'ERROR'):
        raise ValueError('terminal job required; no output polling')
    inventory = {}; tokens = set(); token = None
    while True:
        request = ApiListKernelSessionOutputRequest()
        request.user_name = owner; request.kernel_slug = slug; request.page_size = 200
        if token: request.page_token = token
        with service.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            if item.file_name in inventory: raise ValueError('duplicate remote output')
            inventory[item.file_name] = item.url
        token = response.next_page_token
        if not token: break
        if token in tokens: raise ValueError('pagination cycle')
        tokens.add(token)
    out.mkdir(parents=True)
    report = dict(utc=datetime.now(timezone.utc).isoformat(), slug=prepared['slug'],
        remote_state=state, prepared_sha256=digest(prepared_path), files={},
        raw_RNA_downloaded=False, numerical_arrays_downloaded=False, private_urls_persisted=False)
    try:
        for name, url in sorted(inventory.items()):
            local = metadata_name(name, slug)
            if local is None: continue
            path = out/local; size = 0
            with requests.get(url, stream=True, timeout=(15, 60)) as response:
                response.raise_for_status()
                with path.open('xb') as stream:
                    for block in response.iter_content(1 << 20):
                        size += len(block)
                        if size > 20_000_000: raise ValueError('metadata file bound exceeded')
                        stream.write(block)
            read(path)
            report['files'][local] = dict(path=str(path), bytes=size, sha256=digest(path))
        if state == 'COMPLETE':
            report['verification'] = validate(out, prepared, inventory)
            report['status'] = report['verification']['status']
        else:
            report['status'] = 'REMOTE_ERROR_METADATA_PRESERVED_NO_REFIT'
    except Exception as error:
        report.update(status='INCOMPLETE', error_type=type(error).__name__,
            http_status=getattr(getattr(error, 'response', None), 'status_code', None))
    write(receipt, report)
    print(json.dumps(dict(status=report['status'], metadata_files=len(report['files']))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for key in ('prepared', 'out', 'receipt'): parser.add_argument('--'+key, required=True)
    args = parser.parse_args(); collect(args.prepared, args.out, args.receipt)
