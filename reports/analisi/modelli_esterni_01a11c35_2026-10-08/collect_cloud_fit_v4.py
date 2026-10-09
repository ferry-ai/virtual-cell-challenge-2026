"""Retrieve an exact terminal-output allowlist with visible paging and bounded HTTPS.

Unlike the CLI, this streams downloads, sets transport timeouts, and never prints
signed URLs, provider logs, arbitrary exception bodies or private input locators.
No training, publication, source download or changes to remote objects.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

CONFIG = {'davideferrante11': '.kaggle-davideferrante11',
          'davidmaisterx': '.kaggle', 'davideferante': '.kaggle-codex'}
NAMES = ('complete.json', 'resolution_receipt.json', 'package_preflight.json',
         'chunk_preflight.json', 'initial_resources.json', 'staging.json', 'real_smoke.json',
         'fit/manifest.json', 'fit_manifest.json', 'store_manifest.json',
         'fit/ridge.npz', 'fit/native_predictions.npz', 'progress.jsonl', 'heartbeat.jsonl', 'failure.json')


def safe_error(exc):
    response = getattr(exc, 'response', None)
    return {'type': type(exc).__name__, 'http_status': getattr(response, 'status_code', None)}


def main(prepared_path, out, receipt):
    prepared = json.loads(prepared_path.read_text())
    owner, slug = prepared['slug'].split('/')
    job = prepared['job_id']
    if owner not in CONFIG or not prepared['private'] or not slug.startswith('esm2-') or slug != job:
        raise ValueError('known private job required')
    if out.exists() or receipt.exists() or out.resolve().is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('new destination outside repository required')
    for key in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN'):
        os.environ.pop(key, None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    import requests
    api = KaggleApi(); api.authenticate()
    report = dict(utc=datetime.now(timezone.utc).isoformat(), slug=prepared['slug'],
                  out=str(out), files=[], pages=0, errors=[], training_launched=False,
                  private_locators_persisted=False, RNA_requested=False)
    try:
        state = str(api.kernels_status(prepared['slug']).status).split('.')[-1]
        report['state'] = state
        if state not in ('COMPLETE', 'ERROR'):
            raise ValueError('terminal job required')
        selected, token, tokens = {}, None, set()
        allowed = {job + '/' + n for n in NAMES}
        while True:
            request = ApiListKernelSessionOutputRequest()
            request.user_name = owner; request.kernel_slug = slug; request.page_size = 200
            if token: request.page_token = token
            for attempt in range(3):
                try:
                    with api.build_kaggle_client() as client:
                        response = client.kernels.kernels_api_client.list_kernel_session_output(request)
                    break
                except Exception as exc:
                    report['errors'].append(dict(stage='list', **safe_error(exc)))
                    if attempt == 2: raise RuntimeError('output listing failed') from None
                    time.sleep(2 ** attempt)
            report['pages'] += 1
            for item in response.files or []:
                if item.file_name in allowed:
                    if item.file_name in selected: raise ValueError('duplicate output name')
                    selected[item.file_name] = item.url
            print(json.dumps(dict(stage='list', page=report['pages'], selected=len(selected))), flush=True)
            token = response.next_page_token
            if not token: break
            if token in tokens: raise ValueError('repeated pagination token')
            tokens.add(token)
        required = {job+'/'+n for n in ('complete.json', 'resolution_receipt.json', 'fit/manifest.json',
                                      'fit/ridge.npz', 'fit/native_predictions.npz')}
        if state == 'COMPLETE' and not required.issubset(selected):
            raise ValueError('required terminal output absent')
        out.mkdir(parents=True, exist_ok=False)
        for name, url in sorted(selected.items(), key=lambda kv: (kv[0].endswith('.npz'), kv[0])):
            path = out/name; path.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(3):
                partial = path.with_name(path.name + '.attempt' + str(attempt) + '.partial')
                count, digest = 0, hashlib.sha256()
                try:
                    with requests.get(url, stream=True, timeout=(15, 60)) as response:
                        response.raise_for_status()
                        expected = response.headers.get('Content-Length')
                        with partial.open('xb') as dest:
                            for block in response.iter_content(1 << 20):
                                dest.write(block); digest.update(block); count += len(block)
                    if expected and count != int(expected): raise ValueError('content length mismatch')
                    partial.rename(path)
                    break
                except Exception as exc:
                    report['errors'].append(dict(stage='download', file=name, attempt=attempt, **safe_error(exc)))
                    print(json.dumps(report['errors'][-1]), flush=True)
                    if attempt == 2: raise RuntimeError('bounded download failed') from None
                    time.sleep(2 ** attempt)
            report['files'].append(dict(file=name, bytes=count, sha256=digest.hexdigest()))
            print(json.dumps(dict(stage='downloaded', **report['files'][-1])), flush=True)
        report['status'] = 'RETRIEVED_NOT_SCIENTIFICALLY_VERIFIED'
    except Exception as exc:
        report['status'] = 'INCOMPLETE'
        report['errors'].append(dict(stage='final', **safe_error(exc)))
    finally:
        with receipt.open('x', encoding='utf-8') as f: json.dump(report, f, indent=2)
    print(json.dumps(dict(status=report['status'], files=len(report['files']), errors=report['errors'])), flush=True)
    return 0 if report['status'].startswith('RETRIEVED') else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(main(a.prepared, a.out, a.receipt))
