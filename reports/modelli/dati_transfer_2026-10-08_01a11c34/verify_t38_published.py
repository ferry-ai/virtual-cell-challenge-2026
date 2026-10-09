"""Independently check the fresh official status against the frozen rule and comparison."""
import json
import math
from percorso import HERE, ROOT, read, pin, sha, write_new, now


def main():
    current_path = ROOT / 'reports/invii/trial_2026-10-09/status_LJmnhqqh1WTrx1JcoRlr_lead_update_r2.json'
    reference_path = ROOT / 'reports/invii/trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json'
    prediction_path = ROOT / 'reports/invii/prediction_t38_2026-10-09/prediction.json'
    comparison_path = prediction_path.with_name('comparison.json')
    current, reference, prediction, comparison = map(read, (current_path, reference_path, prediction_path, comparison_path))
    assert current['status'] == reference['status'] == 'published'
    assert current['entry_id'] == 'LJmnhqqh1WTrx1JcoRlr'
    assert reference['entry_id'] == 'JLcMRGExhXKk77XVds7x'
    assert sha(prediction_path) == 'c680e024c165e9f783db96faccae8081e6f4c241da47e065f6b2e0d28eedb3dd'
    for key in ('panel_id', 'anchor_version', 'partition'):
        assert current[key] == reference[key] and current[key] is not None
    scaled = ('score_pds', 'score_mse', 'score_nmae', 'score_fid', 'score_reach', 'score_jac')
    raw = ('pds_cosine', 'expr_mse_unbiased_capped_norm', 'de_wilcoxon_lfc_nmae',
           'de_wilcoxon_direction_fidelity_yield_raw', 'de_wilcoxon_direction_reach_raw', 'de_wilcoxon_sig_jaccard')
    for name, status in [('t38', current), ('t36', reference)]:
        assert all(isinstance(status[k], (int, float)) and math.isfinite(status[k]) for k in scaled)
        assert abs(sum(status[k] for k in scaled) / 6 - status['score_avg']) < 1e-14
        assert comparison['scaled_published'][name] == {k: status[k] for k in scaled}
        assert comparison['raw_published'][name] == {k: status[k] for k in raw}
    delta = current['score_avg'] - reference['score_avg']
    assert prediction['reference']['official_score'] == reference['score_avg']
    assert prediction['decision_threshold_absolute'] == 0.005
    assert abs(delta) <= prediction['decision_threshold_absolute']
    assert comparison['t38_minus_t36'] == delta
    assert comparison['rule_branch'] == 'delta_within_plus_minus_0.005'
    assert comparison['rule_text'] == prediction['readout_rule'][comparison['rule_branch']]
    assert comparison['scaled_delta'] == {k: current[k] - reference[k] for k in scaled}
    write_new(HERE / 't38_published_verified_r1.json', dict(
        utc=now(), status='PASS_FRESH_OFFICIAL_STATUS_AND_EXISTING_COMPARISON',
        entry_id=current['entry_id'], official_status=current['status'], score_avg=current['score_avg'],
        t36_score=reference['score_avg'], delta=delta, threshold=prediction['decision_threshold_absolute'],
        rule_branch=comparison['rule_branch'], verdict='INCONCLUSIVE_AGAINST_T36',
        inside_registered_band=prediction['expected_score_band'][0] <= current['score_avg'] <= prediction['expected_score_band'][1],
        partition=current['partition'], panel_id=current['panel_id'], anchor_version=current['anchor_version'],
        same_panel_partition_anchors=True, all_six_scaled_published=True, no_imputed_member=True,
        scaled_mean=sum(current[k] for k in scaled) / 6,
        scaled_published={k: current[k] for k in scaled}, scaled_delta={k: current[k] - reference[k] for k in scaled},
        rank_at_fresh_read=current['rank'], rank_at_original_comparison=comparison['rank_at_scoring'],
        rank_note='Rank is time-dependent; all score fields and the preregistered verdict agree.',
        evidence={k:pin(p) for k,p in [('fresh_status',current_path),('reference_status',reference_path),
            ('prediction',prediction_path),('existing_comparison',comparison_path)]},
        existing_checkpoint='docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md',
        new_submission=False, scientific_promotion=False, source_effect_attribution=False, claims_complete_D053=False))
    print(json.dumps(dict(status='PASS', score=current['score_avg'], delta=delta, verdict='INCONCLUSIVE_AGAINST_T36')))


if __name__ == '__main__':
    main()
