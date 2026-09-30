"""Read-only report of exact A/B baseline CSV differences, including binary ULP."""
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent


def rows(path):
    with path.open(newline='') as stream:
        result = list(csv.DictReader(stream))
    mapped = {(x['perturbation'], x['metric']): x['value'] for x in result}
    assert len(mapped) == len(result)
    return result, mapped


def bits(value):
    return struct.unpack('>Q', struct.pack('>d', value))[0]


def main():
    out = HERE / 'stack_ab_numerical_diagnostic_r1'
    if out.exists():
        raise FileExistsError(out)
    paths = [HERE / name / 'per_pert_transfer.csv' for name in ('stack_a_scoring_r2', 'stack_b_scoring_r1')]
    (ra, a), (rb, b) = [rows(path) for path in paths]
    assert a.keys() == b.keys()
    differences = []
    for key in sorted(a):
        if a[key] != b[key]:
            x, y = float(a[key]), float(b[key])
            differences.append({'target': key[0], 'metric': key[1], 'text_a': a[key], 'text_b': b[key],
                'decimal_b_minus_a': str(Decimal(b[key])-Decimal(a[key])), 'float_b_minus_a': y-x,
                'absolute_difference': abs(y-x), 'ulp_distance': abs(bits(y)-bits(x)),
                'spacing_a': math.ulp(x), 'relative_difference': abs(y-x)/abs(x)})
    comparisons = [json.loads((path.parent / 'pilot_comparison.json').read_text()) for path in paths]
    environments = [json.loads((path.parent / 'evaluation_manifest.json').read_text())['versions'] for path in paths]
    result = {'scope': 'Completed development reports only; no raw counts, outcomes on reserve, or scoring rerun',
        'csv_files': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
        'row_count_each': len(a), 'key_sets_identical': True, 'raw_row_order_identical': ra == rb,
        'different_value_count': len(differences), 'differences': differences,
        'aggregate_transfer_json_exact': comparisons[0]['raw']['transfer'] == comparisons[1]['raw']['transfer'],
        'runtime_versions_exact': environments[0] == environments[1],
        'scorer_config_bytes_exact': (paths[0].parent / 'scorer_config.json').read_bytes() == (paths[1].parent / 'scorer_config.json').read_bytes()}
    out.mkdir()
    with (out / 'csv_difference.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
