"""Measures, contrasts and audits of the leave-one-lineage-out bench, free of any runtime path.

`measure` takes, for every (arm, fold), the effects stage 100 wrote, and for every fold the truth tables of
the held lineage; it returns the per-target rows, the per-fold contrasts with a paired bootstrap over
targets, the macro over folds and the shuffle control. `table_audit` and `vote_audit` describe duplicated
experiments and votes per lineage. The cloud driver and the local tests call the same functions.
"""
from __future__ import annotations

import numpy as np

import metrics as M

# (id, first, second): the difference first - second is reported. K* are the contrasts of the contract,
# c_* its controls. A label "ARM~name" is a variant or a derived control of ARM.
CONTRASTS = [('K0', 'T0', 'P4'), ('K1', 'T1', 'T0'), ('K1r1', 'R1', 'T0'), ('c_shuffle', 'T0', 'T0~shuffle'),
             ('c_meanonly', 'T0', 'T0~meanonly'), ('c_null', 'T0', 'T0~null'), ('c_gamma0', 'T0', 'T0~gamma0'),
             ('c_nocis', 'T0', 'T0~nocis'), ('c_shuffle_T1', 'T1', 'T1~shuffle')]
REPORTED = (*M.MEASURES, 'disc95')
CSV_HEADER = ['fold', 'truth', 'arm', 'target', 'truth_cells', *REPORTED, 'n_valid', 'n_conf']


def derived_controls(labels: dict, n: int) -> dict:
    """The controls that need no stage-100 run: other targets' predictions, the arm's mean for every target,
    and no prediction at all."""
    perm = M.shuffled_rows(n)
    out = dict(labels)
    for base in ('T0', 'T1'):
        lfc, obs = labels[base]
        out[base + '~shuffle'] = (lfc[perm], obs[perm])
    lfc, obs = labels['T0']
    seen = obs.any(axis=0)
    mean = np.where(seen, np.where(obs, lfc, 0.0).sum(axis=0) / np.maximum(obs.sum(axis=0), 1), 0.0)
    out['T0~meanonly'] = (np.repeat(mean[None, :].astype(np.float32), n, axis=0), np.repeat(seen[None, :], n, axis=0))
    out['T0~null'] = (np.zeros_like(lfc), obs.copy())
    return out


def measure(folds: dict, arms: list, effects: dict, load_truth, panel: list, axis: list, log=print,
            extra_arms=(), extra_contrasts=()):
    """``effects[(label, fold id)]`` is (lfc [panel, axis], observed); ``load_truth(table name)`` returns a dict
    with targets, shrunk, raw, se, n_cells. Returns (results, macro, shuffle, csv rows).

    ``arms`` are the arms of the manifest: they alone define the targets compared and the genes of the rank, so
    that adding an arm never moves a number of the others. ``extra_arms`` (analysis or external arms) are
    measured on the same targets and genes where their effects exist for the fold; ``extra_contrasts`` are
    (id, first, second) triples added to CONTRASTS, skipped on a fold that lacks one of the two labels.

    A fold may carry three options, used by the J regime: ``only_targets`` (evaluate these symbols only),
    ``require_prediction`` False (a target no arm predicts stays in, read as a null prediction) and
    ``rank_genes_from`` 'truth' (the genes of the discrimination rank come from the truth alone, one truth for
    every arm, a pair an arm does not predict counting zero)."""
    plan = [*CONTRASTS, *[tuple(c) for c in extra_contrasts]]
    axis_pos = {g: i for i, g in enumerate(axis)}
    exclude_cols = sorted(axis_pos[t] for t in panel if t in axis_pos)
    own_all = np.array([axis_pos.get(t, -1) for t in panel])
    rows_csv, results, boots = [], {}, {}
    for fid, fold in folds.items():
        results[fid] = {'lineage': fold['lineage'], 'truth': {}}
        present = [a for a in extra_arms if (a, fid) in effects]
        labels = derived_controls({a: effects[(a, fid)] for a in [*arms, *present, 'T0~gamma0', 'T0~nocis']},
                                  len(panel))
        for truth_spec in fold['truth']:
            tname = truth_spec['table']
            table = load_truth(tname)
            pos = {t: j for j, t in enumerate(table['targets'])}
            only = set(fold['only_targets']) if fold.get('only_targets') is not None else None
            need = fold.get('require_prediction', True)
            keep = [i for i, t in enumerate(panel) if t in pos and (only is None or t in only)
                    and (not need or all(labels[a][1][i].any() for a in arms))]
            if len(keep) < 3:
                results[fid]['truth'][tname] = {'role': truth_spec['role'], 'targets': len(keep), 'skipped': True}
                continue
            trow = np.array([pos[panel[i]] for i in keep])
            shrunk, raw, se = table['shrunk'][trow], table['raw'][trow], table['se'][trow]
            valid = {a: M.valid_pairs(labels[a][1][keep], shrunk, raw, se, exclude_cols) for a in labels}
            from_truth = fold.get('rank_genes_from') == 'truth'
            if from_truth:
                truth_ok = M.valid_pairs(np.ones(shrunk.shape, bool), shrunk, raw, se, exclude_cols)
                one_truth = np.where(truth_ok, np.nan_to_num(shrunk.astype(np.float64)), 0.0)
                cols, cols95 = truth_ok.all(axis=0), truth_ok.mean(axis=0) >= 0.95
            else:
                cols = np.logical_and.reduce([valid[a].all(axis=0) for a in arms])
                cols95 = np.mean([valid[a] for a in arms], axis=0).mean(axis=0) >= 0.95
            per, summary = {}, {}
            for a, (lfc, obs) in labels.items():
                per[a] = M.per_target(lfc[keep], valid[a], shrunk, raw, se, cols)
                if from_truth:
                    masked = np.where(valid[a], lfc[keep], 0.0)
                    per[a]['disc'] = M.per_target(masked, valid[a], one_truth, raw, se, cols)['disc']
                    per[a]['disc95'] = M.per_target(masked, valid[a], one_truth, raw, se, cols95)['disc']
                else:
                    loose = M.per_target(np.where(valid[a], lfc[keep], 0.0), valid[a],
                                         np.where(valid[a], shrunk, 0.0), raw, se, cols95)
                    per[a]['disc95'] = loose['disc']
                summary_predicted = int(labels[a][1][keep].any(axis=1).sum())
                summary[a] = M.arm_summary(lfc[keep], valid[a], raw, cols, own_all[keep], obs[keep])
                with np.errstate(all='ignore'):
                    summary[a].update({m: float(np.nanmean(per[a][m])) for m in REPORTED})
                summary[a].update(targets=len(keep), targets_with_a_prediction=summary_predicted,
                                  median_n_conf=float(np.median(per[a]['n_conf'])),
                                  median_n_valid=float(np.median(per[a]['n_valid'])))
                for k, i in enumerate(keep):
                    rows_csv.append([fid, tname, a, panel[i], int(table['n_cells'][trow[k]])]
                                    + [float(per[a][m][k]) for m in (*REPORTED, 'n_valid', 'n_conf')])
            contrasts = {}
            for cid, first, second in plan:
                if first not in labels or second not in labels:
                    continue
                changed = np.abs(labels[first][0][keep] - labels[second][0][keep]).max(axis=1) > 0
                entry = {'first': first, 'second': second, 'targets': len(keep), 'targets_changed': int(changed.sum()),
                         'changed': [panel[keep[k]] for k in np.flatnonzero(changed)] if changed.sum() <= 40 else None,
                         'measures': {}}
                for m in REPORTED:
                    full = M.paired_bootstrap(per[first][m], per[second][m])
                    sub = (M.paired_bootstrap(per[first][m][changed], per[second][m][changed])
                           if changed.sum() >= 2 else None)
                    entry['measures'][m] = {'all': M.strip(full), 'changed_only': M.strip(sub) if sub else None,
                                            'higher_is_better': M.HIGHER_IS_BETTER.get(m, True)}
                    if truth_spec['role'] == 'primary':
                        boots[(cid, m, fid)] = full
                contrasts[cid] = entry
            results[fid]['truth'][tname] = {'role': truth_spec['role'], 'targets': len(keep),
                                            'genes_for_rank_strict': int(cols.sum()),
                                            'genes_for_rank_95': int(cols95.sum()), 'arms': summary,
                                            'contrasts': contrasts}
            log('%s %s: %d targets, %d genes shared by all' % (fid, tname, len(keep), int(cols.sum())))
    macro = {}
    for cid, first, second in plan:
        macro[cid] = {'first': first, 'second': second,
                      'folds_with_the_contrast': [fid for fid in folds if (cid, REPORTED[0], fid) in boots],
                      'measures': {m: M.macro([boots[(cid, m, fid)] for fid in folds if (cid, m, fid) in boots])
                                   for m in REPORTED}}
    shuffle = {}
    for fid, fold in folds.items():
        primary = next(t['table'] for t in fold['truth'] if t['role'] == 'primary')
        block = results[fid]['truth'][primary]
        if block.get('skipped'):
            continue
        shuffle[fid] = {'T0_disc': block['arms']['T0']['disc'], 'shuffle_disc': block['arms']['T0~shuffle']['disc'],
                        'difference': block['contrasts']['c_shuffle']['measures']['disc']['all']}
    return results, macro, shuffle, rows_csv


def table_audit(tables: dict, exclude: np.ndarray) -> list:
    """Duplicated experiments and pseudo-replicates: for every pair of tables with at least three shared
    targets, the cosine of their shrunk effects on jointly measured genes, per shared target, as it is and
    after removing each table's mean over the shared targets. ``exclude`` masks the targets' own genes."""
    names = sorted(n for n, t in tables.items() if len(t['targets']) > 0)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ta, tb = tables[a], tables[b]
            pos_b = {t: j for j, t in enumerate(tb['targets'])}
            shared = [(k, pos_b[t]) for k, t in enumerate(ta['targets']) if t in pos_b]
            if len(shared) < 3:
                continue
            A = ta['shrunk'][[k for k, _ in shared]].astype(np.float64)
            B = tb['shrunk'][[j for _, j in shared]].astype(np.float64)
            ok = np.isfinite(A) & np.isfinite(B)
            ok[:, exclude] = False

            def cosines(X, Y):
                X, Y = np.where(ok, X, 0.0), np.where(ok, Y, 0.0)
                den = np.linalg.norm(X, axis=1) * np.linalg.norm(Y, axis=1)
                return (X * Y).sum(axis=1) / np.maximum(den, 1e-12)

            with np.errstate(all='ignore'):
                Ac = np.nan_to_num(A - np.nanmean(np.where(ok, A, np.nan), axis=0))
                Bc = np.nan_to_num(B - np.nanmean(np.where(ok, B, np.nan), axis=0))
            raw_cos, spec_cos = cosines(np.nan_to_num(A), np.nan_to_num(B)), cosines(Ac, Bc)
            out.append({'a': a, 'b': b, 'shared_targets': len(shared),
                        'genes_shared_by_all': int(ok.all(axis=0).sum()),
                        'cosine_median': float(np.median(raw_cos)),
                        'cosine_specific_median': float(np.median(spec_cos)),
                        'cosine_p10': float(np.quantile(raw_cos, 0.1)), 'cosine_p90': float(np.quantile(raw_cos, 0.9))})
    return out


def vote_audit(manifest: dict, targets_of: dict, panel: list) -> dict:
    """Votes per panel target by lineage, for every arm: a lineage voting twice is not two lineages."""
    lineage_of = {t: name for name, lin in manifest['lineages'].items() for t in lin['tables']}
    out = {}
    for arm, spec in manifest['arms'].items():
        sets = {s: set(targets_of[s]) for s in spec['sources']}
        votes, lineages, repeated_by = [], [], {}
        repeated = 0
        for target in panel:
            by = {}
            for source in spec['sources']:
                if target in sets[source]:
                    by.setdefault(lineage_of[source], []).append(source)
            votes.append(sum(len(v) for v in by.values()))
            lineages.append(len(by))
            twice = [lin for lin, v in by.items() if len(v) > 1]
            repeated += bool(twice)
            for lin in twice:
                repeated_by[lin] = repeated_by.get(lin, 0) + 1
        out[arm] = {'votes_histogram': {str(k): votes.count(k) for k in sorted(set(votes))},
                    'lineages_histogram': {str(k): lineages.count(k) for k in sorted(set(lineages))},
                    'targets_with_a_lineage_voting_more_than_once': repeated,
                    'repeated_votes_by_lineage': repeated_by,
                    'votes_total': int(sum(votes)), 'lineage_votes_total': int(sum(lineages))}
    return out
