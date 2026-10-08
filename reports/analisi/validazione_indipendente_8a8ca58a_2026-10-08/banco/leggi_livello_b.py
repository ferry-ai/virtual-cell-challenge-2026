"""Read the six-member benches (level B) by section 8 of the contract, and write tables and verdicts.

    leggi_livello_b.py <level A reading json (v2)> <out.md> <out.json> <fold>=<completion dir> [<fold>=<dir> ...]

Per fold: the technical checks (bench completed, inputs verified by sha256, archived bench code, the control
with exchanged rows), then for every declared pair the paired difference over the five generator seeds on the
six members, on the five without JAC and on each member, with bench_v2's own "resolved" (|mean| > 2 sd / sqrt 5).
Macro: the mean over folds of the per-seed differences, same convention. Verdict per contrast by section 8:
favourable needs at least two folds, a resolved positive macro of the six members with the same sign without
JAC, no fold with a resolved loss of the six members or of PDS, and level A without a resolved loss of
discrimination. Local scales on half-depth truths: not VCC scores.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

MEMBERS = ('PDS', 'MSE', 'NMAE', 'FID', 'REACH', 'JAC')
CONTRASTS = {'K1': ('full', 'T1:T0'), 'K0': ('full', 'T0:P4')}
LEVEL_A_ID = {'K1': 'K1', 'K0': 'K0'}


def stats(values) -> dict:
    v = np.asarray(values, float)
    sd = float(v.std(ddof=1)) if v.size > 1 else float('nan')
    return {'mean': float(v.mean()), 'sd': sd, 'values': [float(x) for x in v],
            'resolved': bool(abs(v.mean()) > 2 * sd / np.sqrt(v.size)) if v.size > 1 else False}


def cell(s) -> str:
    if s is None:
        return '—'
    return '%+.4f ± %.4f%s' % (s['mean'], s['sd'], ' **ris.**' if s['resolved'] else '')


def find(root: Path, name: str) -> Path:
    hits = sorted(root.rglob(name))
    if not hits:
        raise FileNotFoundError('%s under %s' % (name, root))
    return hits[0]


def read_fold(root: Path) -> dict:
    done = json.loads(find(root, 'bench_done.json').read_text(encoding='utf-8'))
    out = {'ok': bool(done.get('ok')), 'steps': done.get('steps'), 'targets': done.get('targets'), 'runs': {}}
    for step in ('control', 'changed', 'full'):
        hits = [p for p in root.rglob('paired.json') if p.parent.name == 'bench_' + step]
        if not hits:
            continue
        paired = json.loads(hits[0].read_text(encoding='utf-8'))
        run = json.loads((hits[0].parent / 'run.json').read_text(encoding='utf-8'))
        bench = json.loads(find(hits[0].parent, 'bench.json').read_text(encoding='utf-8'))
        out['runs'][step] = {'pairs': paired['pairs'], 'n_pred': paired['n_pred'], 'gen_seeds': paired['gen_seeds'],
                             'emission': paired['emission'], 'code_sha256': run['code_sha256'],
                             'targets': len(bench.get('targets', [])) or None}
    return out


def main() -> None:
    level_a = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    out_md, out_json = Path(sys.argv[2]), Path(sys.argv[3])
    folds = {}
    for item in sys.argv[4:]:
        name, root = item.split('=', 1)
        folds[name] = read_fold(Path(root))
    lines = ['## Controlli tecnici del livello B', '',
             '| Fold | Banco concluso | Bersagli | Controllo: PDS di T0 − T0 a righe scambiate (1 seme) | Banco utilizzabile |',
             '|---|---|---:|---:|---|']
    usable = {}
    for name, f in folds.items():
        ctrl = f['runs'].get('control', {}).get('pairs', {}).get('T0:T0shuffle')
        gap = ctrl['members']['PDS']['mean'] if ctrl else None
        usable[name] = bool(f['ok'] and gap is not None and gap > 0)
        lines.append('| %s | %s | %s | %s | %s |' % (
            name, 'sì' if f['ok'] else '**no**', f['targets']['all'] if f.get('targets') else '—',
            '—' if gap is None else '%+.4f' % gap, 'sì' if usable[name] else '**no**'))
    verdicts = {}
    for cid, (step, pair) in CONTRASTS.items():
        first, second = pair.split(':')
        lines += ['', '## %s — %s − %s, sei membri (scala locale), 400 cellule per bersaglio, 5 semi' % (cid, first, second), '',
                  '| Fold | Sei membri | Senza JAC | ' + ' | '.join(MEMBERS) + ' |', '|---|---|---|' + '---|' * len(MEMBERS)]
        per_fold, six_by_seed, nojac_by_seed, pds_by_seed = {}, [], [], []
        for name, f in folds.items():
            p = f['runs'].get(step, {}).get('pairs', {}).get(pair)
            if p is None or not usable[name]:
                lines.append('| %s | non disponibile | | ' % name + ' | ' * (len(MEMBERS) - 1) + '|')
                continue
            per_fold[name] = {'six': p['six'], 'without_JAC': p['without_JAC'],
                              'members': {m: p['members'][m] for m in MEMBERS},
                              'raw_members': {m: p['raw_members'][m] for m in MEMBERS}}
            six_by_seed.append(p['six']['values'])
            nojac_by_seed.append(p['without_JAC']['values'])
            pds_by_seed.append(p['members']['PDS']['values'])
            lines.append('| %s | %s | %s | %s |' % (name, cell(p['six']), cell(p['without_JAC']),
                                                    ' | '.join(cell(p['members'][m]) for m in MEMBERS)))
        macro = None
        if per_fold:
            macro = {'six': stats(np.mean(six_by_seed, axis=0)), 'without_JAC': stats(np.mean(nojac_by_seed, axis=0)),
                     'PDS': stats(np.mean(pds_by_seed, axis=0)), 'folds': len(per_fold)}
            lines.append('| **macro, %d fold** | %s | %s | %s | | | | | |' % (
                len(per_fold), cell(macro['six']), cell(macro['without_JAC']), cell(macro['PDS'])))
        a = level_a['reading'][LEVEL_A_ID[cid]]
        loss_folds = [n for n, v in per_fold.items()
                      if (v['six']['resolved'] and v['six']['mean'] < 0)
                      or (v['members']['PDS']['resolved'] and v['members']['PDS']['mean'] < 0)]
        level_a_stop = bool(a['folds_with_resolved_negative'] or a['macro_resolved_negative'])
        if not per_fold:
            verdict, why = 'INCONCLUDENTE', 'nessun fold di livello B utilizzabile'
        elif macro['six']['resolved'] and macro['six']['mean'] < 0:
            verdict, why = 'VALIDO E SFAVOREVOLE', 'macro dei sei membri risolta negativa'
        elif loss_folds:
            verdict, why = 'VALIDO E SFAVOREVOLE', 'regressione risolta della media o del PDS su: ' + ', '.join(loss_folds)
        elif a['macro_resolved_negative']:
            verdict, why = 'VALIDO E SFAVOREVOLE', 'macro di disc95 risolta negativa nel livello A'
        elif (len(per_fold) >= 2 and macro['six']['resolved'] and macro['six']['mean'] > 0
              and macro['without_JAC']['mean'] > 0 and not level_a_stop):
            verdict, why = 'VALIDO E FAVOREVOLE', 'macro risolta positiva su %d fold, nessuna regressione risolta' % len(per_fold)
        else:
            reasons = []
            if len(per_fold) < 2:
                reasons.append('meno di due fold di livello B')
            if not macro['six']['resolved']:
                reasons.append('macro dei sei membri non risolta')
            elif macro['six']['mean'] > 0 and macro['without_JAC']['mean'] <= 0:
                reasons.append('il segno cambia senza JAC')
            if level_a_stop:
                reasons.append('livello A: discriminazione risolta negativa su ' + ', '.join(a['folds_with_resolved_negative']))
            verdict, why = 'INCONCLUDENTE', '; '.join(reasons) or 'condizioni del §8 non tutte soddisfatte'
        verdicts[cid] = {'pair': pair, 'verdict': verdict, 'why': why, 'macro': macro, 'per_fold': per_fold,
                         'folds_with_resolved_loss': loss_folds, 'level_A': a['level_A_reading']}
        lines += ['', '**Esito del §8 per %s (%s):** %s — %s.' % (cid, pair, verdict, why)]
    changed = {}
    lines += ['', '## Solo i bersagli con voti nuovi (corsa «cambiati»)', '',
              '| Fold | Bersagli | Coppia | Sei membri | Senza JAC | PDS | NMAE | FID | REACH |', '|---|---:|---|---|---|---|---|---|---|']
    for name, f in folds.items():
        run = f['runs'].get('changed')
        if not run or not usable[name]:
            continue
        changed[name] = {}
        for pair, p in run['pairs'].items():
            changed[name][pair] = {'six': p['six'], 'without_JAC': p['without_JAC'],
                                   'members': {m: p['members'][m] for m in MEMBERS}}
            lines.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s |' % (
                name, len(f['targets']['changed']), pair, cell(p['six']), cell(p['without_JAC']),
                cell(p['members']['PDS']), cell(p['members']['NMAE']), cell(p['members']['FID']),
                cell(p['members']['REACH'])))
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump({'usable': usable, 'verdicts': verdicts, 'changed_only': changed,
                   'folds': {n: {'ok': f['ok'], 'steps': f['steps'], 'targets': f['targets']} for n, f in folds.items()},
                   'rule': 'contract v2, section 8', 'not_vcc_scores': True}, fh, indent=1)
        fh.write('\n')
    print(json.dumps({c: (v['verdict'], v['why']) for c, v in verdicts.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
