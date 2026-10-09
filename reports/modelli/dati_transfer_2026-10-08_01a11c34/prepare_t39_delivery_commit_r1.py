"""Prepare an exact owned-file commit after T39 delivery, with secret scanning."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
from percorso import HERE, ROOT, pin, write_new, now

trial = 'reports/invii/trial_2026-10-10/'
entry = 'C49E3QzIDZk0LGmXPCPP'
owned = HERE.relative_to(ROOT).as_posix() + '/'
excluded = {owned + 'production_mx_private_access_issued_r1.json'}
paths = set()
for command in (['git', 'diff', '--name-only', '-z', '--'],
                ['git', 'ls-files', '--others', '--exclude-standard', '-z', '--']):
    result = subprocess.run(command + [owned, trial], cwd=ROOT,
                            check=True, capture_output=True)
    for item in result.stdout.split(b'\0'):
        if not item:
            continue
        name = item.decode('utf-8')
        base = Path(name).name
        is_trial_receipt = name.startswith(trial) and (
            base.startswith(('t39_t3_', 'submit_t39_t3_', 'status_' + entry + '_'))
            or base == 'submit_' + entry + '.json')
        if (name.startswith(owned) or is_trial_receipt) and name not in excluded and not name.endswith('.nul'):
            paths.add(name)

problems = []
for name in sorted(paths):
    data = (ROOT / name).read_bytes()
    text = data.decode('utf-16' if data[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig')
    if len(data) > 1_000_000:
        problems.append(dict(path=name, reason='over 1 MB'))
    patterns = [r'https?://[^\s"\']*kaggleusercontent\.com',
                r'"(?:KAGGLE_KEY|api_key|access_token|refresh_token)"\s*:\s*"[^"\s]{12,}"',
                r'"upload_url"\s*:\s*"https?://',
                r'X-Goog-(?:Signature|Credential)=']
    if any(re.search(pattern, text, re.I) for pattern in patterns):
        problems.append(dict(path=name, reason='possible secret or bearer locator'))
if problems:
    print(json.dumps(dict(status='BLOCKED', problems=problems)))
    raise SystemExit(1)
receipt = HERE / 'scoped_commit_t39_delivery_r2.json'
write_new(receipt, dict(utc=now(), status='PASS',
    checks='exact ownership, size, decoded text, credential and locator scan',
    files=[pin(ROOT / name) for name in sorted(paths)],
    explicit_exclusions=sorted(excluded)))
paths.add(receipt.relative_to(ROOT).as_posix())
pathspec = Path(tempfile.gettempdir()) / 'dati_transfer_commit_t39_delivery_r2.nul'
with pathspec.open('xb') as output:
    output.write(b'\0'.join(name.encode('utf-8') for name in sorted(paths)) + b'\0')
print(json.dumps(dict(status='PASS', files=len(paths), pathspec=str(pathspec))))
