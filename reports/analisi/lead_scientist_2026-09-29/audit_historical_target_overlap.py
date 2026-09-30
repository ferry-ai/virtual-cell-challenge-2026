"""Exact overlap of frozen target lists; read only target columns, never scores."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIST = HERE.parents[1] / 'generatore_e_banchi/banco_hepg2_v2_2026-09-26/r1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / 'score_bias_dati_r1/historical_overlap.json'
    if out.exists():
        raise FileExistsError(out)
    current_path = HERE / 'generator_confirmation_r3/target_manifest.json'
    current = json.loads(current_path.read_text())
    bench_path = HIST / 'bench.json'
    bench = json.loads(bench_path.read_text())
    historical = set(bench['targets'])
    current_sets = {k: set(current[k]) for k in ['development', 'confirmation', 'eligible']}
    files = []
    for path in sorted(HIST.glob('per_pert*.csv')):
        # Standard CSV reader parses rows, but metric/value fields are neither used
        # nor emitted. This audit only measures target-list identity.
        with path.open(newline='', encoding='utf-8') as f:
            targets = {r['perturbation'] for r in csv.DictReader(f)}
        files.append({'file': path.name, 'sha256': sha(path), 'targets': len(targets),
                      'same_as_bench_targets': targets == historical,
                      'overlap_confirmation': len(targets & current_sets['confirmation']),
                      'overlap_development': len(targets & current_sets['development'])})
    result = {'claim': 'Target-list audit only, no metric values inspected',
              'current_manifest_sha256': sha(current_path), 'historical_manifest_sha256': sha(bench_path),
              'historical_finished_utc': bench['finished_utc'], 'historical_n_targets': len(historical),
              'historical_args': {k: v for k, v in bench['args'].items() if k in ['seed', 'max_controls', 'min_cells', 'max_targets', 'model', 'effects']},
              'overlaps': {k: {'current': len(v), 'historical_intersection': len(v & historical),
                               'not_previously_in_historical_manifest': sorted(v - historical)}
                           for k, v in current_sets.items()},
              'actual_scored_target_lists': files,
              'confirmed_current_target_list': sorted(current_sets['confirmation']),
              'knowledge_limit': 'Files prove previous execution and availability, not which numeric results a person read before selecting today\u0027s grid.'}
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['confirmed_current_target_list']}))


if __name__ == '__main__':
    main()
