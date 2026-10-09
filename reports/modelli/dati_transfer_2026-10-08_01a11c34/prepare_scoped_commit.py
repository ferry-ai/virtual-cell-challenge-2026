"""List owned changed files and reject private locators before a scoped commit."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
from percorso import HERE, ROOT, pin, write_new, now

p = argparse.ArgumentParser()
p.add_argument('label')
p.add_argument('--exclude', action='append', default=[], help='Exact repository-relative path owned by another active session')
a = p.parse_args()
scopes = [HERE.relative_to(ROOT).as_posix(),
          'reports/invii/prediction_t38_2026-10-09', 'reports/invii/trial_2026-10-09']
paths = set()
for command in (['git', 'diff', '--name-only', '-z', '--'],
                ['git', 'ls-files', '--others', '--exclude-standard', '-z', '--']):
    result = subprocess.run(command + scopes, cwd=ROOT, check=True, capture_output=True)
    paths.update(x.decode('utf-8') for x in result.stdout.split(b'\0') if x)
paths = sorted(x for x in paths if not x.endswith('.nul') and x not in set(a.exclude))
problems = []
for name in paths:
    data = (ROOT / name).read_bytes()
    text = data.decode('utf-8-sig')
    if len(data) > 1_000_000:
        problems.append(dict(path=name, reason='over 1MB'))
    if re.search(r'https?://[^\s"\']*kaggleusercontent\.com[^\s"\']*', text, re.I):
        problems.append(dict(path=name, reason='private bearer locator'))
    if re.search(r'"(?:KAGGLE_KEY|api_key|access_token|refresh_token)"\s*:\s*"[^"\s]{12,}"', text, re.I):
        problems.append(dict(path=name, reason='possible credential value'))
if problems:
    print(json.dumps(dict(status='BLOCKED', problems=problems)))
    raise SystemExit(1)
receipt = HERE / ('scoped_commit_' + a.label + '.json')
write_new(receipt, dict(utc=now(), status='PASS', checks='size, UTF-8, private locator and credential value scan',
    files=[pin(ROOT / name) for name in paths], excluded='*.nul; files outside owned scopes',
    explicit_exclusions=a.exclude))
paths.append(receipt.relative_to(ROOT).as_posix())
pathspec = Path(tempfile.gettempdir()) / ('dati_transfer_commit_' + a.label + '.nul')
with pathspec.open('xb') as out:
    out.write(b'\0'.join(x.encode('utf-8') for x in paths) + b'\0')
print(json.dumps(dict(status='PASS', files=len(paths), pathspec=str(pathspec), receipt=str(receipt))))
