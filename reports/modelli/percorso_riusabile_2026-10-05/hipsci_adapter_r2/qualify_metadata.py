"""Qualify existing row metadata; no bank arrays, remote fetch, fit or admission."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve().parent
raw = here.parent/'hipsci_adapter_r1/real_rows_r1/rows.csv'
pin = '6ba1ca45325b2c245d576b8f99b080d5dfbab004e174a61325801ab6980461ac'
if hashlib.sha256(raw.read_bytes()).hexdigest() != pin:
    raise ValueError('row metadata changed')
totals = Counter()
with raw.open(encoding='utf-8', newline='') as f:
    for row in csv.DictReader(f):
        target = row['target']
        role = {'NTC':'controls', 'UNASSIGNED':'guide_unassigned',
                'NO_METADATA':'metadata_missing'}.get(target, 'assigned_target_label')
        totals[role] += int(row['n'])
if sum(totals.values()) != 1161865:
    raise ValueError('coverage changed')
payload = dict(metadata_only=True, training_used=False, row_sha256=pin,
               cells_by_observed_label=dict(totals), cells_total=sum(totals.values()),
               unknown_total=totals['guide_unassigned']+totals['metadata_missing'],
               caveat='assigned labels are not proof of QC/crosswalk/fit admission',
               fixture_observed=dict(command='scripts/py.cmd '+
                   'reports/modelli/percorso_riusabile_2026-10-05/hipsci_adapter_r2/test_joint.py',
                   tests=2, exit_code=0, scope='joint pooling and incompatible chemistry; local fixture'),
               fixture_file_hashes={name:hashlib.sha256((here/name).read_bytes()).hexdigest()
                                    for name in ('adapter.py','test_joint.py')})
out = here/'metadata_qualification_r1.json'
if out.exists():
    raise FileExistsError('new evidence destination required')
out.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(totals)))
