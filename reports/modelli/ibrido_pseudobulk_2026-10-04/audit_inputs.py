"""Read existing evidence to select a starting transfer and inventory aggregate contexts."""
import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
METRICS = ('pds_cosine', 'expr_mse_unbiased_capped_norm', 'de_wilcoxon_lfc_nmae',
           'de_wilcoxon_direction_fidelity_yield_raw', 'de_wilcoxon_direction_reach_raw',
           'de_wilcoxon_sig_jaccard')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    source = ROOT / 'reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04'
    lines = {}
    for line, suffix in {'H1': 'h1_r1', 'HepG2': 'hepg2_r1', 'RPE1': 'rpe1_r1',
                         'Jurkat': 'jurkat_r1', 'K562': 'k562_r2'}.items():
        path = source / f'lettura_{suffix}/bench_v2/bench/bench.json'
        receipt = json.loads((source / f'lettura_{suffix}/fetch_receipt.json').read_text())
        expected = receipt['fetched']['bench_v2/bench/bench.json']['sha256']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        b = json.loads(path.read_text())
        differences = {}
        for metric in METRICS:
            values = [b['results'][f'all@s{k}']['scaled_local'][metric] -
                      b['results'][f'prod@s{k}']['scaled_local'][metric] for k in range(5)]
            differences[metric] = {'mean': statistics.mean(values), 'sd': statistics.stdev(values),
                                   'values': values}
        six = [statistics.mean(differences[m]['values'][k] for m in METRICS) for k in range(5)]
        lines[line] = {'six_mean': statistics.mean(six), 'six_sd': statistics.stdev(six),
                       'members': differences, 'sha256': expected}
    path = a.cube / 'manifest.json'
    manifest = json.loads(path.read_text())
    tables = manifest['tables']
    doc = {'utc': datetime.now(timezone.utc).isoformat(), 'claim_type': 'exploratory_reanalysis',
           'comparison': 'all minus prod without neural correction; t28; paired generator seeds',
           'not_independent_confirmation': True, 'lines': lines,
           'cube_manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'cube_tables': tables, 'groups': sorted(set(v['group'] for v in tables.values())),
           'coverage_complete': False,
           'coverage_note': 'Existing aggregate cube only; donor-resolved CD4 and missing catalogue sources remain open.'}
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)
    print(json.dumps({'all_minus_prod': {k: round(v['six_mean'], 6) for k, v in lines.items()},
                      'tables': len(tables), 'groups': doc['groups']}))


if __name__ == '__main__':
    main()
