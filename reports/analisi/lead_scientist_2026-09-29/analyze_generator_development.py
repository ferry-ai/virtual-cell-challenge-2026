"""Descriptive analysis of frozen development reports; no scoring or selection."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd

METRICS = {
    'pds_cosine': 'PDS', 'expr_mse_unbiased_capped_norm': 'MSE',
    'de_wilcoxon_lfc_nmae': 'NMAE', 'de_wilcoxon_direction_fidelity_yield_raw': 'FID',
    'de_wilcoxon_direction_reach_raw': 'REACH', 'de_wilcoxon_sig_jaccard': 'JAC'}
FIVE = [m for m in METRICS if METRICS[m] != 'MSE']


def stats(x):
    x = np.asarray(x, dtype=float)
    return dict(zip(('min', 'q25', 'median', 'q75', 'max'), np.quantile(x, [0, .25, .5, .75, 1]).tolist()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reports', type=Path, required=True)
    p.add_argument('--anchors', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    copied = read(a.reports / 'COPY_MANIFEST.json')
    for item in copied['files']:
        data = (a.reports / item['path']).read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    d = a.reports / 'development'
    manifest = read(a.reports / 'target_manifest.json')
    run = read(d / 'run_manifest.json')
    assert run['split'] == 'development' and run['truth'] == 'full'
    targets = run['targets']
    assert set(targets) == set(manifest['development']) and len(targets) == 48
    anchors = read(a.anchors)['anchors']
    slopes = np.array([1 / (anchors[m]['replicate'] - anchors[m]['baseline']) / 6 for m in FIVE])
    selection = read(d / 'selection.json')
    results, per, comp, diag = {}, {}, {}, {}
    for path in sorted(d.glob('result_*.json')):
        arm = path.stem.removeprefix('result_')
        results[arm] = read(path)
        long = pd.read_csv(d / f'per_pert_{arm}.csv', keep_default_na=False)
        long['value'] = pd.to_numeric(long['value'], errors='coerce')
        assert not long.duplicated(['perturbation', 'metric']).any()
        per[arm] = long.pivot(index='perturbation', columns='metric', values='value').reindex(targets)
        comp[arm] = pd.read_csv(d / f'components_{arm}.csv', keep_default_na=False).set_index('target').reindex(targets)
        diag[arm] = pd.DataFrame(read(d / f'diagnostics_{arm}.json')).set_index('target').reindex(targets)
    ref = 'a1_p0_s1'
    mask = per[ref][FIVE].notna().to_numpy()
    n = mask.sum(0)
    rawrows, memberrows, influence, summary = [], [], [], {}
    metadata = pd.DataFrame({'target': targets, 'real_cells': [len(manifest['target_rows'][t]) for t in targets],
                             'n_conf': comp[ref]['n_conf'].to_numpy()}).set_index('target')
    all_deltas = {}
    for arm, res in results.items():
        frame = per[arm]
        assert np.array_equal(frame[FIVE].notna().to_numpy(), mask)
        assert np.array_equal(comp[arm]['n_conf'], comp[ref]['n_conf'])
        reconstructed_fid = comp[arm]['k'] / comp[arm][['n_pred', 'n_conf']].max(axis=1)
        assert np.allclose(reconstructed_fid, frame['de_wilcoxon_direction_fidelity_yield_raw'], atol=1e-12)
        # The MSE aggregate is a ratio of sums, not a mean of per-target ratios.
        mse = frame['expr_mse_unbiased_capped'].sum() / frame['expr_distance_unbiased'].sum()
        assert abs(mse - res['raw']['expr_mse_unbiased_capped_norm']) < 1e-10
        delta = (frame[FIVE].to_numpy() - per[ref][FIVE].to_numpy()) * slopes
        all_deltas[arm] = delta
        members = np.nanmean(delta, axis=0)
        total = float(members.sum())
        memberrows.append({'arm': arm, 'delta_projection': total, **dict(zip([METRICS[m] for m in FIVE], members))})
        eligible = comp[arm]['n_conf'] > 0
        row = {'arm': arm, 'amplitude': res['amplitude_relative'], 'phi_scale': res['phi_scale'],
               'generator': res['generator'], 'delta_projection': total,
               **{METRICS[m]: v for m, v in res['raw'].items()},
               'n_pred_median': comp[arm]['n_pred'].median(), 'n_pred_mean': comp[arm]['n_pred'].mean(),
               'n_pred_sum': int(comp[arm]['n_pred'].sum()), 'k_mean': comp[arm]['k'].mean(),
               'precision_pooled': comp[arm]['k'].sum() / comp[arm]['n_pred'].sum(),
               'fidelity_is_precision_targets': int((comp[arm].loc[eligible, 'n_pred'] >= comp[arm].loc[eligible, 'n_conf']).sum()),
               'realised_bulk_l1_median': diag[arm].get('realised_bulk_l1_from_expected', pd.Series(dtype=float)).median(),
               'clipped_gene_pairs': diag[arm]['n_genes_clipped'].sum(),
               'mean_library_median': diag[arm].get('mean_library', pd.Series(dtype=float)).median()}
        rawrows.append(row)
        # Exact additive attribution; denominators differ across metric populations.
        individual = np.nansum(delta / n[None, :], axis=1)
        assert abs(individual.sum() - total) < 1e-12
        order = np.argsort(-individual)
        for i, t in enumerate(targets):
            influence.append({'arm': arm, 'target': t, 'contribution_to_total': individual[i],
                              'real_cells': metadata.loc[t, 'real_cells'], 'n_conf': metadata.loc[t, 'n_conf'],
                              'n_pred': comp[arm].loc[t, 'n_pred'], 'k': comp[arm].loc[t, 'k'],
                              **{METRICS[m]: delta[i, j] / n[j] for j, m in enumerate(FIVE)}})
        leaveout = {}
        for k in (1, 3, 5):
            remain = np.ones(len(targets), bool)
            remain[order[:k]] = False
            leaveout[str(k)] = float(np.nanmean(delta[remain], axis=0).sum())
        strata = []
        for low, high, name in [(-1, 0, '0'), (0, 9, '1-9'), (9, 99, '10-99'), (99, 499, '100-499'), (499, 1999, '500-1999'), (1999, np.inf, '2000+')]:
            keep = (metadata['n_conf'].to_numpy() > low) & (metadata['n_conf'].to_numpy() <= high)
            strata.append({'n_conf': name, 'targets': int(keep.sum()), 'contribution_to_total': float(individual[keep].sum()),
                           'member_contributions': dict(zip([METRICS[m] for m in FIVE], np.nansum(delta[keep] / n[None, :], axis=0).tolist()))})
        summary[arm] = {'positive_target_contributions': int((individual > 0).sum()),
                        'negative_target_contributions': int((individual < 0).sum()),
                        'top5': [{'target': targets[i], 'contribution_to_total': float(individual[i])} for i in order[:5]],
                        'bottom5': [{'target': targets[i], 'contribution_to_total': float(individual[i])} for i in order[-5:]],
                        'leave_top_k_out_recomputed_delta': leaveout, 'n_conf_strata': strata,
                        'rank_correlations': {
                            'gain_vs_n_conf': pd.Series(individual).corr(metadata['n_conf'].reset_index(drop=True), method='spearman') if np.ptp(individual) > 0 else None,
                            'gain_vs_real_cells': pd.Series(individual).corr(metadata['real_cells'].reset_index(drop=True), method='spearman') if np.ptp(individual) > 0 else None},
                        'reach_top5': sorted([{'target': t, 'contribution_to_total': float(delta[i, 3] / n[3]), 'n_conf': int(metadata.loc[t, 'n_conf'])} for i, t in enumerate(targets) if np.isfinite(delta[i, 3])], key=lambda x: -x['contribution_to_total'])[:5]}
    raw = pd.DataFrame(rawrows).set_index('arm')
    contributions = pd.DataFrame(memberrows).set_index('arm')
    for comparison in selection['comparisons']:
        matching = raw[(raw.amplitude == comparison['amplitude']) & (raw.phi_scale == comparison['phi_scale']) & (raw.generator == comparison['generator'])]
        assert len(matching) == 1
        assert abs(matching.iloc[0].delta_projection - comparison['delta_projection']) < 1e-12
    # Difference of differences isolates the amplitude x dispersion interaction.
    interactions = []
    for amp in ('1p5', '2'):
        for phi in ('0p25', '0p5', '1'):
            v = contributions.loc[f'a{amp}_p{phi}_s1'] - contributions.loc[f'a{amp}_p0_s1'] - contributions.loc[f'a1_p{phi}_s1']
            interactions.append({'amplitude': amp.replace('p', '.'), 'phi_scale': phi.replace('p', '.'), **v.to_dict()})
    out = {'written_utc': datetime.now(timezone.utc).isoformat(), 'claim_type': 'Exploratory development analysis, not a VCC score or confirmation.',
           'data_scope': '48 development targets only; confirmation outputs never read.',
           'verified_copy_files': len(copied['files']), 'verified_projection_comparisons': len(selection['comparisons']),
           'eligible_counts': dict(zip([METRICS[m] for m in FIVE], n.tolist())),
           'cells': stats(metadata.real_cells), 'real_cells_total': int(metadata.real_cells.sum()),
           'n_conf': stats(metadata.n_conf), 'n_conf_zero_targets': metadata.index[metadata.n_conf == 0].tolist(),
           'n_conf_lt10_targets': metadata.index[metadata.n_conf < 10].tolist(),
           'n_conf_vs_cells_spearman': metadata.n_conf.corr(metadata.real_cells, method='spearman'),
           'fixed_shortlist': selection['shortlist'], 'per_arm': summary,
           'verified': ['Copied file hash and size', 'Identical 48 target populations', 'Finite eligibility equal across arms',
                        'MSE ratio-of-sums reconstruction', 'Fidelity components formula', '13 projection deltas to 1e-12'],
           'anchors_sha256': hashlib.sha256(a.anchors.read_bytes()).hexdigest(),
           'analysis_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.out.mkdir()
    raw.to_csv(a.out / 'all_arms.csv')
    contributions.to_csv(a.out / 'member_contributions.csv')
    pd.DataFrame(influence).to_csv(a.out / 'target_contributions.csv', index=False)
    pd.DataFrame(interactions).to_csv(a.out / 'interactions.csv', index=False)
    metadata.to_csv(a.out / 'development_target_metadata.csv')
    (a.out / 'analysis.json').write_text(json.dumps(out, indent=2, allow_nan=True) + '\n', encoding='utf-8')
    print(raw.round(6).to_string())
    print(contributions.round(6).to_string())
    print(json.dumps({k: out[k] for k in ('cells', 'n_conf', 'n_conf_zero_targets', 'n_conf_vs_cells_spearman')}))
    for arm in ('a1p5_p1_s1', 'a1p5_p0p5_s1', 'bins_a1_s1'):
        print(arm, json.dumps(summary[arm]))


if __name__ == '__main__':
    main()
