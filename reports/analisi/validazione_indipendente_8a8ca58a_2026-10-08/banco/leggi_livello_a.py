"""Read the level-A results by the rule of contract v1 and write the tables, without retyping a number.

    leggi_livello_a.py <completion dir> <out.md> <out.json>

For every contrast: per fold the paired difference of the two primary measures with its interval over
targets, on all targets and on the targets the contrast changed; the macro; and the reading the contract's
section 8 allows from level A alone (it can stop a candidate, never promote it). The shuffle control decides
whether a fold's discrimination measure is usable at all.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PRIMARY = ('disc', 'r_spec')
SECONDARY = ('disc95', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')
NAMES = {'K0': 'K0 — T0 − P4: più linee, tabelle e modello fissi', 'K1': 'K1 — T1 − T0: banca ampliata a modello invariato',
         'K1r1': 'K1 (r1) — R1 − T0: la release r1 com\'era', 'c_gamma0': 'Controllo — T0 − T0 senza sottrazione comune (gamma 0)',
         'c_nocis': 'Controllo — T0 − T0 senza testa cis'}


def cell(x):
    if x is None or x.get('mean') is None:
        return '—'
    star = ' **ris.**' if x['resolved'] else ''
    return '%+.4f [%+.4f; %+.4f]%s' % (x['mean'], x['lo'], x['hi'], star)


def main() -> None:
    src, out_md, out_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    r = json.loads((src / 'results.json').read_text(encoding='utf-8'))
    folds = r['folds']
    primary = {f: next(tn for tn, t in blk['truth'].items() if t['role'] == 'primary') for f, blk in folds.items()}
    lines, reading = [], {}
    lines += ['## Controllo a bersagli permutati (validità del banco, per fold)', '',
              '| Fold | Bersagli | Geni comuni a tutti | `disc` di T0 | `disc` permutato | Differenza [IC 95%] | `disc` utilizzabile |',
              '|---|---:|---:|---:|---:|---|---|']
    usable = {}
    for f, s in r['shuffle_control'].items():
        blk = folds[f]['truth'][primary[f]]
        d = s['difference']
        usable[f] = bool(d['resolved'] and d['lo'] > 0)
        lines.append('| %s | %d | %d | %.3f | %.3f | %s | %s |' % (
            f, blk['targets'], blk['genes_for_rank_strict'], s['T0_disc'], s['shuffle_disc'], cell(d),
            'sì' if usable[f] else '**no**'))
    lines += ['', '## Livelli per braccio (verità primaria del fold; proxy, non punteggi VCC)', '',
              '| Fold | Braccio | `disc` | `disc95` | `r_spec` | `sign50` | `reach` | `nmae_conf` | `mse_ratio` | quota comune prev./verità | ampiezza ottima |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|']
    for f, blk in folds.items():
        t = blk['truth'][primary[f]]
        for a in ('P4', 'T0', 'T1', 'R1', 'T0~gamma0', 'T0~nocis', 'T0~meanonly', 'T0~shuffle'):
            s = t['arms'][a]
            share = '—' if s['common_share_pred'] != s['common_share_pred'] else '%.3f' % s['common_share_pred']
            lines.append('| %s | %s | %.3f | %.3f | %s | %.3f | %.3f | %.3f | %.3f | %s / %.3f | %.2f |' % (
                f, a, s['disc'], s['disc95'], '—' if s['r_spec'] != s['r_spec'] else '%+.3f' % s['r_spec'], s['sign50'],
                s['reach'], s['nmae_conf'], s['mse_ratio'], share, s['common_share_truth'], s['amplitude_star']))
    for cid in ('K1', 'K1r1', 'K0', 'c_gamma0', 'c_nocis'):
        lines += ['', '## ' + NAMES[cid], '',
                  '| Fold | Cambiati / bersagli | `disc`, tutti | `disc`, solo cambiati | `r_spec`, tutti | `r_spec`, solo cambiati |',
                  '|---|---:|---|---|---|---|']
        negative, positive, per_fold = [], [], {}
        for f, blk in folds.items():
            c = blk['truth'][primary[f]]['contrasts'][cid]
            m = c['measures']
            note = '' if usable[f] else ' (non utilizzabile)'
            lines.append('| %s | %d / %d | %s%s | %s | %s | %s |' % (
                f, c['targets_changed'], c['targets'], cell(m['disc']['all']), note, cell(m['disc']['changed_only']),
                cell(m['r_spec']['all']), cell(m['r_spec']['changed_only'])))
            d = m['disc']['all']
            per_fold[f] = {'disc': {k: d[k] for k in ('mean', 'lo', 'hi', 'resolved', 'n')}, 'disc_usable': usable[f],
                           'r_spec': {k: m['r_spec']['all'][k] for k in ('mean', 'lo', 'hi', 'resolved', 'n')},
                           'targets_changed': c['targets_changed'], 'targets': c['targets']}
            if usable[f] and d['resolved']:
                (negative if d['hi'] < 0 else positive).append(f)
        mac = r['macro'][cid]['measures']
        lines.append('| **macro, 6 fold** | | %s | | %s | |' % (cell(mac['disc']), cell(mac['r_spec'])))
        lines += ['', '| Misura secondaria | macro [IC 95%] | verso migliore |', '|---|---|---|']
        for m in SECONDARY:
            lines.append('| `%s` | %s | %s |' % (m, cell(mac[m]), 'più alto' if m in ('disc95', 'sign50', 'reach') else 'più basso'))
        macro_negative = bool(mac['disc']['resolved'] and mac['disc']['hi'] < 0)
        if cid.startswith('K'):
            verdict = ('ferma il candidato: `disc` risolto negativo' if (negative or macro_negative)
                       else 'nessun arresto dal livello A; il livello A non promuove')
            reading[cid] = {'folds_with_resolved_negative_disc': negative, 'folds_with_resolved_positive_disc': positive,
                            'macro_disc': {k: mac['disc'][k] for k in ('mean', 'lo', 'hi', 'resolved', 'folds')},
                            'macro_disc_resolved_negative': macro_negative, 'level_A_reading': verdict,
                            'folds_where_disc_is_not_usable': [f for f in folds if not usable[f]], 'per_fold': per_fold}
            lines += ['', '**Lettura del §8 dal solo livello A:** %s. Fold con `disc` risolto negativo: %s; risolto '
                      'positivo: %s; fold dove `disc` non è utilizzabile: %s.' % (
                          verdict, ', '.join(negative) or 'nessuno', ', '.join(positive) or 'nessuno',
                          ', '.join(f for f in folds if not usable[f]) or 'nessuno')]
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump({'source': str(src.as_posix()), 'parity': r['parity'], 'disc_usable_by_fold': usable,
                   'reading': reading, 'bootstrap': r['bootstrap']}, fh, indent=1)
        fh.write('\n')
    print(json.dumps({k: v['level_A_reading'] for k, v in reading.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
