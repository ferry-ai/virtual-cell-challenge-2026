"""Sensitivity of `disc95` to how invalid pairs are masked, on one fold, from local files.

`bench_core.measure` zero-fills, for each arm, the pairs that arm cannot be judged on, in the prediction and
in the truth alike: two arms with different masks are then ranked against slightly different truth vectors
(at most 5% of the entries, by the definition of the gene set). This recomputes the measure with ONE truth
for every arm - zero only where the truth itself is unmeasured - and the prediction zero where unpredicted,
and compares the K1 and K0 differences under the two conventions.

    py sensibilita_disc95.py <arms dir> <truth npz> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402

ARMS = ('T0', 'R1', 'T1', 'P4')


def rank(P, O, cols):
    A, B = np.where(cols, P, 0.0), np.where(cols, O, 0.0)
    cos = (A @ B.T) / np.maximum(np.outer(np.linalg.norm(A, axis=1), np.linalg.norm(B, axis=1)), 1e-12)
    own = np.diag(cos)
    ranks = (cos > own[:, None]).sum(axis=1) + 0.5 * ((cos == own[:, None]).sum(axis=1) - 1)
    return 1.0 - ranks / max(P.shape[0] - 1, 1)


def main() -> None:
    arms_dir, truth_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    labels = {}
    for a in ARMS:
        with np.load(arms_dir / (a + '.npz'), allow_pickle=False) as z:
            targets, genes = [str(t) for t in z['targets']], [str(g) for g in z['genes']]
            labels[a] = (z['lfc'].astype(np.float64), z['observed'].astype(bool))
    with np.load(truth_path, allow_pickle=False) as z:
        pos = {str(t): j for j, t in enumerate(z['targets'])}
        shrunk, raw, se = z['shrunk'], z['raw'], z['se']
    axis_pos = {g: i for i, g in enumerate(genes)}
    exclude = sorted(axis_pos[t] for t in targets if t in axis_pos)
    keep = [i for i, t in enumerate(targets) if t in pos and all(labels[a][1][i].any() for a in ARMS)]
    trow = np.array([pos[targets[i]] for i in keep])
    shrunk, raw, se = shrunk[trow], raw[trow], se[trow]
    valid = {a: M.valid_pairs(labels[a][1][keep], shrunk, raw, se, exclude) for a in ARMS}
    cols95 = np.mean([valid[a] for a in ARMS], axis=0).mean(axis=0) >= 0.95
    truth_ok = M.valid_pairs(np.ones_like(valid['T0']), shrunk, raw, se, exclude)
    one_truth = np.where(truth_ok, np.nan_to_num(shrunk.astype(np.float64)), 0.0)
    per = {}
    for a in ARMS:
        lfc, obs = labels[a][0][keep], labels[a][1][keep]
        own = rank(np.where(valid[a], lfc, 0.0), np.where(valid[a], np.nan_to_num(shrunk.astype(np.float64)), 0.0), cols95)
        shared = rank(np.where(obs & truth_ok, lfc, 0.0), one_truth, cols95)
        per[a] = {'as_run': own, 'one_truth': shared}
    doc = {'targets': len(keep), 'genes_95': int(cols95.sum()),
           'share_of_pairs_in_those_genes_invalid_by_arm': {a: float(1 - valid[a][:, cols95].mean()) for a in ARMS},
           'levels': {a: {k: float(v.mean()) for k, v in per[a].items()} for a in ARMS}, 'contrasts': {}}
    for cid, first, second in (('K1', 'T1', 'T0'), ('K0', 'T0', 'P4')):
        doc['contrasts'][cid] = {k: M.strip(M.paired_bootstrap(per[first][k], per[second][k]))
                                 for k in ('as_run', 'one_truth')}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    print(json.dumps(doc, indent=1))


if __name__ == '__main__':
    main()
