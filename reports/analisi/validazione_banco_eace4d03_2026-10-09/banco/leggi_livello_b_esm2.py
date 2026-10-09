"""Read the four-arm six-member bench of a fill candidate by the rules written before its numbers (LIVELLO_B_ESM2.md).

    leggi_livello_b_esm2.py <level-A results.json> <out.md> <out.json> <fold>=<completion dir> [<fold>=<dir> ...]
        [--candidate E2f] [--reference T0] [--swapped E2swap] [--generic E2gen] [--level-a-contrast C_integration]

Per fold: the technical checks (bench completed, inputs verified, the exchanged-rows control lowers the local PDS),
then every declared pair as bench_v2 wrote it (paired differences over the generator seeds; "resolved" is
|mean| > 2 sd / sqrt(seeds)). Macro: the mean over the usable folds of the per-seed differences, same convention.
The outcome of section 8 of contract v1 is derived for candidate - reference; the four sentences of the plan are
then decided mechanically. Local scales on half-depth truths: not VCC scores.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

MEMBERS = ('PDS', 'MSE', 'NMAE', 'FID', 'REACH', 'JAC')


def stats(values) -> dict:
    v = np.asarray(values, float)
    sd = float(v.std(ddof=1)) if v.size > 1 else float('nan')
    return {'mean': float(v.mean()), 'sd': sd, 'values': [float(x) for x in v],
            'resolved': bool(abs(v.mean()) > 2 * sd / np.sqrt(v.size)) if v.size > 1 else False}


def cell(s) -> str:
    if s is None:
        return '—'
    return ('%+.4f ± %.4f%s' % (s['mean'], s['sd'], ' **ris.**' if s['resolved'] else '')).replace('.', ',')


def find(root: Path, name: str, parent=None):
    hits = [p for p in sorted(root.rglob(name)) if parent is None or p.parent.name == parent]
    return hits[0] if hits else None


def read_fold(root: Path) -> dict:
    done_path = find(root, 'bench_done.json')
    done = json.loads(done_path.read_text(encoding='utf-8')) if done_path else {}
    steps = done.get('steps') or {}
    out = {'steps': steps, 'targets': (done.get('targets') or {}).get('all'), 'pairs': {}, 'control': None}
    control = find(root, 'paired.json', 'bench_control')
    if control:
        pair = json.loads(control.read_text(encoding='utf-8'))['pairs'].get('T0:T0shuffle')
        out['control'] = None if pair is None else {'PDS_gap': pair['members']['PDS']['mean'], 'six_gap': pair['six']['mean']}
    full = find(root, 'paired.json', 'bench_full')
    if full:
        paired = json.loads(full.read_text(encoding='utf-8'))
        out['pairs'] = paired['pairs']
        out['n_pred'], out['gen_seeds'], out['emission'] = paired['n_pred'], paired['gen_seeds'], paired['emission']
    verified = find(root, 'inputs_verified.json')
    out['inputs_verified'] = sorted(json.loads(verified.read_text(encoding='utf-8'))) if verified else None
    out['usable'] = bool(all((steps.get(s) or {}).get('returncode') == 0 for s in ('control', 'full'))
                         and out['control'] and out['control']['PDS_gap'] > 0 and out['pairs'])
    return out


def macro(folds: dict, pair: str, key: str, member=None):
    series = []
    for f in folds.values():
        if not f['usable'] or pair not in f['pairs']:
            continue
        node = f['pairs'][pair][key] if member is None else f['pairs'][pair]['members'][member]
        series.append(node['values'])
    if not series or len({len(s) for s in series}) != 1:
        return None
    return stats(np.mean(np.asarray(series, float), axis=0))


def section8(folds: dict, pair: str, level_a_blocks: dict) -> dict:
    usable = {n: f for n, f in folds.items() if f['usable'] and pair in f['pairs']}
    six, five = macro(folds, pair, 'six'), macro(folds, pair, 'without_JAC')
    fold_losses = [n for n, f in usable.items()
                   if (f['pairs'][pair]['six']['resolved'] and f['pairs'][pair]['six']['mean'] < 0)
                   or (f['pairs'][pair]['members']['PDS']['resolved'] and f['pairs'][pair]['members']['PDS']['mean'] < 0)]
    a_losses = [n for n, b in level_a_blocks.items() if b and b['resolved'] and b['mean'] < 0]
    if len(usable) < 2 or six is None:
        outcome = 'INCONCLUDENTE'
        why = 'meno di due fold di livello B utilizzabili'
    elif (six['resolved'] and six['mean'] < 0) or fold_losses or a_losses:
        outcome, why = 'VALIDO E SFAVOREVOLE', 'macro dei sei membri risolta negativa, oppure un fold con una regressione risolta'
    elif six['resolved'] and six['mean'] > 0 and five is not None and five['mean'] > 0:
        outcome, why = 'VALIDO E FAVOREVOLE', 'macro dei sei membri risolta positiva, stesso segno senza JAC, nessuna regressione risolta'
    else:
        outcome, why = 'INCONCLUDENTE', 'macro dei sei membri non risolta'
    return {'outcome': outcome, 'why': why, 'folds_usable': sorted(usable), 'macro_six': six, 'macro_without_JAC': five,
            'folds_with_resolved_loss_of_six_or_PDS': fold_losses, 'level_A_disc95_resolved_losses': a_losses}


def main() -> None:
    args = sys.argv[1:]
    names = {'candidate': 'E2f', 'reference': 'T0', 'swapped': 'E2swap', 'generic': 'E2gen', 'level-a-contrast': 'C_integration'}
    for key in list(names):
        flag = '--' + key
        if flag in args:
            i = args.index(flag)
            names[key] = args[i + 1]
            del args[i:i + 2]
    level_a = json.loads(Path(args[0]).read_text(encoding='utf-8'))
    out_md, out_json = Path(args[1]), Path(args[2])
    folds = {item.split('=', 1)[0]: read_fold(Path(item.split('=', 1)[1])) for item in args[3:]}
    cand, ref, swap, gen = names['candidate'], names['reference'], names['swapped'], names['generic']
    pairs = ['%s:%s' % (cand, ref), '%s:%s' % (gen, ref), '%s:%s' % (swap, ref), '%s:%s' % (cand, swap), '%s:%s' % (cand, gen)]
    level_a_blocks = {}
    for name in folds:
        fold = level_a['folds'].get(name)
        block = None
        if fold:
            primary = next(b for b in fold['truth'].values() if b['role'] == 'primary')
            contrast = primary['contrasts'].get(names['level-a-contrast'])
            block = contrast['measures']['disc95']['all'] if contrast else None
        level_a_blocks[name] = block
    lines = ['# Sei membri per il riempimento: %s contro %s, con i bracci di controllo' % (cand, ref), '',
             'Scritto da `banco/leggi_livello_b_esm2.py`; nessun numero ricopiato a mano. Scala locale su verità a metà '
             'profondità: **non sono punteggi VCC** e danno il verso, non l\'entità. «ris.» = |media| > 2·sd/√semi.', '',
             '## Controlli tecnici', '',
             '| Fold | Bersagli | Passi conclusi | Controllo: PDS di T0 − T0 a righe scambiate | Utilizzabile |', '|---|---:|---|---:|---|']
    for name, f in folds.items():
        ok_steps = ', '.join('%s %s' % (s, 'ok' if (v or {}).get('returncode') == 0 else '**no**') for s, v in f['steps'].items()) or '—'
        gap = None if not f['control'] else f['control']['PDS_gap']
        lines.append('| %s | %s | %s | %s | %s |' % (name, f['targets'] or '—', ok_steps,
                                                    '—' if gap is None else ('%+.4f' % gap).replace('.', ','),
                                                    'sì' if f['usable'] else '**no**'))
    for pair in pairs:
        first, second = pair.split(':')
        lines += ['', '## %s − %s' % (first, second), '', '| Fold | Sei membri | Senza JAC | ' + ' | '.join(MEMBERS) + ' |',
                  '|---|---|---|' + '---|' * len(MEMBERS)]
        for name, f in folds.items():
            p = f['pairs'].get(pair) if f['usable'] else None
            if p is None:
                lines.append('| %s | non utilizzabile |  |' % name + ' |' * len(MEMBERS))
                continue
            lines.append('| %s | %s | %s | %s |' % (name, cell(p['six']), cell(p['without_JAC']),
                                                   ' | '.join(cell(p['members'][m]) for m in MEMBERS)))
        lines.append('| **macro** | %s | %s | %s |' % (cell(macro(folds, pair, 'six')), cell(macro(folds, pair, 'without_JAC')),
                                                        ' | '.join(cell(macro(folds, pair, None, m)) for m in MEMBERS)))
    verdict = section8(folds, pairs[0], level_a_blocks)

    def pair_of(fold, pair, key='six', member=None):
        f = folds[fold]
        if not f['usable'] or pair not in f['pairs']:
            return None
        return f['pairs'][pair][key] if member is None else f['pairs'][pair]['members'][member]

    usable = [n for n in folds if folds[n]['usable']]
    cr = {n: pair_of(n, pairs[0]) for n in usable}
    sr = {n: pair_of(n, pairs[2]) for n in usable}
    cs = {n: pair_of(n, pairs[3]) for n in usable}
    cs_pds = {n: pair_of(n, pairs[3], member='PDS') for n in usable}
    cr_pds = {n: pair_of(n, pairs[0], member='PDS') for n in usable}
    pos = lambda s: bool(s and s['resolved'] and s['mean'] > 0)
    neg = lambda s: bool(s and s['resolved'] and s['mean'] < 0)
    helps = bool(usable) and any(pos(cr[n]) for n in usable) and not any(neg(cr[n]) for n in usable)
    words = {
        'riempire aiuta i sei membri': helps,
        'aiuta perché conosce il bersaglio': helps and any(pos(cs[n]) or pos(cs_pds[n]) for n in usable),
        'è un effetto di copertura': any((pos(cr[n]) and pos(sr[n]) or neg(cr[n]) and neg(sr[n]))
                                         and not (cs[n] and cs[n]['resolved']) for n in usable),
        'riempire costa': any(neg(cr[n]) or neg(cr_pds[n]) for n in usable)}
    lines += ['', '## Esito', '', '- **§8 del contratto v1 per %s − %s: %s** (%s). Fold utilizzabili: %s. Macro dei sei membri %s; '
              'senza JAC %s. Livello A, `disc95` di %s: %s.'
              % (cand, ref, verdict['outcome'], verdict['why'], ', '.join(verdict['folds_usable']) or 'nessuno',
                 cell(verdict['macro_six']), cell(verdict['macro_without_JAC']), names['level-a-contrast'],
                 '; '.join('%s %s%s' % (n, ('%+.5f' % b['mean']).replace('.', ','), '' if not b['resolved'] else ' risolto')
                           for n, b in level_a_blocks.items() if b) or 'non disponibile'),
              '', '| Affermazione fissata prima dei numeri | Si scrive? |', '|---|---|']
    lines += ['| «%s» | %s |' % (k, '**sì**' if v else 'no') for k, v in words.items()]
    doc = {'schema': 'livello-b-riempimento/1', 'names': names, 'folds': folds, 'pairs': pairs,
           'macro': {p: {'six': macro(folds, p, 'six'), 'without_JAC': macro(folds, p, 'without_JAC'),
                         'members': {m: macro(folds, p, None, m) for m in MEMBERS}} for p in pairs},
           'section_8': verdict, 'statements': words, 'level_A_disc95': level_a_blocks, 'not_vcc_scores': True}
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False, default=float)
        fh.write('\n')
    with out_md.open('x', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(json.dumps({'outcome': verdict['outcome'], 'statements': words, 'usable': usable}, ensure_ascii=False))


if __name__ == '__main__':
    main()
