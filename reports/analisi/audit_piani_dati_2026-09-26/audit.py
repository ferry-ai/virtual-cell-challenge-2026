"""Read-only inventory and small isolation counterexamples; writes a fresh audit output."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone

import numpy as np
from vcc2026.multisource import AxisTable, mix

ROOT = Path(__file__).resolve().parents[2]
DATA = Path('C:/Users/ferra/vcc2026-data')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    refs = {}
    for base in ('docs', 'reports'):
        for p in (ROOT / base).rglob('*.md'):
            if 'audit_piani_dati_2026-09-26' in p.parts:
                continue
            for accession in set(re.findall(r'\b(?:GSE\d+|E-MTAB-\d+|PRJNA\d+|PRJEB\d+)\b', p.read_text(encoding='utf-8-sig', errors='replace'))):
                refs.setdefault(accession, []).append(p.relative_to(ROOT).as_posix())
    with (args.out / 'accession_mentions.csv').open('x', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['accession', 'references', 'interpretation'])
        for accession, paths in sorted(refs.items()):
            w.writerow([accession, ';'.join(sorted(paths)), 'Mention only; not verified dataset identity or adoption'])
    files = []
    for p in sorted((DATA / 'external').rglob('*')):
        if p.is_file():
            st = p.stat()
            files.append({'path': str(p), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns})
    (args.out / 'local_external_files.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    cache = []
    for p in sorted((DATA / 'processed/multisource_2026-09-23_r5').glob('*.npz')):
        with np.load(p, allow_pickle=False) as z:
            ts = z['targets'].astype(str)
            cache.append({'source': p.stem, 'targets': len(ts), 'meta': json.loads(str(z['meta']))})
    # A held-out row affects an ostensibly training-only row through source centering.
    def feature(test_value, safe):
        a = np.array([[1.0], [test_value]], dtype=np.float32)
        tab = AxisTable('source', ['train', 'test'], a, a, np.ones_like(a), np.array([100., 100.]))
        common = {'source': tab.common(['train'])} if safe else None
        return float(mix([tab], ['train'], gamma=1, common=common)[0][0, 0])
    probe = {'description': 'Synthetic counterexample through the production mix function; not measured score bias',
             'global_center_before': feature(2., False), 'global_center_after': feature(12., False),
             'train_only_center_before': feature(2., True), 'train_only_center_after': feature(12., True),
             'global_label_center_before': float((np.array([1., 2.]) - np.mean([1., 2.]))[0]),
             'global_label_center_after': float((np.array([1., 12.]) - np.mean([1., 12.]))[0])}
    assert probe['global_center_before'] != probe['global_center_after']
    assert probe['train_only_center_before'] == probe['train_only_center_after']
    tracked = ['configs/recipes/t20.json', 'src/vcc2026/multisource.py',
               'src/vcc2026/transfer_model.py', 'scripts/104_learned_reweighting.py',
               'reports/trasferimento_appreso_2026-09-26/lct_bench2.py',
               'reports/trasferimento_appreso_2026-09-26/lct_bench3.py',
               'reports/trasferimento_appreso_2026-09-26/r3/measurements.json',
               'reports/trasferimento_appreso_2026-09-26/r4/measurements.json',
               'reports/data_audit/public_catalog.json', 'reports/data_audit/hipsci_coverage.json']
    hashes = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in tracked}
    learned = json.loads((ROOT / tracked[6]).read_text())['rows']
    selected = [r for r in learned if r['arm'] in ('t20like', 't20_rw0.25', 't20_rw0.5')]
    out = {'utc': datetime.now(timezone.utc).isoformat(), 'claim_type': 'inventory, existing-result extraction and synthetic isolation demonstration',
           'accession_mentions': len(refs), 'external_files': len(files), 'cache': cache,
           'isolation_probe': probe, 'learned_results': selected, 'input_sha256': hashes,
           'limitations': ['No model refit or new VCC score', 'No download or remote storage completeness assertion',
                           'Accession list may include duplicates, unsuitable studies and historically wrong references',
                           'File presence and byte length do not verify matrix correctness or completeness']}
    (args.out / 'measurements.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps({'accession_mentions': len(refs), 'external_files': len(files),
                      'cache': [(x['source'], x['targets']) for x in cache], 'isolation_probe': probe}, indent=2))


if __name__ == '__main__':
    main()
