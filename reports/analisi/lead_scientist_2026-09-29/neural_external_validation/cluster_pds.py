"""Additive target-cluster bootstrap, recalculating PDS inside each resampled panel.

No training, prediction or promotion rule is changed. Full-fold outputs and r2
truth are required. Real use belongs on a runner, not on the laptop.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LEAD = HERE.parent
sys.path.insert(0, str(LEAD))
from verify_neural_runs import verify, canonical_code


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def losses(pred, truth):
    """Pairwise rank losses including diagonal ties, on an already fixed gene mask."""
    p, y = np.asarray(pred, float), np.asarray(truth, float)
    if p.shape != y.shape or p.ndim != 2 or len(p) < 2 or p.shape[1] < 1:
        raise ValueError('Incompatible prediction/truth dimensions')
    if not np.isfinite(p).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite values entered the common measured support')
    cor = (p / np.maximum(np.linalg.norm(p, axis=1)[:, None], 1e-12)) @ (
        y / np.maximum(np.linalg.norm(y, axis=1)[:, None], 1e-12)).T
    own = np.diag(cor)[:, None]
    return (cor > own).astype(float) + .5*(cor == own)


def pds(pair_loss):
    a = np.asarray(pair_loss, float)
    return 1-(a.sum(1)-.5)/(len(a)-1)


def resampled_delta(net_loss, reference_loss, counts):
    """Exact expanded-panel PDS delta, including tied duplicate cluster copies.

    An expanded sample's own cell is excluded once. Other copies of the same
    target are tied competitors; their losses cancel in the arm contrast.
    """
    w = np.atleast_2d(np.asarray(counts, float))
    d = np.asarray(reference_loss, float)-np.asarray(net_loss, float)
    if d.ndim != 2 or d.shape[0] != d.shape[1] or w.shape[1] != len(d):
        raise ValueError('Pair-matrix and weight axes differ')
    if not np.isfinite(w).all() or np.any(w < 0) or np.any(w != np.floor(w)):
        raise ValueError('Cluster counts must be nonnegative integers')
    n = w.sum(1)
    if np.any(n < 2):
        raise ValueError('A bootstrap panel has fewer than two target copies')
    return np.einsum('bi,bi->b', w @ d, w)/(n*(n-1))


def cluster_counts(targets_by_context, n_draws=2000, seed=20260929):
    union = sorted(set().union(*map(set, targets_by_context.values())))
    lookup = {t:i for i,t in enumerate(union)}
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(union), np.full(len(union), 1/len(union)), size=n_draws)
    return union, {c: weights[:, [lookup[t] for t in ts]] for c, ts in targets_by_context.items()}


def load_context(run, manifest, context, rows, data, axes, arrays):
    names, response, official = axes
    rows = np.asarray(rows, int)
    rt = np.asarray(arrays['row_target'][rows], int)
    expected = names[rt]
    path = run / f'pred_{context}.npz'
    with np.load(path, allow_pickle=False) as z:
        if not np.array_equal(z['targets'].astype(str), expected) or not np.array_equal(z['genes'].astype(str), official):
            raise ValueError(f'{context}: exported axes do not match frozen rows/official genes')
        pred = {arm: z[arm][:, response.axis_index.to_numpy(int)] for arm in ('net','transfer','blind')}
    finite = np.isfinite(pred['net'])
    if any(not np.array_equal(np.isfinite(x), finite) for x in pred.values()):
        raise ValueError(f'{context}: model-space masks differ across compared arms')
    raw, se = [np.asarray(arrays[k][rows, :], np.float32) for k in ('raw','se')]
    ok = np.isfinite(raw)
    # Match finite_mean(raw) -> float32 centre in frozen truth_arrays exactly.
    centre = np.divide(np.where(ok,raw,0).sum(0), ok.sum(0),
                       out=np.zeros(raw.shape[1]), where=ok.sum(0)>0).astype(np.float32)
    raw -= centre
    common = (np.isfinite(raw) & np.isfinite(se) & (se > 0) & finite).all(0)
    if common.sum() < 10:
        raise ValueError(f'{context}: fewer than ten common measured genes')
    pair = {arm: losses(x[:, common], raw[:, common]) for arm,x in pred.items()}
    reported = pd.read_csv(run/'per_target.csv', keep_default_na=False)
    for arm in pair:
        r = reported[(reported.context == context) & (reported.arm == arm)].set_index('target').loc[expected]
        if not (r.common_genes == common.sum()).all() or not np.allclose(r['rank'], pds(pair[arm]), atol=1e-12, rtol=0):
            raise ValueError(f'{context}/{arm}: reconstruction differs from original metric/mask')
    return expected.tolist(), pair, {'prediction_sha256': digest(path), 'common_genes': int(common.sum()),
                                    'targets': len(rows), 'original_rank_reproduced': True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runs', type=Path, nargs='+', required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    guard = verify(args.runs)  # Completeness/provenance gate before any effect read.
    manifests = [json.loads((run/'manifest.json').read_text()) for run in args.runs]
    first = manifests[0]
    repo = LEAD.parents[2]
    for name, sha in canonical_code(first['code_hashes']).items():
        path = repo/'reports/modelli/rete_contesti_2026-09-27/pool.py' if name == 'pool.py' else LEAD/name
        if digest(path) != sha:
            raise ValueError(f'Frozen local code differs: {name}')
    for name, record in first['data_files'].items():
        path = args.data/name
        if not path.is_file() or path.stat().st_size != record['bytes'] or (record['sha256'] and digest(path) != record['sha256']):
            raise ValueError(f'Data provenance differs: {name}')
    names = pd.read_csv(args.data/'targets.csv', keep_default_na=False).target.to_numpy(str)
    response = pd.read_csv(args.data/'genes.csv', keep_default_na=False)
    official = pd.read_csv(args.data/'axis.csv', keep_default_na=False).gene.to_numpy(str)
    arrays = {k: np.load(args.data/f'{k}.npy', mmap_mode='r') for k in ('raw','se','row_target')}
    targets, matrices, families, evidence = {}, {}, {}, {}
    for run,m in zip(args.runs,manifests):
        for ci, rows in m['design']['test'].items():
            context = m['context_names'][int(ci)]
            targets[context], matrices[context], evidence[context] = load_context(
                run,m,context,rows,args.data,(names,response,official),arrays)
            families[context] = m['options']['holdout']
    union, weights = cluster_counts(targets)
    context_count = Counter(families.values())
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'not_vcc_score': True,
              'claim_type': 'additive sensitivity diagnostic; frozen promotion rule unchanged',
              'bootstrap': {'draws':2000, 'seed':20260929, 'unit':'same target across all contexts/families',
                            'conditional':'fixed learned predictions, measured gene support and original truth centring; these five observed families'},
              'unique_targets':len(union), 'target_occurrences':sum(map(len,targets.values())),
              'targets_in_multiple_contexts':sum(v>1 for v in Counter(t for ts in targets.values() for t in ts).values()),
              'target_overlap_by_context':{c:{d:len(set(ts)&set(targets[d])) for d in targets} for c,ts in targets.items()},
              'contexts':evidence, 'contrasts':{}, 'provenance_guard':guard,
              'code_sha256':digest(Path(__file__)), 'large_arrays_rehashed':False}
    all_draws = {}
    for reference in ('transfer','blind'):
        recalculated, rank_only = np.zeros(2000), np.zeros(2000)
        point, per_context = 0., {}
        for c, pair in matrices.items():
            scale = 1/(len(context_count)*context_count[families[c]])
            w = weights[c]
            delta = pds(pair['net'])-pds(pair[reference])
            actual = float(delta.mean())
            point += scale*actual
            per_context[c] = actual
            recalculated += scale*resampled_delta(pair['net'],pair[reference],w)
            rank_only += scale*(w@delta)/w.sum(1)
        result['contrasts'][reference] = {'macro_family_delta':point,'per_context':per_context,
                                         'cluster_recalculated_pds_ci95':np.quantile(recalculated,[.025,.975]).tolist(),
                                         'cluster_fixed_rank_ci95':np.quantile(rank_only,[.025,.975]).tolist()}
        all_draws[f'net_minus_{reference}_pds'] = recalculated
        all_draws[f'net_minus_{reference}_fixed_rank'] = rank_only
    args.out.mkdir(parents=True)
    (args.out/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    pd.DataFrame(all_draws).to_csv(args.out/'bootstrap_draws.csv',index=False)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
