"""Tables of any contrasts of a level-A run, per fold and in the macro, without retyping a number.

    leggi_contrasti.py <completion dir> <out.md> <out.json> <contrast id>=<title> [...] [--equal A=-B ...]
    leggi_contrasti.py --regime-j <completion dir> ...      the same on the hidden-target structure of the run

For every named contrast and every reported measure: the paired difference with its interval over targets,
the number of targets it changes, and the macro over the folds where it exists. `--equal X2=-Q3` checks that
two contrasts are the same up to sign on every fold and measure (a run must reproduce what an earlier one
measured). Descriptive: it applies no adoption rule.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MEASURES = ('disc95', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')
BETTER = {'disc95': 'più alto', 'r_spec': 'più alto', 'sign50': 'più alto', 'reach': 'più alto',
          'nmae_conf': 'più basso', 'mse_ratio': 'più basso'}


def cell(x):
    if x is None or x.get('mean') is None:
        return '—'
    return '%+.4f [%+.4f; %+.4f]%s' % (x['mean'], x['lo'], x['hi'], ' **ris.**' if x['resolved'] else '')


def main() -> None:
    args = sys.argv[1:]
    regime_j = '--regime-j' in args
    args = [a for a in args if a != '--regime-j']
    equal = []
    if '--equal' in args:
        i = args.index('--equal')
        equal, args = args[i + 1:], args[:i]
    src, out_md, out_json = Path(args[0]), Path(args[1]), Path(args[2])
    wanted = [a.split('=', 1) for a in args[3:]]
    r = json.loads((src / 'results.json').read_text(encoding='utf-8'))
    if regime_j:
        r = dict(r, folds=r['regime_J']['folds'], macro=r['regime_J']['macro'])
    primary = {f: next(tn for tn, t in blk['truth'].items() if t['role'] == 'primary') for f, blk in r['folds'].items()}
    checks = {'parity': all(p['equal'] for p in r['parity'].values())}
    for item in equal:
        a, b = item.split('=-')
        worst = 0.0
        for f, blk in r['folds'].items():
            c = blk['truth'][primary[f]]['contrasts']
            for m in MEASURES:
                worst = max(worst, abs((c[a]['measures'][m]['all']['mean'] or 0.0) + (c[b]['measures'][m]['all']['mean'] or 0.0)))
        checks['%s_equals_minus_%s_max_abs_error' % (a, b)] = worst
    lines = ['## Controlli', '', '| Controllo | Esito |', '|---|---|',
             '| Parità degli effetti di produzione (T0, R1, T1) | %s |' % ('sì' if checks['parity'] else '**no**')]
    lines += ['| %s | %.2e |' % (k.replace('_', ' '), v) for k, v in checks.items() if k != 'parity'] + ['']
    table = {}
    for m in MEASURES:
        lines += ['## `%s` (meglio: %s)' % (m, BETTER[m]), '', '| Fold | ' + ' | '.join(t for _, t in wanted) + ' |',
                  '|---|' + '---|' * len(wanted)]
        table[m] = {}
        for f, blk in r['folds'].items():
            c = blk['truth'][primary[f]]['contrasts']
            cells, table[m][f] = [], {}
            for cid, _ in wanted:
                if cid not in c:
                    cells.append('—')
                    continue
                x = c[cid]['measures'][m]['all']
                cells.append('%s (%d cambiati)' % (cell(x), c[cid]['targets_changed']))
                table[m][f][cid] = {k: x.get(k) for k in ('mean', 'lo', 'hi', 'resolved', 'n')} | {
                    'targets_changed': c[cid]['targets_changed']}
            lines.append('| %s | %s |' % (f, ' | '.join(cells)))
        macro = [r['macro'][cid]['measures'][m] for cid, _ in wanted]
        table[m]['macro'] = {cid: x for (cid, _), x in zip(wanted, macro)}
        lines += ['| **macro** | ' + ' | '.join(cell(x) for x in macro) + ' |', '']
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump({'checks': checks, 'table': table, 'contrasts': dict(wanted), 'not_vcc_scores': True,
                   'descriptive_only': True}, fh, indent=1)
        fh.write('\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
