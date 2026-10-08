"""Read the J-regime baseline of a level-A run (REGIME_J.md): tables and checks, no adoption rule.

    leggi_regime_j.py <completion dir> <out.md> <out.json>

Checks: every filtered table lost exactly its hidden rows and stage 100 read the filtered copies (the run
fails otherwise; here the receipts are counted); no arm differs from T0 on the hidden targets. Table: per
fold, the hidden targets with a truth row, how many get any prediction, and the measures of T0 against the
null prediction and against the shuffled control.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MEASURES = ('disc95', 'r_spec', 'sign50', 'nmae_conf', 'mse_ratio')


def cell(x):
    if x is None or x.get('mean') is None:
        return '—'
    return '%+.4f [%+.4f; %+.4f]%s' % (x['mean'], x['lo'], x['hi'], ' **ris.**' if x['resolved'] else '')


def num(v, fmt='%.3f'):
    return '—' if v is None or v != v else fmt % v


def main() -> None:
    src, out_md, out_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    r = json.loads((src / 'results.json').read_text(encoding='utf-8'))
    j = r['regime_J']
    consumption = [c for c in json.loads((src / 'consumption.json').read_text(encoding='utf-8'))
                   if c['context'].startswith('J-')]
    removed = {(c['label'], c['context']): c['hidden_rows_removed'] for c in consumption}
    checks = {'parity': all(p['equal'] for p in r['parity'].values()), 'j_runs': len(consumption),
              'hidden_targets': len(j['hidden_targets']),
              'every_j_run_removed_hidden_rows': all(v > 0 for v in removed.values()),
              'no_held_table_read': not any(c.get('held_tables_read') for c in consumption)}
    lines = ['## Controlli', '', '| Controllo | Esito |', '|---|---|',
             '| Parità degli effetti di produzione | %s |' % ('sì' if checks['parity'] else '**no**'),
             '| Corse J dello stadio 100 su tabelle filtrate | %d |' % len(consumption),
             '| Bersagli nascosti (gruppo 0 del pannello) | %d |' % len(j['hidden_targets']),
             '| Ogni corsa J ha tolto righe nascoste; nessuna tabella del lignaggio escluso letta | %s |' % (
                 'sì' if checks['every_j_run_removed_hidden_rows'] and checks['no_held_table_read'] else '**no**'), '',
             '## Base del transfer in J (braccio T0; la previsione è la sola testa cis)', '',
             '| Fold | Nascosti con verità | Con una previsione | Righe nascoste tolte (T0) | `disc95` T0 | `disc95` permutato | T0 − nullo, `disc95` | T1 − T0, `disc95` | P4 − T0, `disc95` |',
             '|---|---:|---:|---:|---:|---:|---|---|---|']
    table, same = {}, True
    for fid, blk in j['folds'].items():
        prim = next(tn for tn, t in blk['truth'].items() if t['role'] == 'primary')
        t = blk['truth'][prim]
        if t.get('skipped'):
            lines.append('| %s | %d | — | — | — | — | — | — | — |' % (fid, t['targets']))
            continue
        a, c = t['arms'], t['contrasts']
        k1, k0 = c['K1']['measures']['disc95']['all'], c['K0']['measures']['disc95']['all']
        same = same and c['K1']['targets_changed'] == 0 and c['K0']['targets_changed'] == 0
        lines.append('| %s | %d | %d | %d | %s | %s | %s | %s | %s |' % (
            fid, t['targets'], a['T0']['targets_with_a_prediction'], removed.get(('T0', fid), 0),
            num(a['T0']['disc95']), num(a['T0~shuffle']['disc95']), cell(c['c_null']['measures']['disc95']['all']),
            cell(k1), cell({**k0, 'mean': -k0['mean'], 'lo': -k0['hi'], 'hi': -k0['lo']} if k0.get('mean') is not None else k0)))
        table[fid] = {'targets': t['targets'], 'with_a_prediction': a['T0']['targets_with_a_prediction'],
                      'T0': {m: a['T0'][m] for m in MEASURES}, 'T0_minus_null': {m: c['c_null']['measures'][m]['all'] for m in MEASURES},
                      'arms_changed_vs_T0': {'T1': c['K1']['targets_changed'], 'P4': c['K0']['targets_changed']}}
    checks['all_arms_equal_T0_on_hidden_targets'] = same
    mac = j['macro']['c_null']['measures']
    lines += ['| **macro** | | | | | | %s | | |' % cell(mac['disc95']), '',
              'Tutti i bracci uguali a T0 sui bersagli nascosti: %s.' % ('sì' if same else '**no**'), '',
              '| Misura, T0 − previsione nulla | macro [IC 95%] |', '|---|---|']
    lines += ['| `%s` | %s |' % (m, cell(mac[m])) for m in MEASURES]
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump({'checks': checks, 'table': table, 'macro_T0_minus_null': mac, 'descriptive_only': True,
                   'not_vcc_scores': True}, fh, indent=1)
        fh.write('\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
