"""Prepare a closed cleanup plan from independent Colab receipts; never delete data."""
import csv
import hashlib
import importlib.util
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/ferra/vcc2026-data')
DRIVE = Path('G:/Il mio Drive/vcc2026/data')
RUN = ROOT / 'processed/archivio_cloud_2026-10-02/r1'
spec = importlib.util.spec_from_file_location('previous', HERE.parent / 'archivio_cloud_2026-10-02/eliminabili.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
proofs = {}
proof_files = []
for name in ('colab_a_r1.jsonl', 'colab_a_r2.jsonl'):
    p = HERE / name
    proof_files.append({'name': name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    for line in p.read_text(encoding='utf-8-sig').splitlines():
        r = json.loads(line)
        if r.get('status') == 'verified' and r.get('sha256') == r.get('expected_sha256') and r.get('bytes') == r.get('expected_bytes'):
            proofs[r['rel']] = {**r, 'receipt': name}
samples = json.loads((ROOT / 'processed/libera_spazio_2026-10-04/colab_opened_r2.json').read_text(encoding='utf-8-sig'))
failed = [r for r in samples if 'error' in r]
(HERE / 'sample_failures.json').write_text(json.dumps(failed, indent=2), encoding='utf-8')
failed_rels = {r['rel'] for r in failed}
old = {r['rel']: r for r in csv.DictReader((RUN / 'local_hashes.tsv').open(encoding='utf-8'), delimiter='\t')}
inventory = []
rows = []
aliases = defaultdict(list)
keep_ext = {'.json', '.jsonl', '.yaml', '.yml', '.md', '.txt', '.log', '.py', '.ps1', '.sh', '.csv', '.tsv'}
for top in ('raw', 'external', 'interim', 'processed', 'kaggle', 'artifacts'):
    for p in sorted((ROOT / top).rglob('*')):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(ROOT).as_posix()
        s = p.stat()
        fid = f'{s.st_dev}:{s.st_ino}'
        aliases[fid].append(rel)
        active = next((why for pre, why in previous.ACTIVE.items() if rel.startswith(pre)), None)
        r = proofs.get(rel)
        reason = None
        if active:
            reason = 'active_dependency'
        elif rel.startswith(('processed/rete_cellulare_', 'processed/rete_ancorata_', 'processed/ingestione_')):
            reason = 'current_research'
        elif p.suffix.lower() in keep_ext or s.st_size < 1024 * 1024:
            reason = 'metadata_code_or_small_fixture'
        elif rel in failed_rels:
            reason = 'remote_sample_open_failed'
        elif not r:
            reason = 'no_independent_remote_proof'
        elif rel not in old or old[rel]['sha256'] != r['sha256'] or s.st_size != r['bytes'] or str(s.st_mtime_ns) != old[rel]['mtime_ns']:
            reason = 'changed_since_archive'
        else:
            remote = DRIVE / rel
            if not remote.is_file() or remote.stat().st_size != s.st_size:
                reason = 'remote_missing_or_size_changed'
        inventory.append({'rel': rel, 'bytes': s.st_size, 'file_id': fid, 'nlink': s.st_nlink, 'status': reason or 'candidate'})
        if reason is None:
            rows.append({'rel': rel, 'path': str(p), 'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns,
                         'file_id': fid, 'nlink': s.st_nlink, 'sha256': r['sha256'],
                         'remote_path': str(DRIVE / rel), 'receipt': r['receipt'], 'remote_verified_utc': r['utc']})
selected = {r['rel'] for r in rows}
unique = {}
for r in rows:
    if set(aliases[r['file_id']]) <= selected and len(aliases[r['file_id']]) == r['nlink']:
        unique[r['file_id']] = r['bytes']
summary = defaultdict(lambda: {'files': 0, 'bytes_by_path': 0})
for r in inventory:
    summary[r['status']]['files'] += 1
    summary[r['status']]['bytes_by_path'] += r['bytes']
doc = {'created_utc': datetime.now(timezone.utc).isoformat(), 'root': str(ROOT), 'proof_files': proof_files,
       'unique_bytes': sum(unique.values()), 'rows': rows, 'summary': dict(summary)}
with (HERE / 'plan.json').open('x', encoding='utf-8') as f:
    json.dump(doc, f, indent=2)
with (HERE / 'inventory.json').open('x', encoding='utf-8') as f:
    json.dump(inventory, f, indent=1)
print(json.dumps({'paths': len(rows), 'unique_GiB': sum(unique.values()) / 2**30, 'summary': dict(summary), 'sample_failures': failed}, indent=2))
