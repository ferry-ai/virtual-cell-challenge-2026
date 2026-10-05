import json
from pathlib import Path
s = json.loads(Path(r'reports/modelli/percorso_riusabile_2026-10-05/hipsci_verified_r2/state.json').read_text(encoding='utf-8'))
for name, unit in s['units'].items():
    print(name, {k: unit[k] for k in unit if k != 'jobs'})
