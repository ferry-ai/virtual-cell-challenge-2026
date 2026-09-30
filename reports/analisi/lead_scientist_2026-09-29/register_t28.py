"""Freeze the t28 forecast before full generation; no data generation or submission."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / 'reports/invii/prediction_t28_2026-09-29'
    if out.exists() or (ROOT / 'configs/recipes/t28.json').exists():
        raise FileExistsError('t28 is already assigned; do not overwrite')
    selection_file = HERE / 'generator_confirmation_r3/confirmation/selection.json'
    analysis_file = HERE / 'confirmation_analysis/results_r1/analysis.json'
    selection = json.loads(selection_file.read_text())
    analysis = json.loads(analysis_file.read_text())
    winner = next(row for row in selection['comparisons']
                  if (row['amplitude'], row['phi_scale'], row['generator']) == (1.5, 1.0, 'pooled'))
    check = next(row for row in analysis['comparisons'] if row['arm'] == [1.5, 1.0, 'pooled'])
    if not (winner['passes_confirmation'] and check['passes_confirmation']
            and winner['delta_projection'] == check['delta_projection']
            and winner['delta_projection'] >= .005
            and len(winner['per_seed_delta']) == 3 and min(winner['per_seed_delta']) > 0
            and winner['paired_target_bootstrap_interval'][0] > 0):
        raise ValueError('No verified confirmation')
    inputs = json.loads((HERE / 'candidate_generation_remote/input_manifest_r1.json').read_text())
    registration = {
        'written_utc': datetime.now(timezone.utc).isoformat(),
        'label': 't28: t25 external effects x1.5, control-fitted gene dispersion x1',
        'claim_type': 'subjective forecast registered before full generation; no official result',
        'references': {'t25': .14023806091483554, 't22': .14125049908559736,
                       't24_best_observed': .14289686095002022, 't22_t24_mean': .1420736800178088},
        'source_recipe': 'configs/recipes/t25.json',
        'source_recipe_sha256': sha(ROOT / 'configs/recipes/t25.json'),
        'effects': 'processed/effects_t25_2026-09-27, unchanged input NPZ files',
        'input_manifest_sha256': sha(HERE / 'candidate_generation_remote/input_manifest_r1.json'),
        'code_archive_sha256': inputs['code_archive']['sha256'],
        'launcher_sha256': sha(HERE / 'candidate_generation_remote/generate_candidate.py'),
        'generator': {'stage': 45, 'trial': 'trial-ext-profile', 'contexts': ['A', 'B', 'C'],
                      'targets_per_context': 300, 'cells_per_target': 400, 'seed': 20260912,
                      'effects_scale': 1.5, 'gene_dispersion': True, 'gene_dispersion_scale': 1.0,
                      'depth_bins': False,
                      'scope_of_scaling': 'entire saved external effect vector, including embedded own/cis terms; not only recipe amplitude',
                      'sampling': 'new independent gamma-Poisson counts with empirical library-size sampling; no control-cell copies or pinned aggregate'},
        'joint_changes': 'effect scale and gene dispersion, selected by prospective factorial development and disjoint confirmation; D-047; no single-factor causal attribution',
        'confirmation': {'selection_path': str(selection_file.relative_to(ROOT)).replace('\\', '/'),
                         'selection_sha256': sha(selection_file), 'analysis_sha256': sha(analysis_file),
                         'n_targets': 96, 'winner': winner,
                         'not_vcc_score': True, 'ranked_first_in_development_and_confirmation': True},
        'expected': {'score_avg_band': [.135, .180], 'working_centre': .155,
                     't28_minus_t25_band': [-.00523806091483553, .03976193908516446],
                     'calibration': 'Subjective planning range, not a confidence or prediction interval. Centre discounts the +0.028918 public-context gain by roughly one half; that discount has not been empirically calibrated.',
                     'members': 'Directional fidelity and reach expected to improve; NMAE/Jaccard may worsen; PDS expected near unchanged. Raw MSE expected worse and its scaled value expected to remain clipped at zero.'},
        'reading_rule_fixed_before_the_result': {
            'score >= 0.14523806091483554': 'Gain >=0.005 over corrected t25: adopt this combination as a promising current-panel reference; no claim of generalization to D/E/F or attribution to one factor.',
            'score <= 0.13523806091483553': 'Loss >=0.005 versus t25: reject this combination as the current recipe improvement; inspect all raw members without moving the threshold.',
            'otherwise': 'Inconclusive for the prespecified improvement claim; record any new best observed leaderboard number separately from robustness. Existing recipe remains the reference pending further evidence.'},
        'risks': ['One public HepG2 context, different targets and K562-only source in the bench versus four-source t25 in production.',
                  'Independent target split does not make contexts or controls independent replications.',
                  'Bootstrap is conditional on observed targets, cells, controls and three seeds; it is not cross-context uncertainty.',
                  't28 includes no learned neural correction; neural routes are evaluated separately.'],
        'submission_authorized': False,
        'next': 'Generate and fully validate artifact, then request owner authorization for any VCC upload.'
    }
    out.mkdir()
    path = out / 'prediction.json'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(registration, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'path': str(path), 'sha256': sha(path), 'written_utc': registration['written_utc']}))


if __name__ == '__main__':
    main()
