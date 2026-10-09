"""Support audit of a fallback arm on one C fold (contract v3, sections 1 and 2). No training, no stage 100.

A fallback arm keeps the transfer where the transfer predicts and fills the other target-gene pairs with an
external model. The level-A bench judges every arm on its own predicted pairs, and ranks on genes chosen from
the manifest arms alone: this script says how many filled pairs each measure actually sees, and compares, with
identical masks and scale, four ways of treating the filled pairs:

    zero       the transfer as the generator emits it (an unpredicted pair is an effect of zero)
    esm2       the delivered fallback
    generic    the same pairs filled with the external model's target-independent part
    swapped    the same pairs filled with the external model's prediction for another target

It first reproduces the published disc95 of the transfer and of the fallback (parity) and checks that the
fallback is the transfer where the transfer predicts and amplitude x external elsewhere (adapter); if either
fails it stops before any diagnostic is read. Every input is verified by sha256 against the spec.

    py supporto_fallback.py --spec spec.json --out out.json [--bench-dir <dir holding the frozen metrics.py>]

Effect-space proxies on a development lineage: not VCC scores, not a promotion rule (the rule is section 8 of
contract v1, six members on at least two folds).
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
METRICS_SHA256 = 'e4bbc08859b3fd2ff0628cf255cd53f8db21507effb78e39fc38d618900567ec'
ARMS = ('T0', 'R1', 'T1', 'P4')              # the arms of the frozen manifest: they alone define targets and rank genes
VIEW = ('zero', 'esm2', 'generic', 'swapped')
MIN_FILLED = 20                              # a target is read on its filled pairs only with at least this many
MIN_CONF = 5
PARITY_TOL = 1e-6
ADAPTER_TOL = 1e-6


def sha(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for block in iter(lambda: fh.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_metrics(bench_dir=None, pinned=True):
    path = Path(bench_dir or FROZEN_BENCH) / 'metrics.py'
    if pinned and sha(path) != METRICS_SHA256:
        raise SystemExit('metrics.py is not the frozen file of the bench: ' + str(path))
    sys.path.insert(0, str(path.parent))
    import metrics
    return metrics


def checked(entry) -> Path:
    path = Path(entry['path'])
    got = sha(path)
    if got != entry['sha256']:
        raise SystemExit('pinned input differs: %s (%s)' % (path, got))
    return path


def load_effects(path):
    with np.load(path, allow_pickle=False) as z:
        return ([str(t) for t in z['targets']], [str(g) for g in z['genes']], z['lfc'].astype(np.float32),
                z['observed'].astype(bool))


def quantiles(values) -> dict:
    v = np.asarray(values, float)
    if v.size == 0:
        return {'n': 0}
    return {'n': int(v.size), 'min': float(v.min()), 'median': float(np.median(v)), 'mean': float(v.mean()),
            'max': float(v.max())}


def filled_only(M, pred, judged, shrunk, raw, se):
    """Per target, on the filled pairs the truth can judge: squared and absolute error relative to predicting
    zero (1.0 is the zero prediction), and sign agreement on the truth's confident genes."""
    n = pred.shape[0]
    out = {k: np.full(n, np.nan) for k in ('mse_vs_zero', 'nmae_conf_vs_zero', 'sign_conf', 'cos', 'amp_star')}
    out['n_filled'] = judged.sum(axis=1).astype(float)
    out['n_conf'] = np.zeros(n)
    with np.errstate(all='ignore'):
        Z = raw.astype(np.float64) / se.astype(np.float64)
    for i in range(n):
        v = judged[i]
        if v.sum() < MIN_FILLED:
            continue
        p, r, o, z = pred[i, v].astype(np.float64), raw[i, v].astype(np.float64), shrunk[i, v], Z[i, v]
        den = float((r * r).sum())
        if den > 0:
            out['mse_vs_zero'][i] = float(((p - r) ** 2).sum() / den)
        pp = float((p * p).sum())
        if pp > 0 and den > 0:                 # amplitude-free agreement, and the multiplier that would fit the truth
            out['cos'][i] = float((p * r).sum() / np.sqrt(pp * den))
            out['amp_star'][i] = float((p * r).sum() / pp)
        conf = np.abs(z) >= M.Z_CONF
        out['n_conf'][i] = float(conf.sum())
        if conf.sum() < MIN_CONF:
            continue
        den = float(np.abs(r[conf]).sum())
        if den > 0:
            out['nmae_conf_vs_zero'][i] = float(np.abs(p[conf] - r[conf]).sum() / den)
        out['sign_conf'][i] = float(np.mean(np.sign(p[conf]) == np.sign(o[conf])))
    return out


def sign_and_coverage(M, pred, predicted, truth_ok, shrunk, raw, se):
    """Per target, on the truth's confident genes: the share the arm predicts at all (coverage), the sign
    agreement among the predicted ones (accuracy), and the agreement over all of them with an unpredicted gene
    counted as a miss (what a sign measure reads when it treats zero as a wrong sign)."""
    n = pred.shape[0]
    out = {k: np.full(n, np.nan) for k in ('coverage_conf', 'sign_predicted', 'sign_all')}
    with np.errstate(all='ignore'):
        Z = raw.astype(np.float64) / se.astype(np.float64)
    for i in range(n):
        conf = truth_ok[i] & (np.abs(Z[i]) >= M.Z_CONF)
        if conf.sum() < MIN_CONF:
            continue
        got = conf & predicted[i]
        agree = np.sign(pred[i]) == np.sign(shrunk[i])
        out['coverage_conf'][i] = float(got.sum() / conf.sum())
        out['sign_all'][i] = float((agree & got).sum() / conf.sum())
        if got.sum() >= MIN_CONF:
            out['sign_predicted'][i] = float(agree[got].mean())
    return out


def against(M, values, null) -> dict:
    """Mean of values - null over the targets where the value exists, with the bench's bootstrap."""
    v = np.asarray(values, float)
    return M.strip(M.paired_bootstrap(v, np.full(v.shape, float(null))))


def audit(spec: dict, M) -> dict:
    amplitude = float(spec['amplitude'])
    fold, tname = spec['fold'], spec['truth_table']
    labels = {}
    panel = axis = None
    for name in (*ARMS, 'fallback', 'E2', 'E2g'):
        entry = spec['arms'][name] if name in ARMS else spec[name]
        targets, genes, lfc, obs = load_effects(checked(entry))
        if panel is None:
            panel, axis = targets, genes
        if targets != panel or genes != axis:
            raise SystemExit('axes differ in ' + name)
        labels[name] = (lfc, obs)
    with np.load(checked(spec['truth']), allow_pickle=False) as z:
        t_targets = [str(t) for t in z['targets']]
        t_shrunk, t_raw, t_se = z['shrunk'], z['raw'], z['se']
    results = json.loads(checked(spec['closure_results']).read_text(encoding='utf-8'))
    block = results['folds'][fold]['truth'][tname]

    axis_pos = {g: i for i, g in enumerate(axis)}
    exclude = sorted(axis_pos[t] for t in panel if t in axis_pos)
    pos = {t: j for j, t in enumerate(t_targets)}
    keep = [i for i, t in enumerate(panel) if t in pos and all(labels[a][1][i].any() for a in ARMS)]
    trow = np.array([pos[panel[i]] for i in keep])
    shrunk, raw, se = t_shrunk[trow], t_raw[trow], t_se[trow]
    valid = {a: M.valid_pairs(labels[a][1][keep], shrunk, raw, se, exclude) for a in (*ARMS, 'fallback')}
    cols = np.logical_and.reduce([valid[a].all(axis=0) for a in ARMS])
    cols95 = np.mean([valid[a] for a in ARMS], axis=0).mean(axis=0) >= 0.95

    def disc95_as_run(name):
        lfc = labels[name][0][keep]
        return M.per_target(np.where(valid[name], lfc, 0.0), valid[name], np.where(valid[name], shrunk, 0.0), raw, se,
                            cols95)['disc']

    # 1. parity with the published closure run
    as_run = {'T0': disc95_as_run('T0'), 'fallback': disc95_as_run('fallback')}
    published = {'T0': block['arms']['T0']['disc95'], 'fallback': block['arms'][spec.get('fallback_label', 'E2f')]['disc95']}
    parity = {k: {'recomputed': float(as_run[k].mean()), 'published': published[k],
                  'abs_difference': abs(float(as_run[k].mean()) - published[k])} for k in as_run}
    parity['targets_equal'] = len(keep) == block['targets']
    parity['genes_for_rank_equal'] = (int(cols.sum()), int(cols95.sum())) == (
        block['genes_for_rank_strict'], block['genes_for_rank_95'])
    parity['passed'] = bool(parity['targets_equal'] and parity['genes_for_rank_equal']
                            and all(parity[k]['abs_difference'] < PARITY_TOL for k in as_run))
    doc = {'schema': 'supporto-fallback/2', 'fold': fold, 'truth': tname, 'contract': 'PROTOCOLLO_v3 sections 1-2',
           'not_vcc_scores': True, 'development_lineage': True, 'numpy': np.__version__, 'parity': parity}
    if not parity['passed']:
        doc['stopped'] = 'parity failed: no diagnostic is read'
        return doc

    # 2. adapter: the fallback is the transfer where the transfer predicts, amplitude x E2 where it fills
    (lfc_t0, obs_t0), (lfc_f, obs_f) = labels['T0'], labels['fallback']
    (lfc_e2, obs_e2), (lfc_g, obs_g) = labels['E2'], labels['E2g']
    fill_all = obs_f & ~obs_t0
    expected = (lfc_e2.astype(np.float64) * amplitude).astype(np.float32)
    adapter = {'transfer_pairs_dropped_by_fallback': int((obs_t0 & ~obs_f).sum()),
               'transfer_values_identical': bool(np.array_equal(lfc_f[obs_t0], lfc_t0[obs_t0])),
               'filled_pairs_panel': int(fill_all.sum()),
               'filled_pairs_expected': spec.get('expected_filled_pairs'),
               'filled_pairs_without_E2': int((fill_all & ~obs_e2).sum()),
               'max_abs_difference_from_amplitude_x_E2': float(np.abs(lfc_f[fill_all] - expected[fill_all]).max())
               if fill_all.any() else 0.0,
               'unpredicted_pairs_nonzero': int((lfc_f[~obs_f] != 0).sum() + (lfc_t0[~obs_t0] != 0).sum())}
    adapter['passed'] = bool(adapter['transfer_pairs_dropped_by_fallback'] == 0 and adapter['transfer_values_identical']
                             and adapter['filled_pairs_without_E2'] == 0
                             and adapter['max_abs_difference_from_amplitude_x_E2'] <= ADAPTER_TOL
                             and adapter['unpredicted_pairs_nonzero'] == 0
                             and (adapter['filled_pairs_expected'] in (None, adapter['filled_pairs_panel'])))
    doc['adapter'] = adapter
    if not adapter['passed']:
        doc['stopped'] = 'adapter check failed: no diagnostic is read'
        return doc

    # 3. support counts: coverage apart from accuracy
    truth_ok = M.valid_pairs(np.ones(shrunk.shape, bool), shrunk, raw, se, exclude)
    panel_cols = np.zeros(len(axis), bool)
    panel_cols[exclude] = True
    fill = fill_all[keep]
    judged = fill & truth_ok
    in_rank = judged & cols95[None, :]
    rank_entries = len(keep) * int(cols95.sum())
    f64 = lfc_f[keep].astype(np.float64)
    with np.errstate(all='ignore'):
        energy_share = (np.where(in_rank, f64, 0.0) ** 2).sum(axis=1) / np.maximum(
            (np.where(valid['fallback'] & cols95[None, :], f64, 0.0) ** 2).sum(axis=1), 1e-300)
    doc['support'] = {
        'targets_panel': len(panel), 'targets_compared': len(keep), 'genes_axis': len(axis),
        'genes_for_rank_strict': int(cols.sum()), 'genes_for_rank_95': int(cols95.sum()),
        'rank_entries': rank_entries,
        'pairs_predicted': {'T0': int(obs_t0[keep].sum()), 'fallback': int(obs_f[keep].sum())},
        'pairs_judgeable_by_truth': {'T0': int(valid['T0'].sum()), 'fallback': int(valid['fallback'].sum()),
                                     'truth_valid_any_arm': int(truth_ok.sum())},
        'pairs_in_rank': {'T0': int((valid['T0'] & cols95[None, :]).sum()),
                          'fallback': int((valid['fallback'] & cols95[None, :]).sum())},
        'filled': {
            'panel_rows': int(fill_all.sum()),
            'in_targets_not_compared': int(fill_all.sum() - fill.sum()),
            'in_targets_compared': int(fill.sum()),
            'not_judgeable_panel_gene_column': int((fill & panel_cols[None, :]).sum()),
            'not_judgeable_truth_unmeasured': int((fill & ~truth_ok & ~panel_cols[None, :]).sum()),
            'judgeable': int(judged.sum()),
            'judgeable_in_rank_95': int(in_rank.sum()),
            'judgeable_outside_rank': int(judged.sum() - in_rank.sum()),
            'share_of_judgeable_filled_in_rank': float(in_rank.sum() / max(int(judged.sum()), 1)),
            'share_of_rank_entries_that_are_filled': float(in_rank.sum() / max(rank_entries, 1)),
            'measure_covers_the_change': bool(in_rank.sum() >= 0.5 * judged.sum()),
        },
        'per_target': {'filled': quantiles(fill.sum(axis=1)), 'filled_judgeable': quantiles(judged.sum(axis=1)),
                       'filled_in_rank': quantiles(in_rank.sum(axis=1)),
                       'share_of_rank_energy_from_filled': quantiles(energy_share)},
        'T0_valid_share_inside_rank_genes': float(valid['T0'][:, cols95].mean()),
    }

    # 4. four arms with identical masks and scale
    rows_pred = np.flatnonzero(obs_e2.any(axis=1))
    donor = np.arange(len(panel))
    donor[rows_pred] = rows_pred[M.shuffled_rows(rows_pred.size)]
    gen_fill = (lfc_g.astype(np.float64) * amplitude).astype(np.float32)
    swap_fill = expected[donor]
    arms = {'zero': lfc_t0, 'esm2': lfc_f, 'generic': np.where(fill_all, gen_fill, lfc_t0),
            'swapped': np.where(fill_all, swap_fill, lfc_t0)}
    doc['controls_built'] = {'E2_rows_with_a_prediction': int(rows_pred.size),
                             'filled_pairs_without_generic': int((fill_all & ~obs_g).sum()),
                             'filled_pairs_whose_donor_lacks_the_gene': int((fill_all & ~obs_e2[donor]).sum()),
                             'swap_seed': M.BOOT_SEED, 'amplitude': amplitude}

    # the generator's view: one truth-defined support for every arm, an unpredicted pair counts as zero
    cols95g = truth_ok.mean(axis=0) >= 0.95
    one_truth = np.where(truth_ok, np.nan_to_num(shrunk.astype(np.float64)), 0.0)
    shuffle_panel = M.shuffled_rows(len(panel))
    view = {**arms, 'zero~shuffle': lfc_t0[shuffle_panel]}
    per = {}
    for name, lfc in view.items():
        lfc_keep = np.where(truth_ok, lfc[keep], 0.0)
        per[name] = M.per_target(lfc_keep, truth_ok, shrunk, raw, se, cols95g)
        per[name]['disc95g'] = M.per_target(lfc_keep, truth_ok, one_truth, raw, se, cols95g)['disc']
        per[name].pop('disc')
    measures = ('disc95g', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')
    pairs = (('esm2', 'zero'), ('esm2', 'swapped'), ('esm2', 'generic'), ('generic', 'zero'),
             ('swapped', 'zero'), ('zero', 'zero~shuffle'))
    with np.errstate(all='ignore'):
        levels = {a: {m: float(np.nanmean(per[a][m])) for m in measures} for a in view}
    doc['generator_view'] = {
        'genes_for_rank_95g': int(cols95g.sum()), 'pairs_in_support': int(truth_ok.sum()),
        'levels': levels,
        'contrasts': {'%s-%s' % (a, b): {m: {**M.strip(M.paired_bootstrap(per[a][m], per[b][m])),
                                             'higher_is_better': M.HIGHER_IS_BETTER.get(m, True)} for m in measures}
                      for a, b in pairs}}
    control = doc['generator_view']['contrasts']['zero-zero~shuffle']['disc95g']
    doc['generator_view']['disc95g_control_passed'] = bool(control['resolved'] and control['mean'] > 0)

    masks = {'zero': obs_t0[keep], 'esm2': obs_f[keep], 'generic': obs_f[keep], 'swapped': obs_f[keep]}
    sac = {name: sign_and_coverage(M, arms[name][keep], masks[name], truth_ok, shrunk, raw, se) for name in arms}
    with np.errstate(all='ignore'):
        doc['sign_apart_from_coverage'] = {
            'note': 'added after the C-K562 numbers of r1 were read and before any C-iPSC number (ADDENDUM_v3_1.md)',
            'levels': {name: {k: float(np.nanmean(v)) for k, v in sac[name].items()} for name in sac},
            'contrasts': {'%s-%s' % (a, b): {k: M.strip(M.paired_bootstrap(sac[a][k], sac[b][k])) for k in sac[a]}
                          for a, b in (('esm2', 'zero'), ('esm2', 'swapped'), ('esm2', 'generic'))}}

    # the own-support convention of the frozen bench, for the same pair of arms (what was published)
    own = {}
    for name in ('T0', 'fallback'):
        lfc = labels[name][0][keep]
        own[name] = M.per_target(lfc, valid[name], shrunk, raw, se, cols)
        own[name]['disc95'] = as_run[name]
    doc['own_support_as_published'] = {
        m: {**M.strip(M.paired_bootstrap(own['fallback'][m], own['T0'][m])),
            'published_mean': block['contrasts'].get(spec.get('integration_contrast', 'C_integration'), {})
            .get('measures', {}).get(m, {}).get('all', {}).get('mean')}
        for m in ('disc95', 'r_spec', 'sign50', 'reach', 'nmae_conf', 'mse_ratio')}

    # the filled pairs alone
    only = {name: filled_only(M, arms[name][keep], judged, shrunk, raw, se) for name in ('esm2', 'generic', 'swapped')}
    readable = np.isfinite(only['esm2']['mse_vs_zero'])
    doc['filled_only'] = {
        'targets_with_enough_filled_pairs': int(readable.sum()), 'min_filled_pairs': MIN_FILLED,
        'targets_with_enough_confident_filled_pairs': int(np.isfinite(only['esm2']['sign_conf']).sum()),
        'min_confident_pairs': MIN_CONF,
        'filled_pairs_per_readable_target': quantiles(only['esm2']['n_filled'][readable]),
        'confident_filled_pairs_per_readable_target': quantiles(only['esm2']['n_conf'][readable]),
        'levels': {name: {k: float(np.nanmean(only[name][k]))
                          for k in ('mse_vs_zero', 'nmae_conf_vs_zero', 'sign_conf', 'cos', 'amp_star')}
                   for name in only},
        'against_zero': {name: {**{k: against(M, only[name][k], 1.0) for k in ('mse_vs_zero', 'nmae_conf_vs_zero')},
                                'cos': against(M, only[name]['cos'], 0.0)} for name in only},
        'contrasts': {'%s-%s' % (a, b): {k: M.strip(M.paired_bootstrap(only[a][k], only[b][k]))
                                         for k in ('mse_vs_zero', 'nmae_conf_vs_zero', 'sign_conf', 'cos')}
                      for a, b in (('esm2', 'swapped'), ('esm2', 'generic'))},
        'cos_and_amp_star_note': 'added after the C-K562 numbers of r1 were read and before any C-iPSC number '
                                 '(ADDENDUM_v3_1.md)'}

    # the words of section 2, decided by the rule written before the numbers
    gv = doc['generator_view']['contrasts']
    doc['reading'] = {
        'fallback_reduces_error': bool(gv['esm2-zero']['mse_ratio']['resolved'] and gv['esm2-zero']['mse_ratio']['mean'] < 0),
        'gain_is_target_specific': bool(gv['esm2-swapped']['mse_ratio']['resolved']
                                        and gv['esm2-swapped']['mse_ratio']['mean'] < 0),
        'generic_part_is_enough': bool(gv['generic-zero']['mse_ratio']['resolved'] and gv['generic-zero']['mse_ratio']['mean'] < 0
                                       and not gv['esm2-generic']['mse_ratio']['resolved']),
        'fallback_discriminates_better': bool(doc['generator_view']['disc95g_control_passed']
                                              and gv['esm2-zero']['disc95g']['resolved']
                                              and gv['esm2-zero']['disc95g']['mean'] > 0),
        'frozen_measure_covers_the_change': doc['support']['filled']['measure_covers_the_change'],
        'section_8_outcome_unchanged': 'INCONCLUDENTE until level B exists; these diagnostics neither promote nor reject'}
    return doc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--spec', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--bench-dir')
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding='utf-8'))
    doc = audit(spec, load_metrics(args.bench_dir))
    doc['spec_sha256'] = sha(args.spec)
    doc['code_sha256'] = sha(__file__)
    with Path(args.out).open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    print(json.dumps({k: doc.get(k) for k in ('fold', 'parity', 'adapter', 'stopped', 'reading')}, indent=1, default=str))


if __name__ == '__main__':
    main()
