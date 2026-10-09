"""Levels of the external arms on the hidden-target structure of a level-A run, per fold: no retyped number.

    leggi_esm2_t.py <completion dir> <out.md> <out.json> <arm> [<arm> ...]

For each lineage: how many hidden targets have a truth row and how many each arm predicts, the measures of each
arm, the amplitude that would fit the truth best and the share of the prediction common to all targets. The
contrasts with their intervals are written by `leggi_contrasti.py --regime-j`. Descriptive, regime T when the
arms come from a fit that saw the lineage: this reader applies no rule.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COLUMNS = ('disc95', 'r_spec', 'sign50', 'nmae_conf', 'mse_ratio', 'amplitude_star', 'common_share_pred')


def num(v, fmt='%.3f'):
    return '—' if v is None or v != v else fmt % v


def main() -> None:
    src, out_md, out_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    arms = sys.argv[4:]
    r = json.loads((src / 'results.json').read_text(encoding='utf-8'))
    j = r['regime_J']
    lines = ['## Livelli per braccio sui bersagli nascosti (proxy, non punteggi VCC)', '',
             '| Lignaggio | Braccio | Bersagli con verità | Bersagli previsti | `disc95` | `r_spec` | `sign50` | `nmae_conf` | '
             'errore quadratico | ampiezza ottima | quota comune |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    table = {}
    for fid, block in j['folds'].items():
        tname = next(tn for tn, t in block['truth'].items() if t['role'] == 'primary')
        t = block['truth'][tname]
        if t.get('skipped'):
            lines.append('| %s | — | %d | | | | | | | | |' % (block['lineage'], t['targets']))
            continue
        table[fid] = {'lineage': block['lineage'], 'truth': tname, 'genes_for_rank_95': t['genes_for_rank_95'], 'arms': {}}
        for arm in arms:
            if arm not in t['arms']:
                continue
            s = t['arms'][arm]
            table[fid]['arms'][arm] = {k: s.get(k) for k in (*COLUMNS, 'targets', 'targets_with_a_prediction')}
            lines.append('| %s | %s | %d | %d | %s | %s | %s | %s | %s | %s | %s |' % (
                block['lineage'], arm, s['targets'], s['targets_with_a_prediction'], num(s['disc95']),
                num(s.get('r_spec'), '%+.3f'), num(s['sign50']), num(s['nmae_conf']), num(s['mse_ratio']),
                num(s.get('amplitude_star'), '%.2f'), num(s.get('common_share_pred'))))
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump({'parity': all(p['equal'] for p in r['parity'].values()), 'hidden_targets': len(j['hidden_targets']),
                   'table': table, 'not_vcc_scores': True, 'descriptive_only': True}, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'parity': all(p['equal'] for p in r['parity'].values()), 'folds': list(table)}))


if __name__ == '__main__':
    main()
