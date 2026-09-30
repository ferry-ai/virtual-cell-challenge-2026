"""Post-hoc exact FID decomposition; no new scores or candidate decisions."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from analyze_biology import PROGRAMS, sha

HERE = Path(__file__).resolve().parent
LEAD = HERE.parent


def fidelity_decomposition(k0, n0, k1, n1, nconf):
    """Symmetric product decomposition where both prediction budgets are positive.

    FID = directional precision * capped call-budget coverage. A zero prediction
    budget has undefined precision: reject it rather than fabricate attribution.
    The scored FID itself is still defined there when nconf > 0.
    """
    k0, n0, k1, n1, nconf = np.broadcast_arrays(*[
        np.asarray(x, dtype=float) for x in (k0, n0, k1, n1, nconf)])
    if not all(np.isfinite(x).all() for x in (k0, n0, k1, n1, nconf)):
        raise ValueError('Nonfinite counts')
    if np.any(n0 <= 0) or np.any(n1 <= 0) or np.any(nconf < 0):
        raise ValueError('Attribution requires positive predicted budgets and nonnegative nconf')
    if np.any(k0 < 0) or np.any(k0 > n0) or np.any(k1 < 0) or np.any(k1 > n1):
        raise ValueError('Invalid correct-call count')
    p0, p1 = k0/n0, k1/n1
    c0, c1 = n0/np.maximum(n0, nconf), n1/np.maximum(n1, nconf)
    return dict(fid0=p0*c0, fid1=p1*c1, p0=p0, p1=p1, c0=c0, c1=c1,
                precision_component=(p1-p0)*(c0+c1)/2,
                coverage_component=(c1-c0)*(p0+p1)/2)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    target_file = HERE/'r1/per_target.csv'
    byseed_file = LEAD/'confirmation_analysis/results_r1/target_by_seed.csv'
    table = pd.read_csv(target_file).set_index('target')
    pairs = pd.read_csv(byseed_file).query("arm == 'a1p5_p1'").copy()
    if len(table) != 96 or len(pairs) != 288 or set(pairs.seed) != {1, 2, 3}:
        raise ValueError('Expected complete 96-target/3-seed confirmation')
    result = fidelity_decomposition(pairs.reference_k, pairs.reference_n_pred,
                                   pairs.k, pairs.n_pred, pairs.n_conf)
    for key, values in result.items():
        pairs[key] = values
    residual = pairs.fid1-pairs.fid0-pairs.precision_component-pairs.coverage_component
    if np.max(np.abs(residual)) > 1e-12:
        raise AssertionError('FID decomposition failed')
    inputs = [target_file, byseed_file, HERE/'r1/annotations_by_target.csv']
    checks = []
    for seed in (1, 2, 3):
        for arm, key in [('a1_p0', 'fid0'), ('a1p5_p1', 'fid1')]:
            path = LEAD/f'generator_confirmation_r3/confirmation/per_pert_{arm}_s{seed}.csv'
            inputs.append(path)
            original = pd.read_csv(path, keep_default_na=False)
            metric = original.query("metric == 'de_wilcoxon_direction_fidelity_yield_raw'")
            actual = pd.to_numeric(metric.set_index('perturbation').value)
            check = pairs[pairs.seed == seed].set_index('target')[key].sort_index()
            if set(actual.index) != set(check.index):
                raise AssertionError('Scorer target set differs')
            error = float(np.max(np.abs(check-actual.reindex(check.index))))
            if error > 1e-12:
                raise AssertionError('FID formula does not reconstruct actual scorer')
            checks.append({'arm': arm, 'seed': seed, 'max_error': error})
    numeric = ['fid0', 'fid1', 'p0', 'p1', 'c0', 'c1', 'precision_component', 'coverage_component']
    target = pairs.groupby('target')[numeric].mean().join(table[['n_conf', 'real_cells', 'contribution_to_projection']])
    strata = []
    for name, low, high in [('zero',0,0),('1_to_9',1,9),('10_to_99',10,99),
                             ('100_to_499',100,499),('500_plus',500,np.inf)]:
        selected = target[target.n_conf.between(low, high)]
        strata.append({'stratum': name, 'n': len(selected),
            'mean_precision_baseline': float(selected.p0.mean()),
            'mean_precision_candidate': float(selected.p1.mean()),
            'mean_capped_coverage_baseline': float(selected.c0.mean()),
            'mean_capped_coverage_candidate': float(selected.c1.mean()),
            'macro_FID_precision_contribution': float(selected.precision_component.sum()/96),
            'macro_FID_coverage_contribution': float(selected.coverage_component.sum()/96),
            'projection_contribution': float(selected.contribution_to_projection.sum())})
    corrcols = ['n_conf', 'real_cells', 'true_effect_distance_unbiased', 'source_expected_energy_all_genes']
    correlations = []
    for i, left in enumerate(corrcols):
        for right in corrcols[i+1:]:
            r, p = spearmanr(table[left], table[right])
            correlations.append({'left':left,'right':right,'rho':float(r),'p_exploratory':float(p)})
    annotations = pd.read_csv(HERE/'r1/annotations_by_target.csv').set_index('target')
    panel_targets = set(annotations.index)-set(json.loads((LEAD/'generator_confirmation_r3/target_manifest.json').read_text())['eligible'])
    # The recorded source confirms challenge and eligible sets are disjoint.
    if len(panel_targets) != 300:
        raise ValueError('Panel membership cannot be reconstructed from disjoint recorded sets')
    experimental = []
    for program in PROGRAMS:
        flag = table[program+'_experimental'].astype(bool)
        part = table[flag]
        experimental.append({'program':program,'n_confirmation':len(part),
            'n_panel':int(annotations.loc[sorted(panel_targets),program+'_experimental'].sum()),
            'mean_contribution_times96':float(part.contribution_to_projection.mean()*96),
            'projection_contribution':float(part.contribution_to_projection.sum()),
            'positive':int((part.contribution_to_projection > 0).sum()),
            'members':part.index.tolist()})
    total_delta = float((target.fid1-target.fid0).mean())
    out = {'created_utc':datetime.now(timezone.utc).isoformat(),
        'claim_type':'POST HOC descriptive exact decomposition; no change to predictions, selection, or gate',
        'targets':len(table),'pairs':len(pairs),'FID_formula_reconstruction':checks,
        'maximum_decomposition_residual':float(np.max(np.abs(residual))),
        'FID_macro_baseline':float(target.fid0.mean()),'FID_macro_candidate':float(target.fid1.mean()),
        'FID_macro_delta':total_delta,
        'precision_component_macro':float(target.precision_component.mean()),
        'coverage_component_macro':float(target.coverage_component.mean()),
        'precision_component_fraction_of_FID_delta':float(target.precision_component.mean()/total_delta),
        'coverage_component_fraction_of_FID_delta':float(target.coverage_component.mean()/total_delta),
        'uncapped_coverage_pairs_baseline':int((pairs.c0 < 1).sum()),
        'uncapped_coverage_pairs_candidate':int((pairs.c1 < 1).sum()),
        'feature_correlations':correlations,'nconf_strata':strata,
        'experimental_annotation_sensitivity':experimental,
        'source_files':{str(x):{'bytes':x.stat().st_size,'sha256':sha(x)} for x in inputs},
        'script_sha256':sha(Path(__file__))}
    a.out.mkdir(parents=True)
    target.reset_index().to_csv(a.out/'fidelity_decomposition_per_target.csv',index=False)
    (a.out/'supplement.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('source_files','experimental_annotation_sensitivity')},indent=2))


if __name__ == '__main__':
    main()
