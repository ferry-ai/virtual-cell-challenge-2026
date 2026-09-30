"""Retrieve the two authorized Stack pilot H5ADs with producer hashes; no scoring."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

KERNEL = 'davidmaisterx/vcc-stack-variant-b-r1'
NAMES = ['prediction_stack.h5ad', 'prediction_transfer.h5ad']
DATA_ROOT = Path('C:/Users/ferra/vcc2026-data').resolve()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reports', required=True, type=Path,
                    help='Downloaded lead_stack_r1 directory, with completion and prediction hashes')
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(DATA_ROOT / 'interim'):
        raise ValueError('Destination must be new and inside the data-root interim directory')
    completion = json.loads((args.reports / 'completion.json').read_text())
    if completion['status'] != 'generated_no_scores':
        raise ValueError('Inference completion not verified')
    manifest_path = args.reports / 'prediction_hashes.json'
    hashes = json.loads(manifest_path.read_text())
    expected = {name: hashes[name] for name in NAMES}
    total = sum(item['bytes'] for item in expected.values())
    if any(type(v['bytes']) is not int or not 0 < v['bytes'] <= 1024**3 for v in expected.values()):
        raise ValueError('Unreasonable H5AD size in producer manifest')
    if total > 2 * 1024**3 or shutil.disk_usage(DATA_ROOT).free < total + 512 * 1024**2:
        raise ValueError('Insufficient disk reserve or size bound exceeded')
    for item in expected.values():
        digest = item['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Malformed producer SHA256')
    review = json.loads((args.reports / 'runtime_review.json').read_text())
    if review['kernel'] != KERNEL or review['code_archive_sha256'] != 'f61f5799d2b8d1c661a705d60bafeb84b3247e72d015b0ff16b5d266726440b0':
        raise ValueError('Unexpected runtime provenance')
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    import requests
    api = KaggleApi()
    api.authenticate()
    status = api.kernels_status(KERNEL).to_dict(ignore_defaults=False)
    if status['status'] not in {'COMPLETE', 'ERROR'}:
        raise ValueError('Refuse artifacts from an active or unspecified version')
    wanted = {'lead_stack_variant_b_r1/prediction/' + name: name for name in NAMES}
    located, token = {}, None
    with api.build_kaggle_client() as client:
        while True:
            request = ApiListKernelSessionOutputRequest()
            request.user_name, request.kernel_slug = KERNEL.split('/')
            api._set_paging(request, 200, token)
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
            for item in response.files or []:
                if item.file_name in wanted:
                    name = wanted[item.file_name]
                    if name in located:
                        raise ValueError('Duplicate remote artifact')
                    located[name] = item.url
            token = response.next_page_token
            if not token:
                break
    if set(located) != set(NAMES):
        raise ValueError('Both exact remote H5AD paths are required')
    out.mkdir(parents=True)
    record = {'kernel': KERNEL, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'producer_manifest_sha256': sha(manifest_path), 'files': [], 'scores_read': False}
    try:
        for name in NAMES:
            target = out / (name + '.partial')
            size, digest = 0, hashlib.sha256()
            try:
                with requests.get(located[name], stream=True, timeout=60) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f'HTTP {response.status_code} for {name}')
                    with target.open('xb') as stream:
                        for block in response.iter_content(chunk_size=4 * 1024**2):
                            size += len(block)
                            if size > expected[name]['bytes']:
                                raise ValueError('Download exceeds exact producer size')
                            digest.update(block)
                            stream.write(block)
            except requests.RequestException:
                raise RuntimeError(f'Network error for {name}; signed URL omitted') from None
            if size != expected[name]['bytes'] or digest.hexdigest() != expected[name]['sha256']:
                raise ValueError(f'Producer size/hash mismatch: {name}')
            final = out / name
            target.rename(final)
            if sha(final) != expected[name]['sha256']:
                raise ValueError('Readback SHA256 differs')
            record['files'].append({'name': name, 'bytes': size, 'sha256': digest.hexdigest()})
            print(json.dumps(record['files'][-1]), flush=True)
        shutil.copytree(args.reports, out / 'reports')
        record['complete'] = True
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with (out / 'download_manifest.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')


if __name__ == '__main__':
    main()
