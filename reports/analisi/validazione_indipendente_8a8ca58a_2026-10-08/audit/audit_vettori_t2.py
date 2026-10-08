"""Audit of the T2 common vectors delivered by DATI-TRANSFER: audit_vettori_t2.py <out.json>

Read-only. For the production and the T (hidden targets) release: every per-source object has the size and
sha256 its manifest declares; the assembled common.npz and support.npz hold exactly those vectors and
denominators; the evidence of each source names its producer and split. Across the two releases: the share of
targets left behind each vector under the hidden-target rule (one group in five hidden: about 0.8 expected).
It does not recompute a mean from cells: that would need the producers' inputs.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
DT = REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34'


def pin(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def release(name):
    manifest_path = DT / name
    m = json.loads(manifest_path.read_text(encoding='utf-8'))
    out = {'manifest': dict(pin(manifest_path), path=manifest_path.relative_to(REPO).as_posix()),
           'regime': m['regime'], 'policy': m.get('policy'), 'sources': {}, 'problems': []}
    with np.load(m['common']['path'], allow_pickle=False) as c, np.load(m['support']['path'], allow_pickle=False) as s:
        out['assembled'] = {k: {'declared': {x: m[k][x] for x in ('bytes', 'sha256')}, 'read': pin(m[k]['path'])}
                            for k in ('common', 'support')}
        for k, v in out['assembled'].items():
            if v['declared'] != v['read']:
                out['problems'].append('assembled %s differs from its manifest' % k)
        for source, spec in sorted(m['sources'].items()):
            obj, ev = spec['object'], spec['evidence']
            got = pin(obj['path'])
            entry = {'object_equal_to_manifest': got == {x: obj[x] for x in ('bytes', 'sha256')},
                     'evidence_equal_to_manifest': pin(ev['path']) == {x: ev[x] for x in ('bytes', 'sha256')}}
            evidence = json.loads(Path(ev['path']).read_text(encoding='utf-8'))
            entry['producer'] = evidence.get('producer') or evidence.get('source') or 'see evidence'
            split = spec['split'] if isinstance(spec['split'], dict) else {'note': spec['split']}
            entry['split'] = {k: split.get(k) for k in ('id', 'regime', 'protected_units', 'note') if split.get(k)}
            entry['hidden_targets_in_split'] = len(split.get('hidden_targets') or [])
            with np.load(obj['path'], allow_pickle=False) as z:
                keys = set(z.files)
                if {'common', 'contributing_targets'} <= keys:
                    vec, count = np.asarray(z['common'], np.float64), np.asarray(z['contributing_targets'])
                elif source in keys:                      # a set-shaped file (K562 bulk, CD4 mix)
                    vec = np.asarray(z[source], np.float64)
                    count = np.asarray(z['support']) if 'support' in keys else None
                else:
                    vec, count = None, None
                entry['object_keys'] = sorted(keys)[:12]
            if vec is not None:
                entry['vector_equal_to_assembled'] = bool(np.array_equal(vec, np.asarray(c[source], np.float64)))
                if count is not None:
                    entry['support_equal_to_assembled'] = bool(np.array_equal(count, np.asarray(s[source])))
            behind = np.asarray(s[source])
            entry['targets_behind_max'] = int(behind.max())
            if not (entry['object_equal_to_manifest'] and entry['evidence_equal_to_manifest']
                    and entry.get('vector_equal_to_assembled', False)):
                out['problems'].append(source)
            out['sources'][source] = entry
    return out


def main():
    out = Path(sys.argv[1])
    prod, hidden = release('common_release_production_r1.json'), release('common_release_T_r1.json')
    ratio = {s: hidden['sources'][s]['targets_behind_max'] / prod['sources'][s]['targets_behind_max']
             for s in prod['sources'] if s in hidden['sources']}
    report = {'production': prod, 'T': hidden, 'targets_behind_T_over_production': ratio,
              'expected_share_under_the_rule': 0.8, 'not_a_recomputation_from_cells': True}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'production_problems': prod['problems'], 'T_problems': hidden['problems'],
                      'ratio': {k: round(v, 3) for k, v in ratio.items()},
                      'hidden_in_T_splits': {s: e['hidden_targets_in_split'] for s, e in hidden['sources'].items()},
                      'keys_example': {s: e['object_keys'] for s, e in list(prod['sources'].items())[:3]},
                      'k562_keys': prod['sources']['k562']['object_keys'], 'cd4_keys': prod['sources']['cd4_mix']['object_keys']}))


if __name__ == '__main__':
    main()
