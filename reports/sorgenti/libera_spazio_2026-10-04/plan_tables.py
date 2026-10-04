"""Add the two archived DepMap matrices excluded by the first plan's CSV metadata rule."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/ferra/vcc2026-data')
DRIVE = Path('G:/Il mio Drive/vcc2026/data')
REL = ('external/depmap_24q4/OmicsCNGene.csv',
       'external/depmap_24q4/OmicsExpressionProteinCodingGenesTPMLogp1.csv')
base = json.loads((HERE / 'plan.json').read_text(encoding='utf-8'))
old = {r['rel']: r for r in csv.DictReader((ROOT / 'processed/archivio_cloud_2026-10-02/r1/local_hashes.tsv').open(encoding='utf-8'), delimiter='\t')}
proofs = {}
for pf in base['proof_files']:
    path = HERE / pf['name']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == pf['sha256']
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        r = json.loads(line)
        if r.get('status') == 'verified':
            proofs[r['rel']] = {**r, 'receipt': pf['name']}
rows = []
for rel in REL:
    p = ROOT / rel
    s = p.stat()
    r = proofs[rel]
    assert r['sha256'] == r['expected_sha256'] == old[rel]['sha256']
    assert r['bytes'] == r['expected_bytes'] == s.st_size == (DRIVE / rel).stat().st_size
    assert str(s.st_mtime_ns) == old[rel]['mtime_ns'] and s.st_nlink == 1
    rows.append({'rel': rel, 'path': str(p), 'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns,
                 'file_id': f'{s.st_dev}:{s.st_ino}', 'nlink': s.st_nlink,
                 'sha256': r['sha256'], 'remote_path': str(DRIVE / rel),
                 'receipt': r['receipt'], 'remote_verified_utc': r['utc']})
doc = {'created_utc': datetime.now(timezone.utc).isoformat(), 'root': str(ROOT),
       'proof_files': base['proof_files'], 'unique_bytes': sum(r['bytes'] for r in rows), 'rows': rows}
with (HERE / 'tables_plan.json').open('x', encoding='utf-8') as f:
    json.dump(doc, f, indent=2)
print(json.dumps({'paths': len(rows), 'unique_GiB': doc['unique_bytes'] / 2**30}))
