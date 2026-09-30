"""Analyze a COMPLETED generator confirmation; never score, tune or select arms.

No input is opened unless selection.json exists. All input snapshots are checked
for stability before a new output directory is created. Small reports only.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import numpy as np
import pandas as pd

FIVE = ('pds_cosine', 'de_wilcoxon_lfc_nmae', 'de_wilcoxon_direction_fidelity_yield_raw',
        'de_wilcoxon_direction_reach_raw', 'de_wilcoxon_sig_jaccard')
SHORT = dict(zip(FIVE, ('PDS', 'NMAE', 'FID', 'REACH', 'JAC')))
MSE = 'expr_mse_unbiased_capped_norm'
NUMERATOR, DENOMINATOR = 'expr_mse_unbiased_capped', 'expr_distance_unbiased'
REFERENCE = (1., 0., 'pooled')
SEEDS = [1, 2, 3]
BOOTSTRAP_SEED, N_BOOTSTRAP, MIN_DELTA = 20260929, 2000, .005
STRATA = ((-1, 0, '0'), (0, 9, '1-9'), (9, 99, '10-99'), (99, 499, '100-499'),
          (499, 1999, '500-1999'), (1999, np.inf, '2000+'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b, message, atol=1e-10):
    require(np.allclose(a, b, atol=atol, rtol=1e-10, equal_nan=True), message)


def name(arm, seed):
    amp, phi, generator = arm
    token = lambda x: f'{x:g}'.replace('.', 'p')
    return (f'bins_a{token(amp)}' if generator == 'bins' else f'a{token(amp)}_p{token(phi)}') + f'_s{seed}'


def finite_mean(x, axis):
    count = np.isfinite(x).sum(axis=axis)
    return np.divide(np.nansum(x, axis=axis), count,
                     out=np.full(np.shape(count), np.nan, dtype=float), where=count > 0)


def bootstrap_check(average, indices):
    """Two independent reductions, same registered target draws (no seed resampling)."""
    registered = finite_mean(average[indices], axis=1).sum(axis=1)
    weights = np.zeros((len(indices), len(average)), dtype=np.int64)
    for i, draw in enumerate(indices):
        weights[i] = np.bincount(draw, minlength=len(average))
    totals = weights @ np.nan_to_num(average, nan=0.)
    eligible = weights @ np.isfinite(average).astype(np.int64)
    weighted = np.divide(totals, eligible, out=np.full(totals.shape, np.nan), where=eligible > 0).sum(axis=1)
    require(np.isfinite(registered).all(), 'A registered bootstrap draw has no eligible target for a member')
    close(registered, weighted, 'Independent bootstrap frequency-weight check failed', atol=1e-12)
    return registered, float(np.max(np.abs(registered - weighted)))


def promotion_rule(delta, per_seed, ci):
    checks = {'mean_at_least_0p005': bool(delta >= MIN_DELTA),
              'positive_in_all_three_seeds': bool(len(per_seed) == 3 and np.all(np.asarray(per_seed) > 0)),
              'paired_target_interval_lower_above_zero': bool(ci[0] > 0)}
    return checks, bool(all(checks.values()))


def reconstruct(candidate, reference, slopes, n_finalists=2, indices=None):
    """Arrays are seed x target x FIVE; each member keeps its own denominator."""
    candidate, reference = np.asarray(candidate, float), np.asarray(reference, float)
    require(candidate.shape == reference.shape and candidate.ndim == 3 and candidate.shape[0] == 3
            and candidate.shape[2] == 5, 'Expected matching three-seed FIVE arrays')
    require(not np.isinf(candidate).any() and not np.isinf(reference).any(), 'Infinite scored values')
    mask = np.isfinite(reference)
    require(np.array_equal(mask, np.isfinite(candidate)), 'Candidate/reference eligibility differs')
    require(np.all(mask == mask[0:1]), 'Eligibility differs across seeds')
    require(np.all(mask[0].sum(0) > 0), 'A member has no eligible target')
    require(n_finalists in (1, 2), 'Only one or two preregistered finalists allowed')
    differences = (candidate - reference) * np.asarray(slopes)[None, None, :] / 6
    average = finite_mean(differences, axis=0)
    members = finite_mean(average, axis=0)
    per_seed = finite_mean(differences, axis=1).sum(axis=1)
    delta = float(members.sum())
    close(per_seed.mean(), delta, 'Seed averaging identity failed')
    if indices is None:
        indices = np.random.default_rng(BOOTSTRAP_SEED).integers(0, len(average), (N_BOOTSTRAP, len(average)))
    draws, maximum_error = bootstrap_check(average, indices)
    level = .975 if n_finalists == 2 else .95
    ci = np.quantile(draws, [(1 - level) / 2, (1 + level) / 2]).tolist()
    checks, passed = promotion_rule(delta, per_seed, ci)
    summary = {'delta_projection': delta, 'per_seed_delta': per_seed.tolist(),
               'seed_sd': float(np.std(per_seed, ddof=1)), 'confidence_level': level,
               'paired_target_bootstrap_interval': ci, 'passes_confirmation': passed,
               'registered_rule_checks': checks, 'member_contributions': dict(zip(FIVE, members.tolist())),
               'eligible_targets_per_member': dict(zip(FIVE, mask[0].sum(0).tolist())),
               'independent_bootstrap_max_absolute_difference': maximum_error}
    return summary, differences, average, draws


def verify_reported(summary, reported):
    for field in ('delta_projection', 'per_seed_delta', 'seed_sd', 'confidence_level', 'paired_target_bootstrap_interval'):
        close(summary[field], reported[field], f'Registered selection mismatch: {field}')
    for field in ('member_contributions', 'eligible_targets_per_member'):
        require(set(reported[field]) == set(FIVE), f'Selection member set differs: {field}')
        close([summary[field][m] for m in FIVE], [reported[field][m] for m in FIVE], f'Selection mismatch: {field}')
    require(summary['passes_confirmation'] == reported['passes_confirmation'], 'Registered decision mismatch')


def describe_targets(average, targets, n_conf):
    n = np.isfinite(average).sum(0)
    pieces = np.where(np.isfinite(average), average / n[None, :], 0.)
    totals = pieces.sum(1)
    close(totals.sum(), finite_mean(average, 0).sum(), 'Additive target attribution failed')
    order = sorted(range(len(targets)), key=lambda i: (-totals[i], targets[i]))
    abs_order = sorted(range(len(targets)), key=lambda i: (-abs(totals[i]), targets[i]))
    top = lambda indices: [{'target': targets[i], 'contribution_to_total': float(totals[i])} for i in indices]
    leaveout = {}
    for k in (1, 3, 5):
        keep = np.ones(len(targets), bool)
        keep[order[:k]] = False
        remaining = finite_mean(average[keep], axis=0)
        leaveout[str(k)] = float(remaining.sum()) if np.isfinite(remaining).all() else None
    strata = []
    for lower, upper, label in STRATA:
        keep = (n_conf > lower) & (n_conf <= upper)
        counts = np.isfinite(average[keep]).sum(0)
        conditional = finite_mean(average[keep], axis=0)
        strata.append({'n_conf_stratum': label, 'targets': int(keep.sum()),
                       'additive_contribution_to_full_panel': float(totals[keep].sum()),
                       **{f'{SHORT[m]}_contribution': float(pieces[keep, j].sum()) for j, m in enumerate(FIVE)},
                       **{f'{SHORT[m]}_eligible': int(counts[j]) for j, m in enumerate(FIVE)},
                       **{f'{SHORT[m]}_conditional_mean': float(conditional[j]) if counts[j] else None for j, m in enumerate(FIVE)}})
    net, absolute = float(totals.sum()), float(np.abs(totals).sum())
    diagnostic = {'used_for_promotion': False, 'positive_targets': int((totals > 0).sum()),
                  'negative_targets': int((totals < 0).sum()), 'top5': top(order[:5]), 'bottom5': top(order[-5:][::-1]),
                  'top5_net_fraction': float(totals[order[:5]].sum() / net) if net > 0 else None,
                  'top5_absolute_fraction': float(np.abs(totals[abs_order[:5]]).sum() / absolute) if absolute > 0 else None,
                  'leave_top_k_out_recomputed_delta': leaveout}
    return pieces, diagnostic, strata


class Snapshot:
    def __init__(self):
        self.data = {}

    def read(self, path):
        path = Path(path)
        require(path.suffix in ('.json', '.csv'), f'Only small JSON/CSV reports allowed: {path}')
        require(path.stat().st_size <= 2_000_000, f'Report unexpectedly large: {path}')
        if path not in self.data:
            self.data[path] = path.read_bytes()
        return self.data[path]

    def json(self, path):
        return json.loads(self.read(path))

    def csv(self, path):
        return pd.read_csv(io.BytesIO(self.read(path)), keep_default_na=False)

    def hashes(self):
        for path, content in self.data.items():
            require(path.read_bytes() == content, f'Report changed during analysis: {path}')
        return [{'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for p, b in self.data.items()]


def load_table(snapshot, path, targets):
    frame = snapshot.csv(path)
    require(not frame.duplicated(['perturbation', 'metric']).any(), 'Duplicate target/metric')
    require(set(frame.perturbation) == set(targets), f'Target set mismatch: {path}')
    frame['value'] = pd.to_numeric(frame.value.replace('', np.nan), errors='raise')
    table = frame.pivot(index='perturbation', columns='metric', values='value').reindex(targets)
    require(set(FIVE + (NUMERATOR, DENOMINATOR)) <= set(table.columns), 'Scorer components missing')
    require(np.isfinite(table[FIVE[0]]).all(), 'PDS must be finite for all targets')
    return table


def run(run_dir, target_manifest, development_selection, anchors_path, out):
    run_dir, out = Path(run_dir), Path(out)
    require(not out.exists(), 'Output already exists; never overwrite a report')
    # The bench writes this LAST. Refuse partial runs before opening any report.
    require((run_dir / 'selection.json').is_file(), 'Incomplete confirmation: selection.json absent; no partial reports opened')
    snapshot = Snapshot()
    selection = snapshot.json(run_dir / 'selection.json')
    require(bool(selection.get('finished_utc')) and selection.get('n_targets') == 96 and selection.get('truth') == 'full', 'Incomplete/wrong final selection')
    meta = snapshot.json(target_manifest)
    development = snapshot.json(development_selection)
    manifest = snapshot.json(run_dir / 'run_manifest.json')
    bench = snapshot.json(run_dir / 'bench.json')
    anchors = snapshot.json(anchors_path)['anchors']
    require(manifest['split'] == 'confirmation' and manifest['truth'] == 'full' and manifest['seeds'] == SEEDS, 'Wrong split/truth/seeds')
    targets = manifest['targets']
    require(len(targets) == 96 and targets == sorted(meta['confirmation']) and len(set(targets)) == 96, 'Confirmation targets differ from frozen 96')
    require(not set(targets).intersection(meta['development']), 'Development/confirmation target overlap')
    require(meta['cells_per_prediction'] == 400 and len(meta['control_rows']) == 2000, 'Cell/control counts differ from protocol')
    require(manifest['target_manifest_sha256'] == hashlib.sha256(snapshot.read(target_manifest)).hexdigest(), 'Target manifest hash differs')
    fingerprints = {Path(k.replace('\\', '/')).name: v['sha256'] for k, v in meta['fingerprints'].items()}
    require(fingerprints.get('anchors.json') == hashlib.sha256(snapshot.read(anchors_path)).hexdigest(), 'Anchor file differs from prepared fingerprint')
    require(fingerprints.get('generator_bench.py') == manifest['generator_script_sha256'], 'Generator differs from prepared fingerprint')
    require(development.get('n_targets') == 48 and development.get('truth') == 'full' and bool(development.get('finished_utc')), 'Development selection is not complete')
    require(bench['run_manifest'] == manifest, 'Bench and run manifests differ')
    finalists = [tuple(x) for x in development['shortlist']]
    require(len(finalists) in (1, 2) and len(set(finalists)) == len(finalists), 'Invalid development shortlist')
    arms = [tuple(x) for x in manifest['arms']]
    require(len(arms) == len(finalists) + 1 and set(arms) == {REFERENCE, *finalists}, 'Arms differ from frozen shortlist plus reference')
    registered = {(x['amplitude'], x['phi_scale'], x['generator']): x for x in selection['comparisons']}
    require(len(selection['comparisons']) == len(finalists) and set(registered) == set(finalists), 'Final comparison set differs')
    require(selection.get('shortlist') == [], 'Confirmation must not select a new shortlist')
    tables, components, results, raw_rows = {}, {}, {}, []
    n_conf = None
    for arm in arms:
        for seed in SEEDS:
            key = name(arm, seed)
            # Fail if even a non-scoring diagnostic was not completed.
            diagnostics = snapshot.json(run_dir / f'diagnostics_{key}.json')
            require(len(diagnostics) == 96 and {x['target'] for x in diagnostics} == set(targets), f'Incomplete generation diagnostics: {key}')
            table = load_table(snapshot, run_dir / f'per_pert_{key}.csv', targets)
            component = snapshot.csv(run_dir / f'components_{key}.csv')
            require(not component.target.duplicated().any() and set(component.target) == set(targets), 'Component target set differs')
            component = component.set_index('target').reindex(targets)
            require(np.isfinite(component[['n_conf', 'n_pred', 'k']]).all().all() and (component[['n_conf', 'n_pred', 'k']] >= 0).all().all(), 'Invalid direction components')
            if n_conf is None:
                n_conf = component.n_conf.to_numpy()
            close(component.n_conf.to_numpy(), n_conf, 'Reference confidence budget changed across arms/seeds', atol=0)
            fidelity = component.k / component[['n_conf', 'n_pred']].max(axis=1)
            close(fidelity, table[FIVE[2]], 'Fidelity component identity failed')
            result = snapshot.json(run_dir / f'result_{key}.json')
            require(result == bench['results'][key], f'Result and bench disagree: {key}')
            require((result['amplitude_relative'], result['phi_scale'], result['generator']) == arm and result['generator_seed'] == seed, 'Result arm/seed mismatch')
            for member in FIVE:
                close(table[member].mean(), result['raw'][member], f'Scorer macro aggregation mismatch: {key} {member}')
            numerator, denominator = table[NUMERATOR].to_numpy(), table[DENOMINATOR].to_numpy()
            require(np.isfinite(numerator).all() and np.isfinite(denominator).all() and denominator.sum() > 0, 'MSE components are incomplete or denominator nonpositive')
            close(numerator.sum() / denominator.sum(), result['raw'][MSE], 'MSE ratio-of-sums mismatch')
            tables[key], components[key], results[key] = table, component, result
            raw_rows.append({'arm': name(arm, 0).removesuffix('_s0'), 'seed': seed,
                             **{SHORT.get(m, 'MSE'): result['raw'][m] for m in (*FIVE, MSE)},
                             'n_pred_mean': float(component.n_pred.mean()), 'n_pred_median': float(component.n_pred.median()),
                             'k_mean': float(component.k.mean()), 'precision_pooled': float(component.k.sum() / component.n_pred.sum())})
    slopes = [1 / (anchors[m]['replicate'] - anchors[m]['baseline']) for m in FIVE]
    reference = np.stack([tables[name(REFERENCE, s)][list(FIVE)].to_numpy(float) for s in SEEDS])
    summaries, target_rows, seed_target_rows, strata_rows, draw_rows = [], [], [], [], []
    for arm in finalists:
        key = name(arm, 0).removesuffix('_s0')
        candidate = np.stack([tables[name(arm, s)][list(FIVE)].to_numpy(float) for s in SEEDS])
        summary, differences, average, draws = reconstruct(candidate, reference, slopes, len(finalists))
        verify_reported(summary, registered[arm])
        pieces, diagnostic, strata = describe_targets(average, targets, n_conf)
        mse_contribution = np.zeros(len(targets))
        for si, seed in enumerate(SEEDS):
            tab, ref = tables[name(arm, seed)], tables[name(REFERENCE, seed)]
            close(tab[DENOMINATOR], ref[DENOMINATOR], 'MSE denominator changed within a seed')
            mse_contribution += (tab[NUMERATOR].to_numpy() - ref[NUMERATOR].to_numpy()) / ref[DENOMINATOR].sum() / 3
            per_seed_pieces = np.where(np.isfinite(differences[si]), differences[si] / np.isfinite(average).sum(0)[None, :], 0.)
            for i, target in enumerate(targets):
                comp, rc = components[name(arm, seed)].loc[target], components[name(REFERENCE, seed)].loc[target]
                seed_target_rows.append({'arm': key, 'seed': seed, 'target': target,
                                        'contribution_to_projection': float(per_seed_pieces[i].sum()),
                                        **{SHORT[m]: float(per_seed_pieces[i, j]) for j, m in enumerate(FIVE)},
                                        'n_conf': int(n_conf[i]), 'n_pred': int(comp.n_pred), 'reference_n_pred': int(rc.n_pred),
                                        'k': int(comp.k), 'reference_k': int(rc.k)})
        mse_delta = float(np.mean([results[name(arm, s)]['raw'][MSE] - results[name(REFERENCE, s)]['raw'][MSE] for s in SEEDS]))
        close(mse_contribution.sum(), mse_delta, 'MSE target contributions fail aggregate identity')
        for i, target in enumerate(targets):
            target_rows.append({'arm': key, 'target': target, 'n_conf': int(n_conf[i]),
                                'real_cells': len(meta['target_rows'][target]), 'contribution_to_projection': float(pieces[i].sum()),
                                'MSE_raw_delta_contribution_separate': float(mse_contribution[i]),
                                **{SHORT[m]: float(pieces[i, j]) for j, m in enumerate(FIVE)}})
        strata_rows.extend({'arm': key, **row} for row in strata)
        draw_rows.extend({'arm': key, 'draw': i, 'delta_projection': float(v)} for i, v in enumerate(draws))
        summaries.append({'arm': list(arm), **summary, 'MSE_raw_delta_mean_seeds_separate': mse_delta, 'descriptive_diagnostics': diagnostic})
    provenance = snapshot.hashes()
    report = {'written_utc': datetime.now(timezone.utc).isoformat(),
              'claim': 'Reconstruction of the preregistered local confirmation; not a VCC score; no automatic submission.',
              'targets': 96, 'seeds': SEEDS, 'fixed_finalists': [list(x) for x in finalists],
              'registered_thresholds': {'minimum_delta': MIN_DELTA, 'bootstrap_draws': N_BOOTSTRAP,
                                        'bootstrap_seed': BOOTSTRAP_SEED, 'level': .975 if len(finalists) == 2 else .95},
              'comparisons': summaries, 'input_files': provenance,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Subgroups, concentration and target deletion are descriptive only; no additional promotion rules.',
              'bootstrap_scope': 'Paired targets, common draws across metrics and seeds; does not resample seeds, controls, cells or context.'}
    out.mkdir(parents=True)
    (out / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for filename, rows in [('raw_by_seed.csv', raw_rows), ('target_contributions.csv', target_rows),
                           ('target_by_seed.csv', seed_target_rows), ('n_conf_subgroups.csv', strata_rows),
                           ('registered_bootstrap_draws.csv', draw_rows)]:
        pd.DataFrame(rows).to_csv(out / filename, index=False)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ('run-dir', 'target-manifest', 'development-selection', 'anchors', 'out'):
        p.add_argument('--' + field, required=True, type=Path)
    a = p.parse_args()
    result = run(a.run_dir, a.target_manifest, a.development_selection, a.anchors, a.out)
    print(json.dumps({'out': str(a.out), 'verified_completed_run': True,
                      'comparisons': [{k: c[k] for k in ('arm', 'delta_projection', 'passes_confirmation')} for c in result['comparisons']]}, indent=2))


if __name__ == '__main__':
    main()
