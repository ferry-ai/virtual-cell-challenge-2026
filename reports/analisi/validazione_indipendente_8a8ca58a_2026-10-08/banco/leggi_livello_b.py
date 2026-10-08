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


def read_fold(root: Path, control_root: Path | None = None) -> dict:
    """``control_root``: a kernel that ran only the full step takes the exchanged-rows control from another
    run of the same fold (same real cells, same T0 effects); the table says so."""
    done = json.loads(find(root, 'bench_done.json').read_text(encoding='utf-8'))
    steps = dict(done.get('steps') or {})
    borrowed = None
    if control_root is not None and 'control' not in steps:
        other = json.loads(find(control_root, 'bench_done.json').read_text(encoding='utf-8'))
        borrowed = (other.get('steps') or {}).get('control')
        if borrowed:
            steps['control'] = borrowed
    # the verdict needs the control and the full run; the changed-targets run is a secondary reading, and its
    # failure is reported without making the fold unusable
    needed = all((steps.get(s) or {}).get('returncode') == 0 for s in ('control', 'full'))
    out = {'ok': needed, 'all_steps_ok': bool(done.get('ok')), 'steps': steps, 'targets': done.get('targets'),
           'runs': {}, 'control_borrowed_from': control_root.as_posix() if borrowed else None}
    for step in ('control', 'changed', 'full'):
        hits = [p for p in root.rglob('paired.json') if p.parent.name == 'bench_' + step]
        if not hits and step == 'control' and borrowed:
            hits = [p for p in control_root.rglob('paired.json') if p.parent.name == 'bench_control']
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
    args = sys.argv[1:]
    contrasts, level_a_id, control_from = dict(CONTRASTS), dict(LEVEL_A_ID), {}
    if '--contrasts' in args:          # the pairs of another full run, id=FIRST:SECOND,...; same id in level A
        i = args.index('--contrasts')
        contrasts = {c.split('=')[0]: ('full', c.split('=')[1]) for c in args[i + 1].split(',')}
        level_a_id = {c: c for c in contrasts}
        del args[i:i + 2]
    while '--control' in args:         # <fold>=<completion dir of the run that holds the control of that fold>
        i = args.index('--control')
        name, root = args[i + 1].split('=', 1)
        control_from[name] = Path(root)
        del args[i:i + 2]
    level_a = json.loads(Path(args[0]).read_text(encoding='utf-8'))
    out_md, out_json = Path(args[1]), Path(args[2])
    folds = {}
    for item in args[3:]:
        name, root = item.split('=', 1)
        folds[name] = read_fold(Path(root), control_from.get(name))
    failed = {n: [s for s, v in f['steps'].items() if v.get('returncode') not in (0, None)] for n, f in folds.items()}
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
    for n, f in folds.items():
        if f['control_borrowed_from']:
            lines += ['', 'Nel fold %s il controllo a righe scambiate è quello della corsa `%s`, sugli stessi dati: '
                      'questo kernel ha eseguito la sola corsa principale.' % (n, f['control_borrowed_from'])]
    for n, steps in failed.items():
        if steps:
            lines += ['', "Nel fold %s la corsa secondaria %s è fallita: non entra nell'esito del §8 e la tabella dei "
                      "soli bersagli cambiati non la riporta." % (n, ', '.join('«%s»' % s for s in steps))]
    verdicts = {}
    for cid, (step, pair) in contrasts.items():
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
        a = level_a['reading'][level_a_id[cid]]
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
                   'folds': {n: {'ok': f['ok'], 'all_steps_ok': f['all_steps_ok'], 'steps': f['steps'],
                                 'targets': f['targets'], 'control_borrowed_from': f['control_borrowed_from']}
                             for n, f in folds.items()},
                   'rule': 'contract v2, section 8', 'not_vcc_scores': True}, fh, indent=1)
        fh.write('\n')
    print(json.dumps({c: (v['verdict'], v['why']) for c, v in verdicts.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
