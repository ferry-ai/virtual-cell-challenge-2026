"""Technical sheet of T3 (T1 plus quarter-weight KO votes) against T1, on production effects, no truth read.

    scheda_t3.py <T3 effects npz> <T1 effects npz> <T3 consumption receipt json> <out.json>

Checks what the protocol promises (nothing changes outside the KO-supported targets, T1 coverage is kept) and
describes what the KO votes do: how far each changed target moves, how much of the change is one row common to
the changed targets (the uncentred KO response the protocol names as its risk), and how large the predictions are
where only a KO vote exists. Not a comparison of predictive value.
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
        return ([str(t) for t in z['targets']], [str(g) for g in z['genes']], z['lfc'].astype(np.float64),
                z['observed'].astype(bool), hashlib.sha256(data).hexdigest())


def q(x):
    x = np.asarray(x, float)
    return {'median': float(np.median(x)), 'p95': float(np.quantile(x, 0.95)), 'max': float(x.max())}


def main():
    t3_path, t1_path, receipt_path, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    targets, genes, a, oa, sha3 = load(t3_path)
    targets1, genes1, b, ob, sha1 = load(t1_path)
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    assert targets == targets1 and genes == genes1, 'axes differ'
    a0, b0 = np.where(oa, a, 0.0), np.where(ob, b, 0.0)
    d = a0 - b0
    changed = np.flatnonzero(np.abs(d).max(axis=1) > 0)
    names = [targets[i] for i in changed]
    declared = receipt['changed_targets']
    new_pairs = oa & ~ob
    lost_pairs = ob & ~oa
    per = {}
    for i in changed:
        both = oa[i] & ob[i]
        x, y = a0[i][both], b0[i][both]
        per[targets[i]] = {
            'correlation_with_T1_where_both_predict': float(np.corrcoef(x, y)[0, 1]),
            'distance_relative_to_T1': float(np.linalg.norm(d[i][both]) / np.linalg.norm(y)),
            'norm_ratio': float(np.linalg.norm(x) / np.linalg.norm(y)),
            'pairs_predicted_by_KO_only': int(new_pairs[i].sum()),
            'max_abs_where_KO_only': float(np.abs(a0[i][new_pairs[i]]).max()) if new_pairs[i].any() else 0.0}
    dc = d[changed]
    mean_row = dc.mean(axis=0)
    common = float(dc.shape[0] * (mean_row @ mean_row) / (dc * dc).sum())
    ko_only = np.abs(a0[new_pairs])
    report = {
        'T3_sha256': sha3, 'T1_sha256': sha1, 'not_a_score': True,
        'changed_targets': len(names), 'changed_equal_to_receipt': sorted(names) == sorted(declared),
        'T1_coverage_kept': bool(not lost_pairs.any()),
        'pairs_predicted_by_KO_only': int(new_pairs.sum()), 'targets_with_KO_only_pairs': int(new_pairs.any(axis=1).sum()),
        'abs_effect_where_KO_only': q(ko_only) if ko_only.size else None,
        'abs_effect_of_T1_on_the_same_targets': q(np.abs(b0[changed][ob[changed]])),
        'distance_of_T3_from_T1_relative_all_targets': float(np.linalg.norm(d) / np.linalg.norm(b0)),
        'per_changed_target': {
            'correlation_with_T1': q([-v['correlation_with_T1_where_both_predict'] for v in per.values()]),
            'correlation_with_T1_min': float(min(v['correlation_with_T1_where_both_predict'] for v in per.values())),
            'correlation_with_T1_median': float(np.median([v['correlation_with_T1_where_both_predict'] for v in per.values()])),
            'distance_relative_to_T1': q([v['distance_relative_to_T1'] for v in per.values()]),
            'norm_ratio': q([v['norm_ratio'] for v in per.values()])},
        'share_of_the_change_common_to_the_changed_targets': common,
        'most_moved': sorted(per, key=lambda t: -per[t]['distance_relative_to_T1'])[:8],
        'targets': per}
    del report['per_changed_target']['correlation_with_T1']
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'targets'}, indent=1))
    for t in report['most_moved']:
        print(t, {k: round(v, 4) for k, v in per[t].items()})


if __name__ == '__main__':
    main()
