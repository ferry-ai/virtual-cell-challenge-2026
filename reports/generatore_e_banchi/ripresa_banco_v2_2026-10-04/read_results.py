"""Verify finished bench receipts and apply the previously frozen diagnostic rule."""
import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MEMBERS = {'PDS': 'pds_cosine', 'MSE': 'expr_mse_unbiased_capped_norm',
           'NMAE': 'de_wilcoxon_lfc_nmae', 'FID': 'de_wilcoxon_direction_fidelity_yield_raw',
           'REACH': 'de_wilcoxon_direction_reach_raw', 'JAC': 'de_wilcoxon_sig_jaccard'}
LINES = {'H1': 'h1_r1', 'HepG2': 'hepg2_r1', 'RPE1': 'rpe1_r1', 'Jurkat': 'jurkat_r1', 'K562': 'k562_r2'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def stats(values):
    assert len(values) == 5 and all(math.isfinite(v) for v in values)
    mean, sd = statistics.mean(values), statistics.stdev(values)
    return {'values': values, 'mean': mean, 'sd': sd,
            'resolved': abs(mean) > 2 * sd / math.sqrt(5)}


def compare(calculated, archived):
    assert calculated['resolved'] == archived['resolved']
    for k in ('mean', 'sd'):
        assert math.isclose(calculated[k], archived[k], rel_tol=1e-10, abs_tol=1e-12), (k, calculated, archived)
    for a, b in zip(calculated['values'], archived['values']):
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)


def line_result(line, suffix):
    folder = HERE / ('lettura_' + suffix)
    receipt = read(folder / 'fetch_receipt.json')
    for name, expected in receipt['fetched'].items():
        path = folder / name
        assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], name
    done = read(folder / 'kernel_done.json')
    assert done['held'] == line and done['versions']['cell-eval2'] == '0.16.0'
    assert set(done['steps']) == {'effects', 'bench_v2'}
    assert all(v['return_code'] == 0 for v in done['steps'].values())
    preflight = read(folder / 'preflight_runtime.json')
    assert preflight['ok'] is True and preflight['scorer_version'] == '0.16.0'
    assert preflight['files'] == len(preflight['inputs']) > 0
    resources = read(folder / 'resources.json')
    assert resources['accelerator'] == 'CPU'
    assert min(resources['available_ram_bytes'], resources['free_disk_bytes']) >= 8 * 2**30
    manifest = read(folder / 'effects/manifest.json')
    assert manifest['held'] == line and manifest['zero_correction_parity'] is True
    assert manifest['leakage_check'] == 'passed'
    bench = read(folder / 'bench_v2/bench/bench.json')
    run = read(folder / 'bench_v2/run.json')
    original = ROOT / 'reports/generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py'
    assert run['code_sha256'] == sha(original)
    assert bench['n_pred'] == 400 and bench['gen_seeds'] == 5
    assert bench['seed'] == 2026 and bench['gen_seed'] == 20260912
    assert bench['emission']['name'] == 't28' and bench['emission']['scale'] == 1.5
    assert bench['emission']['gene_dispersion'] is True
    assert bench['real_sha256'] == manifest['real_sha256']
    assert len(set(bench['targets'])) == len(bench['targets']) == bench['n_targets']
    assert set(bench['targets']) == set(manifest['targets'])
    assert set(bench['arms']) == {'all', 'all_wR', 'prod', 'prod_wR'}
    for arm, evidence in bench['arms'].items():
        assert evidence['sha256'] == manifest['files'][arm]['sha256']
    paired = read(folder / 'bench_v2/paired.json')
    assert paired['n_pred'] == 400 and paired['gen_seeds'] == 5 and paired['emission'] == 't28'
    assert set(paired['pairs']) == {'all_wR:all', 'prod_wR:prod'}
    results = bench['results']
    output = {}
    for pair, archived in paired['pairs'].items():
        candidate, base = pair.split(':')
        delta, raw = {}, {}
        for short, metric in MEMBERS.items():
            delta[short] = stats([results[f'{candidate}@s{k}']['scaled_local'][metric]
                                 - results[f'{base}@s{k}']['scaled_local'][metric] for k in range(5)])
            raw[short] = stats([results[f'{candidate}@s{k}']['raw'][metric]
                               - results[f'{base}@s{k}']['raw'][metric] for k in range(5)])
            compare(delta[short], archived['members'][short])
            compare(raw[short], archived['raw_members'][short])
        six = stats([statistics.mean(v['values'][k] for v in delta.values()) for k in range(5)])
        no_jac = stats([statistics.mean(v['values'][k] for m, v in delta.items() if m != 'JAC') for k in range(5)])
        compare(six, archived['six'])
        compare(no_jac, archived['without_JAC'])
        positive = lambda s: s['resolved'] and s['mean'] > 0
        flags = {'six_resolved_positive': positive(six), 'without_JAC_resolved_positive': positive(no_jac),
                 'PDS_not_resolved_negative': not (delta['PDS']['resolved'] and delta['PDS']['mean'] < 0)}
        output[pair] = {'six': six, 'without_JAC': no_jac, 'members': delta, 'raw_members': raw,
                        'conditions': flags, 'favorable': all(flags.values()),
                        'missing_conditions': [k for k, v in flags.items() if not v]}
    return {'receipt': str((folder / 'fetch_receipt.json').relative_to(ROOT)),
            'receipt_sha256': sha(folder / 'fetch_receipt.json'), 'technical_checks': 'passed',
            'finished_utc': bench['finished_utc'], 'kernel_seconds': done['seconds'],
            'targets': bench['n_targets'], 'genes': bench['genes'], 'control_pool': bench['control_pool'],
            'real_n_conf': bench['real_n_conf'], 'resources': resources,
            'baseline_only_targets': manifest['files']['prod'].get('baseline_only_targets', []),
            'pairs': output}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    lines = {name: line_result(name, suffix) for name, suffix in LINES.items()}
    doc = {'utc': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': sha(HERE / 'PROTOCOLLO.md'),
           'emendment_sha256': sha(HERE / 'EMENDAMENTO_K562.md'),
           'scope': 'Paired local C-lane diagnostic, fixed fits and truth, generator noise only; not VCC score.',
           'lines': lines, 'macro': {}}
    for pair in ('all_wR:all', 'prod_wR:prod'):
        doc['macro'][pair] = {'favorable_lines': [k for k, v in lines.items() if v['pairs'][pair]['favorable']],
                             'mean_six': statistics.mean(v['pairs'][pair]['six']['mean'] for v in lines.values())}
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)
    for name, result in lines.items():
        for pair, v in result['pairs'].items():
            print(f"{name:7} {pair:13} six={v['six']['mean']:+.6f} sd={v['six']['sd']:.6f} "
                  f"noJ={v['without_JAC']['mean']:+.6f} PDS={v['members']['PDS']['mean']:+.6f} "
                  f"favorable={v['favorable']} missing={v['missing_conditions']}")
    print(json.dumps(doc['macro']))


if __name__ == '__main__':
    main()
