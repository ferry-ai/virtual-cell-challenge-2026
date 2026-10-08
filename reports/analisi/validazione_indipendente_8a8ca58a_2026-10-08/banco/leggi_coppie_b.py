"""Every declared pair of a six-member bench kernel, as a table: no verdict, no retyped number.

    leggi_coppie_b.py <completion or failure dir> <out.md> <out.json>

For each bench run found (bench_<name>/paired.json): the paired difference over the generator seeds on the
six members, on the five without JAC, on each scaled member and on each raw member, with bench_v2's own
"resolved" flag, plus the mean local level of every arm. Local scales on half-depth truths: not VCC scores.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

MEMBERS = ('PDS', 'MSE', 'NMAE', 'FID', 'REACH', 'JAC')


def cell(s) -> str:
    if s['sd'] != s['sd']:
        return '%+.4f' % s['mean']
    return '%+.4f ± %.4f%s' % (s['mean'], s['sd'], ' **ris.**' if s['resolved'] else '')


def main() -> None:
    root, out_md, out_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    done_path = next(iter(sorted(root.rglob('bench_done.json'))), None)
    done = json.loads(done_path.read_text(encoding='utf-8')) if done_path else {}
    lines, doc = [], {'steps': done.get('steps'), 'targets': done.get('targets'), 'runs': {}}
    for paired_path in sorted(root.rglob('paired.json')):
        name = paired_path.parent.name
        paired = json.loads(paired_path.read_text(encoding='utf-8'))
        levels = {}
        scaled = next(iter(paired_path.parent.rglob('scaled_local.csv')), None)
        if scaled:
            by = {}
            for row in csv.DictReader(scaled.open(encoding='utf-8')):
                by.setdefault(row[''].split('@')[0], []).append(row)
            levels = {arm: {k: sum(float(r[k]) for r in rows) / len(rows) for k in (*MEMBERS, 'avg', 'sig/t')}
                      for arm, rows in by.items()}
        lines += ['## Corsa `%s`: %d cellule per bersaglio, %d semi, emissione %s' % (
            name, paired['n_pred'], paired['gen_seeds'], paired['emission']), '']
        if levels:
            lines += ['| Braccio | media | ' + ' | '.join(MEMBERS) + ' | geni chiamati per bersaglio |',
                      '|---|---:|' + '---:|' * (len(MEMBERS) + 1)]
            for arm, v in levels.items():
                lines.append('| %s | %.4f | %s | %.1f |' % (arm, v['avg'], ' | '.join('%.4f' % v[m] for m in MEMBERS),
                                                           v['sig/t']))
            lines.append('')
        lines += ['| Coppia | Sei membri | Senza JAC | ' + ' | '.join(MEMBERS) + ' |',
                  '|---|---|---|' + '---|' * len(MEMBERS)]
        for pair, p in paired['pairs'].items():
            lines.append('| %s | %s | %s | %s |' % (pair, cell(p['six']), cell(p['without_JAC']),
                                                    ' | '.join(cell(p['members'][m]) for m in MEMBERS)))
        lines += ['', '| Coppia, membri grezzi | ' + ' | '.join(MEMBERS) + ' |', '|---|' + '---|' * len(MEMBERS)]
        for pair, p in paired['pairs'].items():
            lines.append('| %s | %s |' % (pair, ' | '.join(cell(p['raw_members'][m]) for m in MEMBERS)))
        lines.append('')
        doc['runs'][name] = {'pairs': paired['pairs'], 'levels': levels, 'n_pred': paired['n_pred'],
                             'gen_seeds': paired['gen_seeds'], 'emission': paired['emission']}
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    print(json.dumps({n: {pr: (round(p['six']['mean'], 4), p['six']['resolved']) for pr, p in r['pairs'].items()}
                      for n, r in doc['runs'].items()}))


if __name__ == '__main__':
    main()
