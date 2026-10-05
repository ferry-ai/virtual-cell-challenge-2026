raise SystemExit('one-shot r8 read already recorded in result.md; not a pipeline entry')
import hashlib
import json
from collections import Counter
from pathlib import Path
root = Path(r'reports/modelli/percorso_riusabile_2026-10-05')
manifest = root / 'cloud_catalog_r8/manifest.json'
digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
print('r8', digest)
state = json.loads((root / 'hipsci_verified_r4/state.json').read_text(encoding='utf-8'))
print('keys', sorted(state))
print('training_ready', state.get('training_ready'))
units = state.get('units', {})
for name, unit in units.items():
    print(name, {k: unit[k] for k in unit if k in ('expected_parts', 'verified_parts', 'state', 'union')})
jobs = state.get('jobs', {})
c = Counter(job.get('state') for job in jobs.values())
print('jobs', len(jobs), dict(c))
