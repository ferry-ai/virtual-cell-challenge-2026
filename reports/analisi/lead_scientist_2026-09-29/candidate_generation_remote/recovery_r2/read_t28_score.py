"""Read a complete official t28 status with its unchanged preregistered rule.

Offline only. Never fetches status, submits, estimates an absent member, clips
published scores, or derives official scaled scores from aggregate raw values.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
REGISTRATION = REPO/'reports/invii/prediction_t28_2026-09-29/prediction.json'
REGISTRATION_SHA = 'a2081b9cd615a1020a962def21eafa54d7116db79285887f56c775033d61e192'
BASELINE = REPO/'reports/invii/trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json'
BASELINE_SHA = 'fbef35a25f683e3158b19b83199cd19d0448ecec1c01cbd8d1143cecc9b0d90d'
MODEL = 'trial-28 amplified multi-source transfer with control-fitted gene dispersion'
SCORES = {'pds_cosine': 'score_pds', 'expr_mse_unbiased_capped_norm': 'score_mse',
    'de_wilcoxon_lfc_nmae': 'score_nmae', 'de_wilcoxon_direction_fidelity_yield_raw': 'score_fid',
    'de_wilcoxon_direction_reach_raw': 'score_reach', 'de_wilcoxon_sig_jaccard': 'score_jac'}
UPPER_RULE = 'score >= 0.14523806091483554'
LOWER_RULE = 'score <= 0.13523806091483553'
UPPER = 0.14523806091483554
LOWER = 0.13523806091483553


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError('Missing/nonfinite numeric member: '+field)
    return float(value)


def check_status(status, entry_id, *, model=None):
    if status.get('entry_id') != entry_id:
        raise ValueError('Official status belongs to a different entry')
    if status.get('status') not in ('published', 'superseded') or status.get('is_terminal') is not True:
        raise ValueError('Official result is not a complete scored terminal status')
    if status.get('error_info') is not None:
        raise ValueError('Official status carries an error')
    if model is not None and status.get('model_name') != model:
        raise ValueError('Official model name is not the frozen t28 model')
    for metric in ['score_avg', *SCORES, *SCORES.values()]:
        number(status.get(metric), metric)
    mean = math.fsum(status[name] for name in SCORES.values())/6
    if not math.isclose(mean, status['score_avg'], rel_tol=0., abs_tol=1e-12):
        raise ValueError('Published six-member mean disagrees with score_avg')
    return mean


def rule(score, registration):
    rules = registration['reading_rule_fixed_before_the_result']
    if set(rules) != {UPPER_RULE, LOWER_RULE, 'otherwise'}:
        raise ValueError('Frozen t28 rule changed')
    score = number(score, 'score_avg')
    # Compare the exact registered score cutoffs, not a rounded delta or band.
    branch = UPPER_RULE if score >= UPPER else LOWER_RULE if score <= LOWER else 'otherwise'
    return branch, rules[branch]


def compare(status, baseline, registration, expected_entry):
    mean = check_status(status, expected_entry, model=MODEL)
    check_status(baseline, 'ekxW6wo83Csum25pkddl')
    for key in ('panel_id', 'anchor_version', 'partition'):
        if not baseline.get(key) or status.get(key) != baseline[key]:
            raise ValueError('Incompatible official score basis: '+key)
    if registration['references']['t25'] != baseline['score_avg']:
        raise ValueError('Registered reference is not the frozen official t25')
    branch, text = rule(status['score_avg'], registration)
    delta = status['score_avg']-baseline['score_avg']
    raw = {m: {'t28': status[m], 't25': baseline[m], 't28_minus_t25': status[m]-baseline[m]} for m in SCORES}
    scaled = {label: {s: table[s] for s in SCORES.values()} for label, table in (('t25', baseline), ('t28', status))}
    scaled['t28_minus_t25'] = {s: status[s]-baseline[s] for s in SCORES.values()}
    scaled['t28_minus_t25_contribution_to_mean'] = {s: (status[s]-baseline[s])/6 for s in SCORES.values()}
    band = registration['expected']['score_avg_band']
    difference_band = registration['expected']['t28_minus_t25_band']
    return {'written_utc': datetime.now(timezone.utc).isoformat(), 'entry_id': expected_entry,
        'submission_date': status.get('submission_date'), 'score_avg': status['score_avg'],
        'rank_at_scoring': status.get('rank'), 'official_status': status['status'],
        'panel_id': status['panel_id'], 'anchor_version': status['anchor_version'],
        't28_minus_t25': delta,
        't28_minus_t22_t24_mean': status['score_avg']-registration['references']['t22_t24_mean'],
        't28_minus_t24_best_observed': status['score_avg']-registration['references']['t24_best_observed'],
        'new_best_observed_among_registered_references': status['score_avg'] > registration['references']['t24_best_observed'],
        'rule_branch': branch, 'rule_text': text,
        'registered_band': band, 'inside_avg_band': band[0] <= status['score_avg'] <= band[1],
        't28_minus_t25_band': difference_band,
        'inside_diff_band': difference_band[0] <= delta <= difference_band[1],
        'reference': registration['references'], 'scaled_published': scaled, 'raw': raw,
        'registered_raw_priors': registration['expected'],
        'integrity': {'all_six_raw_finite': True, 'all_six_published_scaled_finite': True,
                      'published_scaled_mean': mean, 'score_avg_absolute_error': abs(mean-status['score_avg']),
                      'no_member_imputed_or_clipped': True, 'same_panel_anchor_version': True},
        'claim_type': 'Official published scores; fixed prospective reading rule, not a new significance test',
        'limits': ['A new best observed score alone does not pass the registered improvement threshold.',
                   'The joint amplitude/dispersion change does not identify either factor alone.',
                   'This current-panel result does not establish generalization to new contexts.',
                   'Raw-to-scaled aggregate reconstruction is not used; official published members are authoritative.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--status', type=Path, required=True)
    p.add_argument('--entry-id', required=True, help='Expected entry from the actual t28 submit receipt')
    p.add_argument('--submit-result', type=Path, help='Optional raw official CLI submit JSON; binds expected entry/model')
    p.add_argument('--out', type=Path, required=True, help='New comparison JSON; refuses overwrite')
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    for path, expected in ((REGISTRATION, REGISTRATION_SHA), (BASELINE, BASELINE_SHA)):
        if sha(path) != expected:
            raise ValueError('Frozen source differs: '+str(path))
    load = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    inputs = [REGISTRATION, BASELINE, a.status]
    if a.submit_result:
        submission = load(a.submit_result)
        if submission.get('entry_id') != a.entry_id or submission.get('model_name') != MODEL:
            raise ValueError('Actual submit receipt is not this t28 entry')
        inputs.append(a.submit_result)
    output = compare(load(a.status), load(BASELINE), load(REGISTRATION), a.entry_id)
    output['inputs'] = {str(path): {'bytes': path.stat().st_size, 'sha256': sha(path)} for path in inputs}
    output['reader_sha256'] = sha(__file__)
    output['entry_binding'] = 'submit receipt and explicit entry' if a.submit_result else 'explicit entry supplied by coordinator'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False); f.write('\n')
    print(json.dumps({'comparison': str(a.out), 'rule_branch': output['rule_branch'],
                      'score_avg': output['score_avg'], 't28_minus_t25': output['t28_minus_t25']}))


if __name__ == '__main__':
    main()
