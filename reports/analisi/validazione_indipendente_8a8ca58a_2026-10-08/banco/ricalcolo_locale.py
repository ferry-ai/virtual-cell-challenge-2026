"""Recompute, on the laptop, the level-A measures of one fold from the files the cloud run wrote.

A run that completes is not proof that its numbers are right. This reads the four arms of a fold as the
level-A kernel saved them (verified against its consumption receipt), the truth table of the held lineage
from a local copy (verified against the release pin), recomputes every measure with `metrics.py` exactly as
`bench_core.measure` does for the manifest arms, and compares the per-arm means and the K1 and K0 differences
with the kernel's results.json. Different machine, different numpy; no stage 100 here, only the measures.

    py ricalcolo_locale.py <fold id> <arms dir> <truth npz> <level-A completion dir> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402

REPO = HERE.parents[3]
RELEASE = REPO / 'reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json'
CONSUMO = REPO / 'reports/modelli/banca_canonica_2026-10-07/fit/r1/completion/consumo.json'
ARMS = ('T0', 'R1', 'T1', 'P4')
REPORTED = (*M.MEASURES, 'disc95')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for b in iter(lambda: fh.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    fold, arms_dir, truth_path, completion, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    results = json.loads((completion / 'results.json').read_text(encoding='utf-8'))
    consumption = {(c['label'], c['context']): c for c in json.loads((completion / 'consumption.json').read_text())}
    release = json.loads(RELEASE.read_text(encoding='utf-8'))
    block = results['folds'][fold]
    tname = next(t for t, v in block['truth'].items() if v['role'] == 'primary')
    checks = {'truth_sha256_equals_release_pin': sha(truth_path) == release['voted'][tname]['sha256']}
    panel = sorted(json.loads(CONSUMO.read_text(encoding='utf-8'))['votes_per_target'])
    labels = {}
    for a in ARMS:
        path = arms_dir / (a + '.npz')
        checks['%s_sha256_equals_level_A_receipt' % a] = sha(path) == consumption[(a, fold)]['effects_sha256']
        with np.load(path, allow_pickle=False) as z:
            targets, genes = [str(t) for t in z['targets']], [str(g) for g in z['genes']]
            labels[a] = (z['lfc'].astype(np.float32), z['observed'].astype(bool))
    assert sorted(targets) == panel
    with np.load(truth_path, allow_pickle=False) as z:
        t_targets = [str(t) for t in z['targets']]
        shrunk, raw, se = z['shrunk'], z['raw'], z['se']
    axis_pos = {g: i for i, g in enumerate(genes)}
    exclude = sorted(axis_pos[t] for t in targets if t in axis_pos)
    pos = {t: j for j, t in enumerate(t_targets)}
    keep = [i for i, t in enumerate(targets) if t in pos and all(labels[a][1][i].any() for a in ARMS)]
    trow = np.array([pos[targets[i]] for i in keep])
    shrunk, raw, se = shrunk[trow], raw[trow], se[trow]
    valid = {a: M.valid_pairs(labels[a][1][keep], shrunk, raw, se, exclude) for a in ARMS}
    cols = np.logical_and.reduce([valid[a].all(axis=0) for a in ARMS])
    cols95 = np.mean([valid[a] for a in ARMS], axis=0).mean(axis=0) >= 0.95
    per, worst = {}, 0.0
    comparison = {}
    for a in ARMS:
        lfc = labels[a][0][keep]
        per[a] = M.per_target(lfc, valid[a], shrunk, raw, se, cols)
        per[a]['disc95'] = M.per_target(np.where(valid[a], lfc, 0.0), valid[a], np.where(valid[a], shrunk, 0.0),
                                        raw, se, cols95)['disc']
        comparison[a] = {}
        for m in REPORTED:
            with np.errstate(all='ignore'):
                mine = float(np.nanmean(per[a][m]))
            theirs = block['truth'][tname]['arms'][a][m]
            comparison[a][m] = {'local': mine, 'cloud': theirs, 'abs_difference': abs(mine - theirs)}
            worst = max(worst, abs(mine - theirs))
    contrasts = {}
    for cid, first, second in (('K1', 'T1', 'T0'), ('K0', 'T0', 'P4')):
        contrasts[cid] = {}
        for m in ('disc95', 'r_spec'):
            mine = M.strip(M.paired_bootstrap(per[first][m], per[second][m]))
            theirs = block['truth'][tname]['contrasts'][cid]['measures'][m]['all']
            contrasts[cid][m] = {'local': mine, 'cloud': theirs,
                                 'abs_difference_mean': abs(mine['mean'] - theirs['mean']),
                                 'same_resolved': mine['resolved'] == theirs['resolved']}
            worst = max(worst, abs(mine['mean'] - theirs['mean']))
    checks.update(targets_compared_equal=len(keep) == block['truth'][tname]['targets'],
                  genes_for_rank_equal=(int(cols.sum()), int(cols95.sum())) == (
                      block['truth'][tname]['genes_for_rank_strict'], block['truth'][tname]['genes_for_rank_95']),
                  largest_abs_difference=worst, measures_agree_to_1e_6=worst < 1e-6)
    doc = {'fold': fold, 'truth': tname, 'numpy_local': np.__version__, 'checks': checks, 'arms': comparison,
           'contrasts': contrasts}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    print(json.dumps(checks, indent=1))


if __name__ == '__main__':
    main()
