"""Read authorized seed1/Stack status and bounded reports after completion only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath

KERNELS = {
    'seed1': 'davidmaisterx/vcc-lead-neural-seed1-r1',
    'stack': 'davidmaisterx/vcc-stack-pilot-r1',
}
TERMINAL = {'ERROR', 'COMPLETE', 'CANCEL_ACKNOWLEDGED'}


def download_reports(api, kernel, out):
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    import requests
    out.mkdir()
    record = {'kernel': kernel, 'files': [], 'other_outputs_retained_remotely': [],
              'started_utc': datetime.now(timezone.utc).isoformat()}
    total, token = 0, None
    try:
        with api.build_kaggle_client() as client:
            while True:
                request = ApiListKernelSessionOutputRequest()
                request.user_name, request.kernel_slug = kernel.split('/')
                api._set_paging(request, 200, token)
                response = client.kernels.kernels_api_client.list_kernel_session_output(request)
                if token is None and response.log:
                    (out / 'kernel_static.log').write_text(response.log, encoding='utf-8')
                for item in response.files or []:
                    name = item.file_name
                    pure = PurePosixPath(name.replace('\\', '/'))
                    if pure.is_absolute() or '..' in pure.parts or ':' in name:
                        raise ValueError('Unsafe remote output path')
                    if pure.suffix.lower() not in {'.json', '.csv', '.txt', '.log'}:
                        record['other_outputs_retained_remotely'].append(name)
                        continue
                    target = out / Path(*pure.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    size, digest = 0, hashlib.sha256()
                    try:
                        with requests.get(item.url, stream=True, timeout=60) as response_file:
                            if response_file.status_code != 200:
                                raise RuntimeError(f'HTTP {response_file.status_code} for {name}')
                            with target.open('xb') as stream:
                                for block in response_file.iter_content(chunk_size=1024**2):
                                    total += len(block)
                                    size += len(block)
                                    if size > 10_000_000 or total > 100_000_000:
                                        raise ValueError('Small-report byte bound exceeded')
                                    digest.update(block)
                                    stream.write(block)
                    except requests.RequestException:
                        raise RuntimeError(f'Network failure for {name}; signed URL omitted') from None
                    record['files'].append({'name': name, 'bytes': size,
                                            'sha256': digest.hexdigest()})
                token = response.next_page_token
                if not token:
                    break
        record['complete'] = True
    finally:
        record['downloaded_bytes'] = total
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with (out / 'download_manifest.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
    return {'complete': True, 'files': len(record['files']), 'bytes': total,
            'other_outputs_retained_remotely': len(record['other_outputs_retained_remotely'])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--jobs', nargs='+', choices=KERNELS, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--download-if-terminal', action='store_true')
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    args.out.mkdir(parents=True)
    record = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'jobs': {}}
    try:
        for job in args.jobs:
            kernel = KERNELS[job]
            status = api.kernels_status(kernel).to_dict(ignore_defaults=False)
            result = {'kernel': kernel, 'status': status}
            record['jobs'][job] = result
            if status['status'] in TERMINAL and args.download_if_terminal:
                result['reports'] = download_reports(api, kernel, args.out / job)
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with (args.out / 'snapshot.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
