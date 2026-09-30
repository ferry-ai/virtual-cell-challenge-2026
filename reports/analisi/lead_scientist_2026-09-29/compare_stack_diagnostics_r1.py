"""Compare every frozen pilot diagnostic; this is not a score or cell equality test."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
REFERENCE = HERE / 'kaggle_stack_inputs_r1/reference_diagnostics_r2'
EXPECTED = ['CCDC130', 'NRBP1', 'MLLT6', 'WBP11', 'RPL36A', 'MBTPS1',
            'RPL41', 'COG6', 'EEF2', 'DCTN1', 'HAUS8', 'SETD1A']
FIELDS = {'shared_genes', 'shared_lfc_rms', 'baseline_mass_preserved_outside_shared',
          'total_mass_relative_error', 'target', 'source_cells'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(reference, current):
    rows = []
    for index, target in enumerate(EXPECTED):
        name = f'diagnostic_{index:02d}.json'
        old_path, new_path = reference / name, current / name
        old, new = json.loads(old_path.read_text()), json.loads(new_path.read_text())
        if set(old) != FIELDS or set(new) != FIELDS:
            raise ValueError(f'Diagnostic schema differs: {name}')
        if old['target'] != target or new['target'] != target:
            raise ValueError(f'Diagnostic target order differs: {name}')
        differences = {}
        for field in sorted(FIELDS):
            a, b = old[field], new[field]
            item = {'reference': a, 'kaggle': b, 'exact': a == b}
            if type(a) in {int, float} and type(b) in {int, float}:
                if not math.isfinite(a) or not math.isfinite(b):
                    raise ValueError(f'Nonfinite diagnostic: {name}/{field}')
                item['delta'] = b - a
                if a:
                    item['relative_delta'] = (b - a) / abs(a)
            differences[field] = item
        rows.append({'target': target, 'reference_sha256': sha(old_path),
                     'kaggle_sha256': sha(new_path), 'semantic_exact': old == new,
                     'fields': differences})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prediction', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    rows = compare(REFERENCE, args.prediction)
    ref_path = HERE / 'neural/stack_runtime_measurement_r2/inference_manifest.json'
    new_path = args.prediction / 'inference_manifest.json'
    old, new = json.loads(ref_path.read_text()), json.loads(new_path.read_text())
    keys = ['bundle_sha256', 'adapter_sha256', 'checkpoint_sha256', 'genelist_sha256',
            'shared_genes', 'model_genes', 'batch_size', 'rng_note', 'versions']
    provenance = {key: {'reference': old[key], 'kaggle': new[key], 'exact': old[key] == new[key]}
                  for key in keys}
    result = {'claim': 'Descriptive comparison of all 12 diagnostic JSONs; no cell parity or quality claim',
              'targets': 12, 'diagnostics_semantically_exact': all(r['semantic_exact'] for r in rows),
              'provenance_fields': provenance, 'diagnostics': rows,
              'reference_manifest_sha256': sha(ref_path), 'kaggle_manifest_sha256': sha(new_path),
              'quality_score_computed': False, 'cell_arrays_compared': False}
    args.out.mkdir(parents=True)
    with (args.out / 'comparison.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'targets': 12, 'diagnostics_semantically_exact': result['diagnostics_semantically_exact'],
                      'provenance_all_exact': all(x['exact'] for x in provenance.values()),
                      'quality_score_computed': False, 'cell_arrays_compared': False}))


if __name__ == '__main__':
    main()
