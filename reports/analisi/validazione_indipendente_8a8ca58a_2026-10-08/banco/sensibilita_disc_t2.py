"""The strict discrimination measure of contract v1 on the T2 contrasts, with and without the fold where it is
not usable: sensibilita_disc_t2.py <level A completion> <out.json>

Contract v2 replaced `disc` with `disc95` because on C-K562 one gene is valid for every target, and promised both
readings side by side. This recomputes the macro of `disc` from the per-target table with the bench's own
bootstrap: over the six folds (it must reproduce results.json) and over the five where the measure is usable.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402

PAIRS = {'K2': ('T2', 'T1'), 'K2t0': ('T2', 'T0'), 'K1': ('T1', 'T0')}


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    results = json.loads((src / 'results.json').read_text(encoding='utf-8'))
    primary = {f: next(tn for tn, t in blk['truth'].items() if t['role'] == 'primary')
               for f, blk in results['folds'].items()}
    genes = {f: results['folds'][f]['truth'][primary[f]]['genes_for_rank_strict'] for f in primary}
    values = {}
    table = src / 'per_target.csv'
    if not table.is_file():                # kept in the data root: the folder holds its position and sha256
        table = Path(json.loads((src / 'POSIZIONE_per_target.json').read_text(encoding='utf-8'))['path'])
    with table.open(encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            if primary.get(row['fold']) == row['truth']:
                values.setdefault((row['fold'], row['arm']), {})[row['target']] = (float(row['disc']), float(row['disc95']))
    report = {'genes_for_rank_strict': genes, 'contrasts': {}, 'not_vcc_scores': True,
              'bootstrap': {'resamples': M.BOOT, 'seed': M.BOOT_SEED, 'unit': 'target'}}
    for cid, (first, second) in PAIRS.items():
        entry = {}
        for k, measure in enumerate(('disc', 'disc95')):
            boots = {}
            for f in primary:
                targets = list(values[(f, first)])            # the order of the table is the order of the bench
                a = np.array([values[(f, first)][t][k] for t in targets])
                b = np.array([values[(f, second)][t][k] for t in targets])
                boots[f] = M.paired_bootstrap(a, b)
            six = M.macro(list(boots.values()))
            recorded = results['macro'][cid]['measures'][measure]
            usable = [f for f in primary if not (measure == 'disc' and genes[f] < 100)]
            entry[measure] = {
                'per_fold': {f: M.strip(b) for f, b in boots.items()},
                'macro_six_folds': six, 'reproduces_results_json': bool(
                    abs(six['mean'] - recorded['mean']) < 1e-12 and abs(six['lo'] - recorded['lo']) < 1e-12
                    and abs(six['hi'] - recorded['hi']) < 1e-12),
                'folds_where_usable': usable, 'macro_usable_folds': M.macro([boots[f] for f in usable])}
        report['contrasts'][cid] = entry
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    for cid, entry in report['contrasts'].items():
        for measure, e in entry.items():
            f = lambda x: '%+.4f [%+.4f; %+.4f]%s' % (x['mean'], x['lo'], x['hi'], ' RIS' if x['resolved'] else '')
            print(cid, measure, 'six:', f(e['macro_six_folds']), 'reproduced' if e['reproduces_results_json'] else 'NOT REPRODUCED',
                  '| usable folds (%d):' % len(e['folds_where_usable']), f(e['macro_usable_folds']))


if __name__ == '__main__':
    main()
