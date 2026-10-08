"""Describe what the frozen common vectors change, from a collected level-A run and the fold effects kept in the
data root: descrivi_t2.py <level A completion> <extra dir> <out.json> <fold>=<effects dir> [...]

Measured, no adoption rule: the level of the shuffled control, the gamma-0 parity by sha256 of the effects, how
far T2 moves from T1, and the share of each arm's effects that is common to all targets (n * |mean row|^2 / |M|^2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def common_share(lfc, obs):
    x = np.where(obs, lfc, 0.0).astype(np.float64)
    rows = obs.any(axis=1)
    x = x[rows]
    mean = x.mean(axis=0)
    return float(x.shape[0] * (mean @ mean) / (x * x).sum()), float(np.sqrt((x * x).sum(axis=1)).mean())


def main():
    completion, extra, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    results = json.loads((completion / 'results.json').read_text(encoding='utf-8'))
    report = {'not_vcc_scores': True, 'shuffle': {}, 'gamma0_parity_sha256': {}, 'frozen_common': {}, 'effects': {},
              'context_macro': {}}
    for fid, block in results['folds'].items():
        for tname, t in block['truth'].items():
            if t.get('skipped') or t['role'] != 'primary':
                continue
            arms = t['arms']
            report['shuffle'][fid] = {a: arms[a]['disc95'] for a in ('T2', 'T2~shuffle', 'T1', 'T1~shuffle', 'T0~null')
                                      if a in arms}
    for path in sorted((extra / 'stage100_manifests').glob('T2g0__*.json')):
        ctx = path.stem.split('__')[1]
        a = json.loads(path.read_text(encoding='utf-8'))
        b = json.loads((path.parent / ('T1g0__%s.json' % ctx)).read_text(encoding='utf-8'))
        sa, sb = a['contexts'][ctx]['sha256'], b['contexts'][ctx]['sha256']
        report['gamma0_parity_sha256'][ctx] = {'T2g0': sa, 'T1g0': sb, 'equal': sa == sb}
    for path in sorted((extra / 'stage100_manifests').glob('T2__*.json')):
        ctx = path.stem.split('__')[1]
        m = json.loads(path.read_text(encoding='utf-8'))
        info = m.get('common') or {}
        panel = json.loads((path.parent / ('T1__%s.json' % ctx)).read_text(encoding='utf-8')).get('common') or {}
        report['frozen_common'][ctx] = {'T2': {k: info.get(k) for k in ('mode', 'sha256', 'norm', 'unused_keys')},
                                        'T1': panel}
    for cid in ('K2', 'K2t0', 'c_gamma0', 'c_shuffle_T2'):
        report['context_macro'][cid] = {m: {k: v[k] for k in ('mean', 'lo', 'hi', 'resolved')}
                                        for m, v in results['macro'][cid]['measures'].items() if v.get('mean') is not None}
    for item in sys.argv[4:]:
        fid, folder = item.split('=', 1)
        loaded = {}
        for arm in ('T0', 'T1', 'T2'):
            with np.load(Path(folder) / (arm + '.npz'), allow_pickle=False) as z:
                loaded[arm] = (z['lfc'].astype(np.float64), z['observed'].astype(bool))
        entry = {}
        for arm, (lfc, obs) in loaded.items():
            share, row_norm = common_share(lfc, obs)
            entry[arm] = {'common_share': share, 'mean_row_norm': row_norm, 'targets': int(obs.any(axis=1).sum())}
        d = loaded['T2'][0] - loaded['T1'][0]
        entry['T2_minus_T1'] = {'observed_equal': bool(np.array_equal(loaded['T2'][1], loaded['T1'][1])),
                                'max_abs': float(np.abs(d).max()), 'l2': float(np.linalg.norm(d)),
                                'l2_relative_to_T1': float(np.linalg.norm(d) / np.linalg.norm(loaded['T1'][0])),
                                'rows_identical_across_targets': bool(np.allclose(d[loaded['T1'][1].any(axis=1)].std(axis=0), 0, atol=1e-6))}
        report['effects'][fid] = entry
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'shuffle': report['shuffle'], 'gamma0': {k: v['equal'] for k, v in report['gamma0_parity_sha256'].items()},
                      'effects': report['effects'], 'macro': report['context_macro']}, indent=1))


if __name__ == '__main__':
    main()
