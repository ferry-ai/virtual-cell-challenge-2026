"""Bind public KOLF pan access to its already verified saved code/version."""
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from pipeline_state import HERE, CONFIG
from verify_public_cd4_v1 import CODE

ref = 'davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1'
env = {k: v for k, v in os.environ.items() if k not in
       ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG['davideferrante11'])
p = subprocess.run([sys.executable, '-c', CODE, ref], env=env,
                   capture_output=True, text=True, timeout=90)
assert p.returncode == 0, 'consumer access failed'
record = json.loads(p.stdout)
proof = next(r for r in json.loads((HERE/'sourcefits_status_r9/verification.json').read_text())['jobs'] if r['job'] == ref)
assert record['version'] == proof['version'] == 1
assert record['is_private'] is False
assert record['source_sha256'] == proof['saved_source_sha256']
payload = {'utc': datetime.now(timezone.utc).isoformat(), 'consumer': 'davideferrante11',
           'no_compute_repeated': True, 'scientific_receipt': str(HERE/'sourcefits_status_r9/verification.json'),
           'jobs': [record]}
with (HERE/'public_kolf_pan_r1/consumer_verified.json').open('x') as f:
    json.dump(payload, f, indent=2)
print(json.dumps(record))
