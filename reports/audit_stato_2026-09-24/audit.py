"""Reproduce the exploratory audit from saved stage-98 caches; no submission.

Run: scripts\\py.cmd reports\\audit_stato_2026-09-24\\audit.py
Outputs are immutable; pass a new --out for a repeat.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from vcc2026.genes import official_axis
from vcc2026.multisource import AxisTable, mix

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, default=Path(__file__).with_name('measurements.json'))
args = p.parse_args()
if args.out.exists():
    raise FileExistsError(args.out)
cache = Path('C:/Users/ferra/vcc2026-data/processed/multisource_2026-09-23_r5')
panel = pd.read_csv('C:/Users/ferra/vcc2026-data/raw/controls/pert_counts.csv').iloc[:, 0].astype(str).tolist()
axis = list(official_axis().symbols)
names = ['k562', 'cd4_mix', 'orion_hct116', 'orion_hek293t']
tabs = {}
hashes = {}
for name in names + ['cd4_halfA', 'cd4_halfB']:
    path = cache / (name + '.npz')
    hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with np.load(path, allow_pickle=False) as z:
        tabs[name] = AxisTable(name, z['targets'].astype(str).tolist(), z['raw'], z['raw'], z['se'], z['n_cells'])

def quantiles(v):
    v = np.asarray(v)
    v = v[np.isfinite(v)]
    return dict(zip(['p10', 'p50', 'p90'], map(float, np.quantile(v, [.1, .5, .9])))) if len(v) else None

result = {'claim_type': 'exploratory measurements; not VCC scores; no model selection',
          'cache': str(cache), 'sha256': hashes, 'seed': 20260924,
          'method': 'Top 100 abs predicted effects, own target excluded; 50 random nonzero cyclic target shifts. CIs bootstrap targets, conditional on these sources.',
          'coverage': {}, 'direction': {}}
for name, tab in tabs.items():
    result['coverage'][name] = {'targets': len(tab.targets), 'cells': quantiles(tab.n_cells),
                              'genes_measured': int(np.isfinite(tab.raw).any(axis=0).sum()),
                              'se_finite_fraction': float(np.isfinite(tab.se).mean())}

for held in names + ['cd4_halfB']:
    truth = tabs[held]
    others = [tabs[n] for n in names if n != held] if held != 'cd4_halfB' else [tabs['cd4_halfA']]
    targets = [t for t in panel if t in truth.index() and any(t in a.index() for a in others)]
    obs = truth.rows(targets)
    se = truth.se[[truth.index()[t] for t in targets]]
    for gamma in [0., 1.]:
        pred, w = mix(others, targets, gamma=gamma, reliability_scale=100.)
        rng = np.random.default_rng(20260924)
        shifts = rng.integers(1, len(targets), 50)
        rows = []
        for i, target in enumerate(targets):
            valid = (w[i] > 0) & np.isfinite(obs[i]) & (pred[i] != 0) & (obs[i] != 0)
            if target in axis:
                valid[axis.index(target)] = False
            ids = np.flatnonzero(valid)
            ids = ids[np.argsort(-np.abs(pred[i, ids]), kind='stable')[:100]]
            if not len(ids):
                continue
            signs = np.sign(pred[i, ids])
            y = obs[i, ids]
            agreement = float(np.mean(signs == np.sign(y)))
            null = []
            for shift in shifts:
                other = obs[(i + shift) % len(targets), ids]
                ok = np.isfinite(other) & (other != 0)
                null.append(float(np.mean(signs[ok] == np.sign(other[ok]))))
            confident = np.isfinite(se[i, ids]) & (np.abs(y) >= 2 * se[i, ids])
            rows.append({'target': target, 'agreement': agreement,
                         'shifted_mean': float(np.mean(null)),
                         'all_up': float(np.mean(y > 0)), 'all_down': float(np.mean(y < 0)),
                         'truth_z2_n': int(confident.sum()),
                         'truth_z2_correct': int((signs[confident] == np.sign(y[confident])).sum())})
        delta = np.array([r['agreement'] - r['shifted_mean'] for r in rows])
        boots = np.mean(delta[rng.integers(0, len(delta), (2000, len(delta)))], axis=1)
        conf_n = sum(r['truth_z2_n'] for r in rows)
        result['direction'][held + '_gamma' + str(int(gamma))] = {
            'targets': len(rows), 'agreement_mean': float(np.mean([r['agreement'] for r in rows])),
            'agreement_median': float(np.median([r['agreement'] for r in rows])),
            'shifted_mean': float(np.mean([r['shifted_mean'] for r in rows])),
            'always_up_mean': float(np.mean([r['all_up'] for r in rows])),
            'always_down_mean': float(np.mean([r['all_down'] for r in rows])),
            'paired_delta_bootstrap95': list(map(float, np.quantile(boots, [.025, .975]))),
            'truth_z2_n': conf_n,
            'truth_z2_pooled_agreement': sum(r['truth_z2_correct'] for r in rows) / conf_n if conf_n else None,
            'per_target': rows}
        print(held, gamma, {k: v for k, v in result['direction'][held + '_gamma' + str(int(gamma))].items() if k != 'per_target'}, flush=True)

a, wa = mix([tabs[n] for n in names[:3]], panel, gamma=1., reliability_scale=100.)
b, wb = mix([tabs[n] for n in names], panel, gamma=1., reliability_scale=100.)
a *= .394
b *= .4285
qa = np.quantile(np.abs(a), .99, axis=1)
qb = np.quantile(np.abs(b), .99, axis=1)
na = np.linalg.norm(a, axis=1)
nb = np.linalg.norm(b, axis=1)
active = (na > 0) & (nb > 0)
cos = np.sum(a[active] * b[active], axis=1) / (na[active] * nb[active])
ratio = qb[active] / qa[active]
result['t17_vs_t15'] = {'active_targets': int(active.sum()),
    'q99_medians': [float(np.median(qa)), float(np.median(qb))],
    'per_target_q99_ratio': quantiles(ratio),
    'per_target_norm_ratio': quantiles(nb[active] / na[active]),
    'per_target_cosine': quantiles(cos),
    'q99_ratio_outside_20_percent': int(((ratio < .8) | (ratio > 1.2)).sum()),
    'total_energy_ratio': float(np.sum(b*b) / np.sum(a*a)),
    'targets_missing_both': [t for t, ok in zip(panel, active) if not ok]}
print('t17_vs_t15', result['t17_vs_t15'], flush=True)
with args.out.open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2, allow_nan=False)
