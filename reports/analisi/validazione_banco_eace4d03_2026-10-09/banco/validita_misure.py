"""Which measure can be trusted on which fold: the positive control against null, generic and swapped predictions.

Reads a level-A `results.json` of the frozen bench (no new computation) and, for every C fold and its primary
truth, asks of each measure whether it tells the reference transfer T0 apart from three degenerate predictions
built from T0 itself:

    swapped   every target gets another target's prediction        (contrast c_shuffle)
    generic   every target gets the mean prediction of the arm     (contrast c_meanonly)
    null      no effect at all                                     (contrast c_null)

A measure "sees" a control on a fold when the paired bootstrap of T0 minus the control is resolved; it is
"with T0" when the resolved difference favours T0. A measure that does not see the swapped control on a fold
cannot be used there to say that an arm knows its targets (contract v2, section 1; contract v3, section 1).

    py validita_misure.py <results.json> <out.json> <out.md>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

MEASURES = ('disc95', 'disc', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')
CONTROLS = (('c_shuffle', 'scambiato'), ('c_meanonly', 'generico'), ('c_null', 'nullo'))


def verdict(entry, higher_is_better):
    a = entry['all']
    if a.get('mean') is None or a.get('lo') is None:
        return {'state': 'non calcolabile', 'mean': a.get('mean')}
    favours_t0 = (a['mean'] > 0) == bool(higher_is_better)
    if not a['resolved']:
        state = 'non distingue'
    else:
        state = 'distingue, a favore di T0' if favours_t0 else 'distingue, CONTRO T0'
    return {'state': state, 'mean': a['mean'], 'lo': a['lo'], 'hi': a['hi'], 'n': a['n']}


def build(results: dict) -> dict:
    out = {}
    for fid, fold in results['folds'].items():
        tname, block = next((t, b) for t, b in fold['truth'].items() if b['role'] == 'primary')
        if block.get('skipped'):
            out[fid] = {'truth': tname, 'skipped': True}
            continue
        rows = {}
        for m in MEASURES:
            rows[m] = {}
            for cid, label in CONTROLS:
                entry = block['contrasts'][cid]['measures'][m]
                rows[m][label] = verdict(entry, entry['higher_is_better'])
            rows[m]['usable_as_specificity_guard'] = rows[m]['scambiato']['state'] == 'distingue, a favore di T0'
        out[fid] = {'lineage': fold['lineage'], 'truth': tname, 'targets': block['targets'],
                    'genes_for_rank_strict': block['genes_for_rank_strict'], 'genes_for_rank_95': block['genes_for_rank_95'],
                    'median_confident_genes_T0': block['arms']['T0']['median_n_conf'], 'measures': rows}
    return out


def render(doc: dict, source: str) -> str:
    short = {'distingue, a favore di T0': 'sì', 'non distingue': '**no**', 'distingue, CONTRO T0': '**contro**',
             'non calcolabile': '—'}
    lines = ['# Quale misura vale su quale fold', '',
             'Scritto da `banco/validita_misure.py` da `%s`, senza nuovi calcoli. Per ogni fold e ogni misura: il transfer '
             'di riferimento T0 si distingue (bootstrap appaiato sui bersagli, risolto) da tre previsioni degeneri costruite '
             'da T0 stesso? **sì** = risolto a favore di T0; **no** = non risolto; **contro** = risolto a sfavore di T0. '
             'Una misura che non vede il braccio scambiato su un fold non può dire, lì, che un braccio conosce i suoi '
             'bersagli. Spazio degli effetti, lignaggi di sviluppo: non sono punteggi VCC.' % source, '']
    for label_key, title in (('scambiato', 'Contro T0 a bersagli scambiati (specificità)'),
                             ('generico', 'Contro la sola media di T0 (parte comune)'),
                             ('nullo', 'Contro nessun effetto')):
        lines += ['## %s' % title, '', '| Fold | Verità | Bersagli | Geni confidenti (mediana) | ' + ' | '.join('`%s`' % m for m in MEASURES) + ' |',
                  '|---|---|---:|---:|' + '---|' * len(MEASURES)]
        for fid, f in doc.items():
            if f.get('skipped'):
                continue
            lines.append('| %s | `%s` | %d | %s | %s |' % (
                fid, f['truth'], f['targets'], ('%.0f' % f['median_confident_genes_T0']),
                ' | '.join(short[f['measures'][m][label_key]['state']] for m in MEASURES)))
        lines.append('')
    usable = {m: [fid for fid, f in doc.items() if not f.get('skipped') and f['measures'][m]['usable_as_specificity_guard']]
              for m in MEASURES}
    lines += ['## In breve', '', '| Misura | Fold su cui vede il braccio scambiato |', '|---|---|']
    for m in MEASURES:
        lines.append('| `%s` | %s |' % (m, ', '.join(usable[m]) or '**nessuno**'))
    return '\n'.join(lines) + '\n'


def main() -> None:
    src, out_json, out_md = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    doc = build(json.loads(src.read_text(encoding='utf-8')))
    payload = {'schema': 'validita-misure/1', 'source': str(src).replace('\\', '/'),
               'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'folds': doc}
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    with out_md.open('x', encoding='utf-8', newline='\n') as fh:
        fh.write(render(doc, payload['source']))
    print(out_md)


if __name__ == '__main__':
    main()
