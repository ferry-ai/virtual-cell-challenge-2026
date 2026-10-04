"""Read-only post-check: removed paths, current Drive presence, and retained inventory."""
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/ferra/vcc2026-data')
evidence = json.loads((HERE / 'local_evidence_manifest.json').read_text(encoding='utf-8-sig'))
inventory_entry = next(r for r in evidence if Path(r['path']).name == 'inventory.json')
inventory_path = Path(inventory_entry['path'])
assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == inventory_entry['sha256']
inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
rows = []
receipts = []
for plan_name, receipt_name in [('plan.json', 'removal.json'), ('tables_plan.json', 'tables_removal.json')]:
    plan_path = HERE / plan_name
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    receipt = json.loads((HERE / receipt_name).read_text(encoding='utf-8-sig'))
    assert receipt['apply'] and receipt['error'] is None
    assert receipt['plan_sha256'].lower() == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    journal = [json.loads(line) for line in (HERE / (receipt_name + '.jsonl')).read_text(encoding='utf-8-sig').splitlines()]
    assert len(journal) == len(plan['rows']) == receipt['removed_paths']
    by_rel = {r['rel']: r for r in journal}
    assert len(by_rel) == len(journal)
    for r in plan['rows']:
        assert by_rel[r['rel']]['sha256'] == r['sha256']
        assert by_rel[r['rel']]['bytes'] == r['bytes']
        assert not Path(r['path']).exists(), r['rel']
        remote = Path(r['remote_path'])
        assert remote.is_file() and remote.stat().st_size == r['bytes'], r['rel']
    rows.extend(plan['rows'])
    receipts.append(receipt)
removed = {r['rel'] for r in rows}
current_physical = {}
for top in ('raw', 'external', 'interim', 'processed', 'kaggle', 'artifacts'):
    for p in (ROOT / top).rglob('*'):
        if p.is_file() and not p.is_symlink():
            s = p.stat()
            current_physical[(s.st_dev, s.st_ino)] = s.st_size
remaining = defaultdict(lambda: {'files': 0, 'bytes_by_path': 0})
kept_missing_or_changed = []
for r in inventory:
    if r['rel'] in removed:
        continue
    p = ROOT / r['rel']
    if not p.is_file() or p.stat().st_size != r['bytes']:
        kept_missing_or_changed.append(r['rel'])
    remaining[r['status']]['files'] += 1
    remaining[r['status']]['bytes_by_path'] += r['bytes']
doc = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'removed_paths': len(rows),
       'removed_unique_bytes': sum(r['expected_unique_bytes'] for r in receipts),
       'removed_bytes_by_path': sum(r['bytes'] for r in rows),
       'all_removed_local_paths_absent': True, 'all_remote_paths_present_same_size': True,
       'kept_missing_or_changed': kept_missing_or_changed, 'kept_inventory_summary': dict(remaining),
       'free_bytes_now': shutil.disk_usage(ROOT).free,
       'remaining_data_unique_bytes': sum(current_physical.values()),
       'free_bytes_before': receipts[0]['free_bytes_before']}
with (HERE / 'postcheck.json').open('x', encoding='utf-8') as f:
    json.dump(doc, f, indent=2)
print(json.dumps(doc, indent=2))
