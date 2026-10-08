"""A quick sheet on a candidate's production effects against a reference, before any generation.

    confronta_effetti.py <candidate.npz> <reference.npz> <out.json>

Both files are in the stage-100 format (targets, genes, lfc in ln, observed). No truth is read and nothing is
scored: the sheet says whether the candidate is the same object as the reference (axes, coverage), how far it
moves (targets changed, distance, per-target correlation, amplitude) and how much of it is common to every
target. It is a technical check and an early signal, not a comparison of predictive value.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def load(path):
    data = Path(path).read_bytes()
    with np.load(path, allow_pickle=False) as z:
        return {'targets': [str(t) for t in z['targets']], 'genes': [str(g) for g in z['genes']],
                'lfc': z['lfc'].astype(np.float64), 'observed': z['observed'].astype(bool),
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def common_share(x):
    mean = x.mean(axis=0)
    return float(x.shape[0] * (mean @ mean) / (x * x).sum())


def main():
    cand, ref, out = load(sys.argv[1]), load(sys.argv[2]), Path(sys.argv[3])
    report = {'candidate': {k: cand[k] for k in ('bytes', 'sha256')}, 'reference': {k: ref[k] for k in ('bytes', 'sha256')},
              'same_targets': cand['targets'] == ref['targets'], 'same_genes': cand['genes'] == ref['genes'],
              'not_a_score': True}
    if not (report['same_targets'] and report['same_genes']):
        report['usable'] = False
    else:
        a, b = np.where(cand['observed'], cand['lfc'], 0.0), np.where(ref['observed'], ref['lfc'], 0.0)
        both = cand['observed'].any(axis=1) & ref['observed'].any(axis=1)
        d = a - b
        changed = np.abs(d).max(axis=1) > 0
        rows = np.flatnonzero(both)
        corr, ratio, flips = [], [], []
        for i in rows:
            x, y = a[i], b[i]
            sx, sy = x.std(), y.std()
            corr.append(float(np.corrcoef(x, y)[0, 1]) if sx > 0 and sy > 0 else float('nan'))
            ratio.append(float(np.linalg.norm(x) / np.linalg.norm(y)) if np.linalg.norm(y) > 0 else float('nan'))
            top = np.argsort(-np.abs(y))[:50]
            flips.append(float((np.sign(x[top]) != np.sign(y[top])).mean()))
        corr, ratio, flips = np.array(corr), np.array(ratio), np.array(flips)
        worst = [cand['targets'][rows[k]] for k in np.argsort(np.nan_to_num(corr, nan=2.0))[:10]]
        report.update(
            usable=True, finite=bool(np.isfinite(cand['lfc']).all()),
            targets_predicted={'candidate': int(cand['observed'].any(axis=1).sum()),
                               'reference': int(ref['observed'].any(axis=1).sum())},
            coverage_equal=bool(np.array_equal(cand['observed'], ref['observed'])),
            observed_entries={'candidate': int(cand['observed'].sum()), 'reference': int(ref['observed'].sum())},
            targets_changed=int(changed.sum()), distance_relative_to_reference=float(np.linalg.norm(d) / np.linalg.norm(b)),
            max_abs_difference=float(np.abs(d).max()),
            per_target_correlation={'median': float(np.nanmedian(corr)), 'p05': float(np.nanquantile(corr, 0.05)),
                                    'min': float(np.nanmin(corr)), 'ten_lowest': worst},
            amplitude_ratio={'median': float(np.nanmedian(ratio)), 'p05': float(np.nanquantile(ratio, 0.05)),
                             'p95': float(np.nanquantile(ratio, 0.95))},
            sign_flips_in_the_50_largest_genes_of_the_reference={'median': float(np.median(flips)),
                                                                'p95': float(np.quantile(flips, 0.95))},
            common_share={'candidate': common_share(a[cand['observed'].any(axis=1)]),
                          'reference': common_share(b[ref['observed'].any(axis=1)])})
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('candidate', 'reference')}, indent=1))


if __name__ == '__main__':
    main()
