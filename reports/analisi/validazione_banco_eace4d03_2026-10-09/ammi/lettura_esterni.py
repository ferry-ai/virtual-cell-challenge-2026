"""Level-A read of external arms on one C fold with the frozen bench, plus coverage and the generator's view.

For a fold whose manifest arms (T0, R1, T1, P4) already exist as files, this measures any number of external arms
delivered in the stage-100 format (an anchor, a model export) with `bench_core.measure` of the frozen bench,
unchanged: the manifest arms alone define the targets compared and the genes of the rank. It then adds, for every
declared pair of arms, what contract v3 asks when masks may differ: how many pairs each arm predicts, how many
change, how many the truth can judge and the rank contains, and the same measures on the truth-defined support
with an unpredicted pair read as zero. Parity with a published run is checked before anything is reported.

    py lettura_esterni.py --spec spec.json --out out.json [--bench-dir <dir with metrics.py and bench_core.py>]

Effect-space proxies on a development lineage: not VCC scores, no promotion rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FROZEN_BENCH = HERE.parents[1] / 'validazione_indipendente_8a8ca58a_2026-10-08' / 'banco'
PINNED = {'metrics.py': 'e4bbc08859b3fd2ff0628cf255cd53f8db21507effb78e39fc38d618900567ec',
          'bench_core.py': 'ffbc0dbabb5a4301e03a455ccbf6c5495e95f03c149ff25e0100551c190c95ee'}
ARMS = ('T0', 'R1', 'T1', 'P4')
PARITY_TOL = 1e-6
VIEW_MEASURES = ('disc95g', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')


def sha(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for block in iter(lambda: fh.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_bench(bench_dir=None):
    folder = Path(bench_dir or FROZEN_BENCH)
    for name, want in PINNED.items():
        if sha(folder / name) != want:
            raise SystemExit('%s is not the frozen file of the bench' % name)
    sys.path.insert(0, str(folder))
    import bench_core
    import metrics
    return metrics, bench_core


def checked(entry) -> Path:
    path = Path(entry['path'])
    if sha(path) != entry['sha256']:
        raise SystemExit('pinned input differs: ' + str(path))
    return path


def load_effects(path):
    with np.load(path, allow_pickle=False) as z:
        return ([str(t) for t in z['targets']], [str(g) for g in z['genes']], z['lfc'].astype(np.float32),
                z['observed'].astype(bool))


def read_fold(spec: dict, M, core) -> dict:
    fold, tname = spec['fold'], spec['truth_table']
    extras = list(spec['extra'])
    labels, panel, axis = {}, None, None
    for name in (*ARMS, *extras):
        entry = spec['arms'][name] if name in ARMS else spec['extra'][name]
        targets, genes, lfc, obs = load_effects(checked(entry))
        if panel is None:
            panel, axis = targets, genes
        if targets != panel or genes != axis:
            raise SystemExit('axes differ in ' + name)
        labels[name] = (lfc, obs)
    with np.load(checked(spec['truth']), allow_pickle=False) as z:
        table = {'targets': [str(t) for t in z['targets']], 'shrunk': z['shrunk'], 'raw': z['raw'], 'se': z['se'],
                 'n_cells': z['n_cells']}
    published = json.loads(checked(spec['published_results']).read_text(encoding='utf-8'))['folds'][fold]['truth'][tname]
    pairs = [tuple(p) for p in spec['pairs']]
    contrasts = [('X_%s_minus_%s' % (a, b), a, b) for a, b in pairs]
    contrasts += [('X_shuffle_%s' % x, x, x + '~shuffle') for x in extras]
    effects = {(a, fold): labels[a] for a in labels}
    for stand_in in ('T0~gamma0', 'T0~nocis'):                    # needed by the derived controls, not read here
        effects[(stand_in, fold)] = labels['T0']
    folds = {fold: {'lineage': spec.get('lineage', fold), 'truth': [{'table': tname, 'role': 'primary'}]}}
    results, _, _, _ = core.measure(folds, list(ARMS), effects, {tname: table}.__getitem__, panel, axis,
                                    log=lambda *_: None, extra_arms=extras, extra_contrasts=contrasts)
    block = results[fold]['truth'][tname]
    parity = {'T0_disc95': {'recomputed': block['arms']['T0']['disc95'], 'published': published['arms']['T0']['disc95']},
              'targets_equal': block['targets'] == published['targets'],
              'genes_for_rank_equal': (block['genes_for_rank_strict'], block['genes_for_rank_95']) ==
                                      (published['genes_for_rank_strict'], published['genes_for_rank_95'])}
    parity['passed'] = bool(parity['targets_equal'] and parity['genes_for_rank_equal'] and abs(
        parity['T0_disc95']['recomputed'] - parity['T0_disc95']['published']) < PARITY_TOL)
    doc = {'schema': 'lettura-esterni/1', 'fold': fold, 'truth': tname, 'not_vcc_scores': True,
           'development_lineage': True, 'numpy': np.__version__, 'parity': parity}
    if not parity['passed']:
        doc['stopped'] = 'parity with the published run failed: nothing is read'
        return doc
    keep_stats = ('disc95', 'disc', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio', 'common_share_pred',
                  'amplitude_star', 'rms_pred', 'targets', 'targets_with_a_prediction', 'median_n_valid', 'median_n_conf')
    doc['frozen_bench'] = {
        'targets': block['targets'], 'genes_for_rank_95': block['genes_for_rank_95'],
        'arms': {a: {k: block['arms'][a].get(k) for k in keep_stats} for a in ('T0', *extras)},
        'contrasts': {cid: {'first': c['first'], 'second': c['second'], 'targets_changed': c['targets_changed'],
                            'measures': {m: v['all'] | {'higher_is_better': v['higher_is_better']} for m, v in c['measures'].items()}}
                      for cid, c in block['contrasts'].items() if cid.startswith('X_')}}

    # coverage and the generator's view, on the rows and genes the frozen bench used
    axis_pos = {g: i for i, g in enumerate(axis)}
    exclude = sorted(axis_pos[t] for t in panel if t in axis_pos)
    pos = {t: j for j, t in enumerate(table['targets'])}
    keep = [i for i, t in enumerate(panel) if t in pos and all(labels[a][1][i].any() for a in ARMS)]
    trow = np.array([pos[panel[i]] for i in keep])
    shrunk, raw, se = table['shrunk'][trow], table['raw'][trow], table['se'][trow]
    valid = {a: M.valid_pairs(labels[a][1][keep], shrunk, raw, se, exclude) for a in ARMS}
    cols95 = np.mean([valid[a] for a in ARMS], axis=0).mean(axis=0) >= 0.95
    truth_ok = M.valid_pairs(np.ones(shrunk.shape, bool), shrunk, raw, se, exclude)
    cols95g = truth_ok.mean(axis=0) >= 0.95
    one_truth = np.where(truth_ok, np.nan_to_num(shrunk.astype(np.float64)), 0.0)
    coverage = {}
    for a, b in pairs:
        (la, oa), (lb, ob) = (labels[a][0][keep], labels[a][1][keep]), (labels[b][0][keep], labels[b][1][keep])
        both, only_a, only_b = oa & ob, oa & ~ob, ob & ~oa
        changed = (both & (la != lb)) | only_a | only_b
        judged = changed & truth_ok
        coverage['%s-%s' % (a, b)] = {
            'pairs_predicted': {a: int(oa.sum()), b: int(ob.sum())}, 'same_mask': bool(np.array_equal(oa, ob)),
            'predicted_only_by_first': int(only_a.sum()), 'predicted_only_by_second': int(only_b.sum()),
            'predicted_by_both_with_different_values': int((both & (la != lb)).sum()),
            'changed_pairs': int(changed.sum()), 'changed_and_judgeable': int(judged.sum()),
            'changed_judgeable_in_rank_95': int((judged & cols95[None, :]).sum()),
            'measure_covers_the_change': bool((judged & cols95[None, :]).sum() >= 0.5 * judged.sum())}
    shuffle_panel = M.shuffled_rows(len(panel))
    view_arms = {name: labels[name][0] for name in ('T0', *extras)}
    view_arms.update({name + '~shuffle': labels[name][0][shuffle_panel] for name in ('T0', *extras)})
    per = {}
    for name, lfc in view_arms.items():
        lfc_keep = np.where(truth_ok, lfc[keep], 0.0)
        per[name] = M.per_target(lfc_keep, truth_ok, shrunk, raw, se, cols95g)
        per[name]['disc95g'] = M.per_target(lfc_keep, truth_ok, one_truth, raw, se, cols95g)['disc']
    with np.errstate(all='ignore'):
        levels = {a: {m: float(np.nanmean(per[a][m])) for m in VIEW_MEASURES} for a in view_arms}
    wanted = [*pairs, *[(name, name + '~shuffle') for name in ('T0', *extras)]]
    doc['coverage'] = coverage
    doc['generator_view'] = {
        'genes_for_rank_95g': int(cols95g.sum()), 'pairs_in_support': int(truth_ok.sum()), 'levels': levels,
        'contrasts': {'%s-%s' % (a, b): {m: {**M.strip(M.paired_bootstrap(per[a][m], per[b][m])),
                                             'higher_is_better': M.HIGHER_IS_BETTER.get(m, True)} for m in VIEW_MEASURES}
                      for a, b in wanted}}
    control = doc['generator_view']['contrasts']['T0-T0~shuffle']['disc95g']
    doc['generator_view']['disc95g_control_passed'] = bool(control['resolved'] and control['mean'] > 0)
    return doc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--spec', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--bench-dir')
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding='utf-8'))
    M, core = load_bench(args.bench_dir)
    doc = read_fold(spec, M, core)
    doc['spec_sha256'], doc['code_sha256'] = sha(args.spec), sha(__file__)
    with Path(args.out).open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, default=float)
        fh.write('\n')
    print(json.dumps({'fold': doc['fold'], 'parity': doc['parity'], 'stopped': doc.get('stopped')}, default=float))


if __name__ == '__main__':
    main()
