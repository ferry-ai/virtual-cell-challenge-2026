"""Read the decomposition of K0 (SCOMPOSIZIONE_K0.md) from a level-A run with the analysis arms P4k and P4kh.

    leggi_scomposizione.py <r2 completion dir> <r1 completion dir> <out.md> <out.json>

Checks first: parity of the production effects; the manifest contrasts K0 and K1 of this run equal those of
run r1 number by number (an added arm must not move the others); Q1 + Q2 + Q3 equals K0 on every fold and
measure. Then the table: per fold and in the macro, each piece on the two primary measures and on the
secondary ones that moved in K0. Descriptive, level A, development lineages: not a score, no adoption rule.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PIECES = (('K0', 'T0 − P4: tutto'), ('Q1', 'P4k − P4: iPSC entra una volta'), ('Q2', 'P4kh − P4k: H1'),
          ('Q3', 'T0 − P4kh: KOLF vota di nuovo'))
MEASURES = ('disc95', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')


def cell(x):
    if x is None or x.get('mean') is None:
        return '—'
    return '%+.4f [%+.4f; %+.4f]%s' % (x['mean'], x['lo'], x['hi'], ' **ris.**' if x['resolved'] else '')


def main() -> None:
    r2_dir, r1_dir, out_md, out_json = (Path(a) for a in sys.argv[1:5])
    r2 = json.loads((r2_dir / 'results.json').read_text(encoding='utf-8'))
    r1 = json.loads((r1_dir / 'results.json').read_text(encoding='utf-8'))
    checks = {'parity': all(p['equal'] for p in r2['parity'].values())}
    primary = {f: next(tn for tn, t in blk['truth'].items() if t['role'] == 'primary') for f, blk in r2['folds'].items()}
    same, worst_sum = True, 0.0
    for f, blk in r2['folds'].items():
        c2 = blk['truth'][primary[f]]['contrasts']
        c1 = r1['folds'][f]['truth'][primary[f]]['contrasts']
        for cid in ('K0', 'K1'):
            same = same and c1[cid]['measures'] == c2[cid]['measures']
        for m in MEASURES:
            total = sum(c2[q]['measures'][m]['all']['mean'] or 0.0 for q in ('Q1', 'Q2', 'Q3'))
            worst_sum = max(worst_sum, abs(total - c2['K0']['measures'][m]['all']['mean']))
    checks['manifest_contrasts_equal_run_r1'] = same
    checks['pieces_sum_to_K0_max_abs_error'] = worst_sum
    checks['pieces_sum_to_K0'] = worst_sum < 1e-3
    lines = ['## Controlli', '', '| Controllo | Esito |', '|---|---|',
             '| Parità degli effetti di produzione (T0, R1, T1) | %s |' % ('sì' if checks['parity'] else '**no**'),
             '| K0 e K1 identici alla corsa r1, numero per numero | %s |' % ('sì' if same else '**no**'),
             '| Q1 + Q2 + Q3 = K0 su ogni fold e misura (errore massimo sulle medie) | %.2e |' % worst_sum, '']
    table = {}
    for m in MEASURES:
        lines += ['## `%s`' % m, '', '| Fold | ' + ' | '.join(name for _, name in PIECES) + ' |',
                  '|---|' + '---|' * len(PIECES)]
        table[m] = {}
        for f, blk in r2['folds'].items():
            c = blk['truth'][primary[f]]['contrasts']
            cells, table[m][f] = [], {}
            for cid, _ in PIECES:
                x = c[cid]['measures'][m]['all']
                n = c[cid]['targets_changed']
                cells.append(cell(x) + (' (%d cambiati)' % n if cid != 'K0' else ''))
                table[m][f][cid] = {k: x.get(k) for k in ('mean', 'lo', 'hi', 'resolved', 'n')} | {'targets_changed': n}
            lines.append('| %s | %s |' % (f, ' | '.join(cells)))
        macro = [r2['macro'][cid]['measures'][m] for cid, _ in PIECES]
        table[m]['macro'] = {cid: x for (cid, _), x in zip(PIECES, macro)}
        lines += ['| **macro** | ' + ' | '.join(cell(x) for x in macro) + ' |', '']
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump({'checks': checks, 'table': table, 'not_vcc_scores': True, 'descriptive_only': True}, fh, indent=1)
        fh.write('\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
