"""Post hoc, exploratory: does T2 behave differently on the targets voted by the small tables?

    t2_tabelle_piccole.py <level A completion of run r5> <out.json>

The targets where T1 differs from T0 in a fold are exactly those that receive a vote from one of the small tables
T1 adds (5-6 panel targets each). On them T2 changes the centring most; on the others only the centring of the
large tables changes. This splits K2 = T2 - T1 into the two groups, per fold and pooled, with the bench's paired
bootstrap over targets. Written after the outcome of T2 was read: it can suggest a contrast, it decides nothing.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402

MEASURES = ('disc95', 'r_spec', 'sign50', 'nmae_conf', 'mse_ratio')


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    results = json.loads((src / 'results.json').read_text(encoding='utf-8'))
    table = src / 'per_target.csv'
    if not table.is_file():
        table = Path(json.loads((src / 'POSIZIONE_per_target.json').read_text(encoding='utf-8'))['path'])
    primary = {f: next(tn for tn, t in blk['truth'].items() if t['role'] == 'primary')
               for f, blk in results['folds'].items()}
    small = {f: set(results['folds'][f]['truth'][primary[f]]['contrasts']['K1']['changed'] or []) for f in primary}
    rows = {}
    with table.open(encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            if primary.get(row['fold']) == row['truth'] and row['arm'] in ('T1', 'T2'):
                rows.setdefault((row['fold'], row['target']), {})[row['arm']] = row
    report = {'what': 'K2 = T2 - T1 on the targets voted by a small table and on the others; exploratory, post hoc',
              'folds': {}, 'pooled': {}, 'not_vcc_scores': True}
    pooled = {g: {m: ([], []) for m in MEASURES} for g in ('small_table_targets', 'other_targets')}
    for f in primary:
        entry = {'small_table_targets': sorted(small[f]), 'groups': {}}
        for group in ('small_table_targets', 'other_targets'):
            keys = [k for k in rows if k[0] == f and ((k[1] in small[f]) == (group == 'small_table_targets'))]
            block = {'targets': len(keys)}
            for m in MEASURES:
                a = np.array([float(rows[k]['T2'][m]) for k in keys])
                b = np.array([float(rows[k]['T1'][m]) for k in keys])
                pooled[group][m][0].extend(a)
                pooled[group][m][1].extend(b)
                block[m] = M.strip(M.paired_bootstrap(a, b)) if len(keys) >= 2 else None
            entry['groups'][group] = block
        report['folds'][f] = entry
    for group, by in pooled.items():
        report['pooled'][group] = {'target_fold_pairs': len(by['disc95'][0])}
        for m, (a, b) in by.items():
            report['pooled'][group][m] = M.strip(M.paired_bootstrap(np.array(a), np.array(b)))
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    for group, by in report['pooled'].items():
        print(group, by['target_fold_pairs'], {m: '%+.4f [%+.4f; %+.4f]%s' % (
            by[m]['mean'], by[m]['lo'], by[m]['hi'], ' RIS' if by[m]['resolved'] else '') for m in MEASURES})
    for f, e in report['folds'].items():
        g = e['groups']['small_table_targets']
        if g['targets'] >= 2:
            print(f, g['targets'], {m: '%+.4f%s' % (g[m]['mean'], '*' if g[m]['resolved'] else '') for m in MEASURES})


if __name__ == '__main__':
    main()
