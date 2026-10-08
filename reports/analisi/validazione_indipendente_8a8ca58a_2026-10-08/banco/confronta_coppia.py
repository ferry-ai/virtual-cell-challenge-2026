"""Does a pair of a six-member bench reproduce the same pair of an earlier kernel of the same fold?

    confronta_coppia.py <pair> <completion dir A> <completion dir B> <out.json>

Compares, seed by seed, the paired differences of the six members and of each member in bench_full/paired.json.
The two kernels share real cells, effects of the two arms, bench code and seeds: the values must coincide.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def full(root):
    hit = next(p for p in Path(root).rglob('paired.json') if p.parent.name == 'bench_full')
    return json.loads(hit.read_text(encoding='utf-8'))['pairs']


def main():
    pair, a, b, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    pa, pb = full(a)[pair], full(b)[pair]
    gaps = {'six': max(abs(x - y) for x, y in zip(pa['six']['values'], pb['six']['values'])),
            'without_JAC': max(abs(x - y) for x, y in zip(pa['without_JAC']['values'], pb['without_JAC']['values']))}
    for m in pa['members']:
        gaps[m] = max(abs(x - y) for x, y in zip(pa['members'][m]['values'], pb['members'][m]['values']))
    report = {'pair': pair, 'a': str(Path(a).as_posix()), 'b': str(Path(b).as_posix()),
              'six_a': pa['six']['values'], 'six_b': pb['six']['values'], 'largest_absolute_gap': gaps,
              'reproduced': max(gaps.values()) < 1e-9}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'pair': pair, 'reproduced': report['reproduced'], 'largest_gap': max(gaps.values())}))


if __name__ == '__main__':
    main()
