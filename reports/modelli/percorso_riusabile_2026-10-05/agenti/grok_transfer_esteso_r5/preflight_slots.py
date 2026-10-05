"""Fresh CPU-slot preflight. Isolated Kaggle config per account. No kernel push."""
import csv
import io
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CONFIG = {'davideferrante11': '.kaggle-davideferrante11', 'davidmaisterx': '.kaggle',
          'davideferante': '.kaggle-codex'}
SECRET_ENV = {'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN', 'KAGGLE_CONFIG_DIR'}


def call(owner, args):
    env = {key: value for key, value in os.environ.items() if key not in SECRET_ENV}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[owner])
    executable = Path(sys.executable).with_name('kaggle.exe')
    if not executable.exists():
        executable = 'kaggle'
    process = subprocess.run([str(executable), *args], env=env, capture_output=True, text=True, timeout=120)
    return process.returncode, (process.stdout + process.stderr).strip()


def main():
    destination = Path(sys.argv[1])
    page_size = sys.argv[2] if len(sys.argv) > 2 else '20'
    if destination.exists():
        raise SystemExit('preflight destination exists')
    observed = []
    for owner in CONFIG:
        code, text = call(owner, ['kernels', 'list', '--mine', '--page-size', page_size,
                                  '--sort-by', 'dateRun', '--csv'])
        refs = []
        if code == 0:
            refs = [row['ref'] for row in csv.DictReader(io.StringIO(text)) if row.get('ref')]
        else:
            observed.append({'owner': owner, 'job': None, 'returncode': code, 'status': 'list_failed'})
        for job in refs:
            status_code, status = call(job.split('/')[0], ['kernels', 'status', job])
            observed.append({'owner': owner, 'job': job, 'returncode': status_code, 'status': status})
    active = Counter(row['owner'] for row in observed
                     if row['returncode'] or any(token in row['status'] for token in ('RUNNING', 'QUEUED')))
    payload = {'utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               'scope': page_size + ' most recently run kernels per account',
               'active': dict(active), 'observed': observed, 'gpu_requested': False}
    destination.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    print(json.dumps({'active': payload['active'], 'n': len(observed)}))


if __name__ == '__main__':
    main()
