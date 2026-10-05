raise SystemExit('one-shot census already recorded in result.md; not a pipeline entry')
import csv
import io
import json
from collections import Counter
from pathlib import Path
import preflight_slots
from reconcile import build_admission

here = Path(__file__).resolve().parent
admission = json.loads((here / 'admission_r3.json').read_text(encoding='utf-8'))
print('OPEN')
for item in admission['open_adapter_ids']:
    print(item)
print('UNION')
for row in admission['units']['units']:
    if row.get('samples_state') == 'remote_complete_union_checked':
        print(row['unit'], row.get('kernel'), row.get('version_ref'))
print('DIFFERS')
for ledger in admission['hipsci']['ledgers']:
    for pair in ledger['planned_slug_differs'][:2]:
        print(pair['planned'], '->', pair['actual'])
    print('n_differs', len(ledger['planned_slug_differs']), 'of', ledger['n'])
root = Path(r'C:/Users/ferra/vcc2026-data/processed/multisource_2026-09-27_r9')
print('CACHE', root.exists(), [p.name for p in root.iterdir()][:12] if root.exists() else [])
for owner in preflight_slots.CONFIG:
    code, text = preflight_slots.call(owner, ['kernels', 'list', '--mine', '--page-size', '100', '--sort-by', 'dateRun', '--csv'])
    rows = list(csv.DictReader(io.StringIO(text))) if code == 0 else []
    fields = rows[0].keys() if rows else []
    status_field = next((name for name in fields if 'status' in name.lower()), None)
    counts = Counter((row.get(status_field) or 'no_status_column') for row in rows) if rows else Counter()
    print('LIST', owner, 'rc', code, 'n', len(rows), 'field', status_field, dict(counts))
