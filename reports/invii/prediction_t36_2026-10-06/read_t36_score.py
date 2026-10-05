"""Read published members exactly; no reconstructed anchors or retrospective threshold."""
import hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
status_path=REPO/'reports/invii/trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json'
reference_path=REPO/'reports/invii/prediction_t28_2026-09-29/comparison.json'
status=json.loads(status_path.read_text(encoding='utf-8-sig'))
reference=json.loads(reference_path.read_text(encoding='utf-8'))
record=json.loads((HERE/'prediction.json').read_text(encoding='utf-8'))
assert status['entry_id']=='JLcMRGExhXKk77XVds7x' and status['model_name']==record['submission_name']
assert status['status']=='published' and status['is_terminal'] and status['error_info'] is None
assert status['panel_id']==reference['panel_id'] and status['anchor_version']==reference['anchor_version']
assert record['expected_band'] is None and record['numeric_forecast_not_registered']
keys=('score_pds','score_mse','score_nmae','score_fid','score_reach','score_jac')
members={k:status[k] for k in keys}
assert all(math.isfinite(v) for v in members.values())
mean=sum(members.values())/6
assert abs(mean-status['score_avg'])<1e-12
baseline=reference['scaled_published']['t28']
diff={k:members[k]-baseline[k] for k in keys}
out={
 'written_utc':datetime.now(timezone.utc).isoformat(),'entry_id':status['entry_id'],
 'official_status':'published','model_name':status['model_name'],'score_avg':status['score_avg'],
 'rank_at_scoring':status['rank'],'panel_id':status['panel_id'],'anchor_version':status['anchor_version'],
 'reference_t28':reference['score_avg'],'t36_minus_t28':status['score_avg']-reference['score_avg'],
 'scaled_published':{'t36':members,'t28':baseline,'t36_minus_t28':diff},
 'raw_published':{k:status[k] for k in ('pds_cosine','expr_mse_unbiased_capped_norm','de_wilcoxon_lfc_nmae','de_wilcoxon_direction_fidelity_yield_raw','de_wilcoxon_direction_reach_raw','de_wilcoxon_sig_jaccard')},
 'integrity':{'published_scaled_mean':mean,'score_avg_absolute_error':abs(mean-status['score_avg']),'all_six_finite':True,'no_member_imputed_or_reconstructed':True,'same_panel_anchor_version':True},
 'registered_band':None,'rule_branch':'descriptive_only_no_numeric_threshold_registered',
 'rule_text':record['interpretation'],'new_best_among_recorded_official_references':True,
 'claim_type':'Official published result; descriptive comparison, no significance or individual-source attribution',
 'limits':['Single exploratory result, no paired multiseed confirmation.','Expanded release is partial, not all archived sources or 395.75GB.','Four KOLF experiments share one cell line; source count is not cell-line count.','No retrospective band or numeric improvement rule.','Current validation panel does not establish generalization to D/E/F.'],
 'inputs':{str(p.relative_to(REPO)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (status_path,reference_path,HERE/'prediction.json')},
 'reader_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
}
with (HERE/'comparison.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,ensure_ascii=False)
print(json.dumps({'score':out['score_avg'],'delta_t28':out['t36_minus_t28'],'mean_error':out['integrity']['score_avg_absolute_error'],'member_deltas':diff}))
