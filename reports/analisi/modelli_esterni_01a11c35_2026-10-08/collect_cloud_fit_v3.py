"""Bounded retrieval of terminal outputs, with transport diagnostics and no launches."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def classify(text):
    """Return only fixed diagnostic labels, never provider URLs or response bodies."""
    markers = ('WinError 10013', 'WinError 10060', 'WinError 10054', 'NameResolutionError',
               'NewConnectionError', 'ConnectionError', 'ReadTimeout', 'ConnectTimeout',
               'SSLError', 'CERTIFICATE_VERIFY_FAILED', 'ProxyError', 'Unauthorized',
               'Forbidden', 'Not Found', 'PermissionError', 'UnicodeEncodeError',
               'No files found', 'No files matching', 'Max retries exceeded')
    return dict(markers=[m for m in markers if m.lower() in text.lower()],
                http_codes=sorted(set(re.findall(r'\b(?:400|401|403|404|408|429|500|502|503|504)\b', text))),
                characters=len(text))


def main(prepared_path, out, receipt_path):
    prepared = json.loads(prepared_path.read_text())
    if out.exists() or receipt_path.exists():
        raise FileExistsError('new retrieval destination required')
    if out.resolve().is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('large outputs must stay outside Git')
    slug, job = prepared['slug'], prepared['job_id']
    configs = {'davideferrante11': '.kaggle-davideferrante11',
               'davidmaisterx': '.kaggle', 'davideferante': '.kaggle-codex'}
    owner = slug.split('/')[0]
    if owner not in configs or not prepared['private'] or not slug.startswith(owner + '/esm2-'):
        raise ValueError('known private job required')
    env = {k:v for k,v in os.environ.items() if k not in
           ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env.update(KAGGLE_CONFIG_DIR=str(Path.home()/configs[owner]), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    cli = str(Path(sys.executable).with_name('kaggle.exe'))
    def call(args):
        result = subprocess.run([cli, *args], env=env, capture_output=True,
                                encoding='utf-8', errors='replace', timeout=600)
        return result, classify(result.stdout + result.stderr)
    status, status_diag = call(['kernels', 'status', slug])
    state = next((s for s in ('COMPLETE', 'ERROR', 'RUNNING', 'QUEUED')
                  if 'KernelWorkerStatus.' + s in status.stdout), 'UNKNOWN')
    report = dict(utc=datetime.now(timezone.utc).isoformat(), slug=slug, state=state,
                  status_returncode=status.returncode, status_diagnostics=status_diag,
                  output=str(out), training_launched=False, RNA_requested=False)
    if status.returncode == 0 and state in ('COMPLETE', 'ERROR'):
        names = ['complete.json', 'resolution_receipt.json', 'package_preflight.json',
                 'chunk_preflight.json', 'initial_resources.json', 'staging.json', 'real_smoke.json',
                 'fit/manifest.json', 'fit_manifest.json', 'store_manifest.json',
                 'fit/ridge.npz', 'fit/native_predictions.npz', 'progress.jsonl', 'heartbeat.jsonl', 'failure.json']
        pattern = '^' + re.escape(job) + '/(' + '|'.join(map(re.escape, names)) + ')$'
        result, diag = call(['kernels', 'output', slug, '-p', str(out), '--file-pattern', pattern])
        actual = [p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()]
        if set(actual) - ({job+'/'+n for n in names} | {job+'.log'}):
            raise ValueError('unexpected output file')
        report.update(returncode=result.returncode, diagnostics=diag, files=actual)
    with receipt_path.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report), flush=True)
    if report.get('returncode', 1):
        raise RuntimeError('retrieval incomplete; see safe diagnostics')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    a = p.parse_args()
    main(a.prepared, a.out, a.receipt)
