"""Collect only small generation receipts after the frozen private job completes."""
import argparse
import hashlib
import json
from pathlib import Path
import requests
from percorso import HERE, ROOT, read, pin, sha, write_new, now
from quick_generation_cloud import api_for_owner

FOLDER = HERE / 'generation_recovery/r1'
TRIAL = ROOT / 'reports/invii/trial_2026-10-09'
EFFECT_SHA = 'b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6'
WANTED = {
    'generation_manifest.json', 'packaging.json', 'compact_diagnostics.json',
    'generation_stage45_manifest.json', 'manifest_48_package_prediction.json',
    'generation_preflight.json',
}


def verify_receipts(dest, proof):
    manifest = read(dest / 'generation_manifest.json')
    packaging = read(dest / 'packaging.json')
    package = packaging['package']
    diagnostics = read(dest / 'compact_diagnostics.json')
    params = read(Path(proof['params']['path']))
    if sha(Path(proof['params']['path'])) != proof['params']['sha256']:
        raise ValueError('frozen parameters changed')
    if manifest['status'] != 'VCC_READY' or manifest['candidate'] != 'T3-CRISPRi-KO':
        raise ValueError('candidate not ready')
    if manifest['product'] != params['product'] or Path(manifest['product']).name != manifest['product']:
        raise ValueError('unexpected product name')
    for key in ('protocol', 'prediction', 'fit_receipt'):
        if manifest[key] != proof[key] or sha(Path(proof[key]['path'])) != proof[key]['sha256']:
            raise ValueError('frozen evidence changed: ' + key)
    if manifest['source_job'] != proof['source_job'] or manifest['new_fit'] is not False:
        raise ValueError('unexpected scientific refit')
    if manifest['code'] != params['embedded_sha256']:
        raise ValueError('embedded code differs')
    if set(manifest['effects']) != {'A', 'B', 'C'} or any(
        x['sha256'] != EFFECT_SHA or x['bytes'] != 18846035 for x in manifest['effects'].values()
    ):
        raise ValueError('effect identity differs')
    if manifest['packaging_sha256'] != sha(dest / 'packaging.json'):
        raise ValueError('packaging receipt differs')
    if not package['validation']['ok'] or package['validation']['failures']:
        raise ValueError('package validation failed')
    if (package['n_obs'], package['n_vars'], package['archive_bytes']) != (360000, 18533, manifest['bytes']):
        raise ValueError('incomplete package')
    verification = packaging['verification']
    payload = verification['payload_vs_input']
    if (packaging['exit_code'] != 0 or verification['official_container_validator'] != 'passed'
            or not isinstance(payload, dict) or payload.get('matches_input') is not True
            or payload.get('x_arrays_bit_identical') is not True
            or verification['archive_sha256'] != manifest['sha256']
            or verification['archive_bytes'] != manifest['bytes']):
        raise ValueError('independent archive verification failed')
    shape = diagnostics['shape']
    if (shape['n_perturbations'], shape['cells_per_pert'], shape['n_cells'], shape['contexts']) != (300, 400, 360000, ['A', 'B', 'C']):
        raise ValueError('incomplete generation')
    if diagnostics['is_pilot'] or diagnostics['context_provenance_ok'] is not True or diagnostics['seed'] != 20260912:
        raise ValueError('generation contract differs')
    return manifest


def main(label, folder=FOLDER):
    global FOLDER
    FOLDER=folder
    proof = read(FOLDER / 'prepared.json')
    api = api_for_owner(proof['owner'])
    status = str(api.kernels_status(proof['slug']).status)
    if status.rsplit('.', 1)[-1].upper() != 'COMPLETE':
        print(json.dumps(dict(status=status, ready=False)))
        return 2
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest, ApiListKernelSessionOutputRequest
    request = ApiGetKernelRequest()
    request.user_name, request.kernel_slug = proof['slug'].split('/')
    with api.build_kaggle_client() as client:
        saved = client.kernels.kernels_api_client.get_kernel(request)
    code_sha = hashlib.sha256(saved.blob.source.replace('\r\n', '\n').encode()).hexdigest()
    if code_sha != proof['code']['sha256'] or not saved.metadata.is_private or saved.metadata.current_version_number != 1:
        raise ValueError('saved producer identity differs')
    request = ApiListKernelSessionOutputRequest()
    request.user_name, request.kernel_slug = proof['slug'].split('/')
    request.page_size = 100
    selected = {}
    while True:
        with api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            if item.file_name not in WANTED:
                continue
            if item.file_name in selected:
                raise ValueError('duplicate receipt')
            selected[item.file_name] = item.url
        if not response.next_page_token:
            break
        request.page_token = response.next_page_token
    if set(selected) != WANTED:
        raise ValueError('required receipts missing: ' + ','.join(sorted(WANTED - set(selected))))
    dest = FOLDER / label
    dest.mkdir(exist_ok=False)
    for name, url in selected.items():
        with requests.get(url, timeout=(30, 60), stream=True) as response:
            response.raise_for_status()
            chunks = []; size = 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError('oversized receipt')
                chunks.append(chunk)
        data = b''.join(chunks)
        text = data.decode('utf-8')
        if 'kaggleusercontent.com' in text or '"url"' in text:
            raise ValueError('sensitive locator in receipt')
        json.loads(text)
        with (dest / name).open('xb') as out:
            out.write(data)
    manifest = verify_receipts(dest, proof)
    report = dict(utc=now(), status='GENERATION_VERIFIED', job=proof['slug'], version=1,
        private=True, saved_code_matches=True, code_sha256=code_sha,
        product=manifest['product'], product_bytes=manifest['bytes'], product_sha256=manifest['sha256'],
        full_shape=[360000, 18533], source_arrays_downloaded=False, product_downloaded=False,
        files={name: pin(dest / name) for name in sorted(WANTED)})
    write_new(dest / 'verification.json', report)
    mappings = {
        'generation_stage45_manifest.json': 't38_manifest_45_generate_prediction.json',
        'compact_diagnostics.json': 't38_generation_diagnostics.json',
        'manifest_48_package_prediction.json': 't38_manifest_48_package_prediction.json',
        'packaging.json': 't38_packaging.json',
        'generation_manifest.json': 't38_generation_manifest.json',
    }
    for src, target in mappings.items():
        with (TRIAL / target).open('xb') as out:
            out.write((dest / src).read_bytes())
    print(json.dumps(report))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    args = parser.parse_args()
    try:
        raise SystemExit(main(args.label))
    except Exception as exc:
        print('Generation receipt collection failed: ' + type(exc).__name__)
        raise SystemExit(1)
