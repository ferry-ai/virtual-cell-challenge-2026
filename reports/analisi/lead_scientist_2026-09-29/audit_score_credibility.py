"""Read only completed small reports; independently check score arithmetic.

No scorer, training, cell matrices, network, new selection or submission.
The output directory must be new. Frozen scientific results are never changed.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIVE = ('pds_cosine', 'de_wilcoxon_lfc_nmae',
        'de_wilcoxon_direction_fidelity_yield_raw',
        'de_wilcoxon_direction_reach_raw', 'de_wilcoxon_sig_jaccard')
SCORES = ('score_pds', 'score_nmae', 'score_fid', 'score_reach', 'score_jac')
MSE = 'expr_mse_unbiased_capped_norm'


class Snapshot:
    def __init__(self):
        self.files = {}

    def read(self, path):
        path = Path(path)
        if path not in self.files:
            if path.stat().st_size > 2_000_000:
                raise ValueError(f'Not a small report: {path}')
            self.files[path] = path.read_bytes()
        return self.files[path]

    def json(self, path):
        return json.loads(self.read(path))

    def hashes(self):
        out = []
        for path, data in self.files.items():
            if path.read_bytes() != data:
                raise ValueError(f'Input changed: {path}')
            out.append({'path': str(path.relative_to(REPO)), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
        return out


def require(ok, message):
    if not ok:
        raise ValueError(message)


def near(a, b, message):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-12, message)


def table(snapshot, path, targets):
    rows = list(csv.DictReader(io.StringIO(snapshot.read(path).decode('utf-8'))))
    keys = [(r['perturbation'], r['metric']) for r in rows]
    require(len(keys) == len(set(keys)), 'Duplicate per-target metric')
    require({k[0] for k in keys} == set(targets), 'Target set differs')
    result = {k: float(r['value']) if r['value'] else math.nan for k, r in zip(keys, rows)}
    require(not any(math.isinf(v) for v in result.values()), 'Infinite score')
    require(all(math.isfinite(result.get((t, FIVE[0]), math.nan)) for t in targets), 'Missing PDS')
    return result


def audit(out):
    require(not out.exists(), 'Output already exists')
    snapshot = Snapshot()
    anchors = snapshot.json(REPO/'reports/gara/anchors_2026-09-17/anchors.json')
    slopes = np.array([1/(anchors['anchors'][m]['replicate']-anchors['anchors'][m]['baseline']) for m in FIVE])
    official = []
    for relative in [
        'trial_2026-09-13/status_PNn227rxP3bVByS37W41.json',
        'trial_2026-09-17/status_49Gvtu504clN1mIu8T2V.json',
        'trial_2026-09-17/status_0TbVAwhVTj6UYpaU2v9d.json',
        'trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json',
    ]:
        status = snapshot.json(REPO/'reports/invii'/relative)
        require(status['panel_id'] == anchors['panel_id'] and status['anchor_version'] == anchors['anchor_version'], 'Panel/anchor identity differs')
        published = [status[s] for s in SCORES] + [status['score_mse']]
        near(sum(published)/6, status['score_avg'], 'Official mean-six identity')
        members = {}
        for m, name in zip(FIVE, SCORES):
            a = anchors['anchors'][m]
            reconstructed = (status[m]-a['baseline'])/(a['replicate']-a['baseline'])
            members[m] = {'published': status[name], 'global_affine_reconstruction': reconstructed,
                          'error_reconstruction_minus_published': reconstructed-status[name]}
        reconstructed_avg = (sum(v['global_affine_reconstruction'] for v in members.values())+status['score_mse'])/6
        official.append({'entry_id': status['entry_id'], 'model_name': status['model_name'],
                         'published_score': status['score_avg'], 'reconstructed_score': reconstructed_avg,
                         'reconstruction_error': reconstructed_avg-status['score_avg'], 'members': members})
    run = HERE/'generator_confirmation_r3/confirmation'
    manifest = snapshot.json(run/'run_manifest.json')
    target_manifest = snapshot.json(HERE/'generator_confirmation_r3/target_manifest.json')
    selection = snapshot.json(run/'selection.json')
    require(selection['n_targets'] == 96 and selection['truth'] == 'full' and selection['finished_utc'], 'Wrong/incomplete confirmation')
    targets = manifest['targets']
    require(len(targets) == 96 and len(set(targets)) == 96 and set(targets) == set(target_manifest['confirmation']), 'Wrong target list')
    require(not set(target_manifest['development']) & set(targets), 'Current development overlap')
    all_tables, rows = {}, []
    for arm in ['a1_p0', 'a1p5_p1', 'a1p5_p0p5']:
        for seed in [1, 2, 3]:
            name = f'{arm}_s{seed}'
            t = table(snapshot, run/f'per_pert_{name}.csv', targets)
            raw = snapshot.json(run/f'result_{name}.json')['raw']
            x = np.array([[t.get((target, m), math.nan) for m in FIVE] for target in targets])
            for j, m in enumerate(FIVE):
                near(float(np.nanmean(x[:, j])), raw[m], f'Aggregate mismatch {name}/{m}')
            num = [t[target, 'expr_mse_unbiased_capped'] for target in targets]
            den = [t[target, 'expr_distance_unbiased'] for target in targets]
            require(all(math.isfinite(v) for v in num+den) and sum(den)>0, 'Invalid MSE components')
            near(sum(num)/sum(den), raw[MSE], f'MSE ratio mismatch {name}')
            all_tables[name] = x
            rows.append({'name': name, 'MSE_ratio_of_sums': sum(num)/sum(den),
                         'MSE_mean_of_row_ratios_DIAGNOSTIC_NOT_THE_METRIC': float(np.mean(np.array(num)/np.array(den))),
                         'eligible_per_member': dict(zip(FIVE, np.isfinite(x).sum(0).tolist())),
                         'raw': raw})
    baseline = np.array([all_tables[f'a1_p0_s{s}'] for s in [1, 2, 3]])
    require(np.array_equal(np.isfinite(baseline), np.repeat(np.isfinite(baseline[:1]), 3, axis=0)), 'Baseline eligibility varies by seed')
    draws = np.random.default_rng(20260929).integers(0, 96, (2000, 96))
    # Frequency counts provide an independent reduction from the benchmark's indexing.
    weights = np.array([np.bincount(draw, minlength=96) for draw in draws])
    comparisons = []
    for prefix, registered in zip(['a1p5_p1', 'a1p5_p0p5'], selection['comparisons']):
        candidate = np.array([all_tables[f'{prefix}_s{s}'] for s in [1, 2, 3]])
        require(np.array_equal(np.isfinite(candidate), np.isfinite(baseline)), 'Eligibility changes')
        d = (candidate-baseline)*slopes/6
        avg = np.nanmean(d, axis=0)
        per_seed = np.nanmean(d, axis=1).sum(axis=1)
        denominator = weights @ np.isfinite(avg).astype(int)
        require(np.all(denominator>0), 'Bootstrap empty member')
        boot = ((weights @ np.nan_to_num(avg, nan=0))/denominator).sum(axis=1)
        ci = np.quantile(boot, [.0125, .9875])
        delta = float(np.nanmean(avg, axis=0).sum())
        near(delta, registered['delta_projection'], 'Projection differs')
        for a,b in zip(per_seed, registered['per_seed_delta']):
            near(float(a), b, 'Seed delta differs')
        for a,b in zip(ci, registered['paired_target_bootstrap_interval']):
            near(float(a), b, 'Bootstrap CI differs')
        verdict = bool(delta>=.005 and np.all(per_seed>0) and ci[0]>0)
        require(verdict == registered['passes_confirmation'], 'Gate differs')
        comparisons.append({'arm': prefix, 'delta': delta, 'per_seed': per_seed.tolist(),
                            'ci97p5_frequency_reconstruction': ci.tolist(), 'registered_gate_pass': verdict,
                            'member_contributions': dict(zip(FIVE, np.nanmean(avg,axis=0).tolist()))})
    history = snapshot.json(HERE/'score_bias_dati_r1/historical_overlap.json')
    require(set(history['confirmed_current_target_list']) == set(targets), 'Historical overlap report refers to other targets')
    payload = {'written_utc': datetime.now(timezone.utc).isoformat(),
               'claim_type': 'measured arithmetic from completed reports; not a new score or selection',
               'official_affine_checks': official, 'generator_aggregate_checks': rows,
               'generator_confirmation_reconstruction': comparisons,
               'historical_overlap_from_separate_data_audit': history['overlaps'],
               'historical_limit': history['knowledge_limit'],
               'source_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'inputs': snapshot.hashes()}
    out.mkdir(parents=True)
    with (out/'arithmetic.json').open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'output': str(out/'arithmetic.json'), 'official_reconstruction_errors':
                     {row['entry_id']: row['reconstruction_error'] for row in official},
                     'generator_comparisons': comparisons}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    audit(parser.parse_args().out)
