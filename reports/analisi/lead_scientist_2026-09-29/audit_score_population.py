"""Audit population and row separation from manifests; never read metric outcomes."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import statistics

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = Path('C:/Users/ferra/vcc2026-data/processed/rete_contesti_r2')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def describe(ns):
    return {'min': min(ns), 'median': statistics.median(ns), 'max': max(ns), 'sum': sum(ns)}


def main():
    out = HERE / 'score_bias_dati_r1'
    if out.exists():
        raise FileExistsError('Audit output exists')
    sources = []
    def read(relative):
        path = HERE / relative
        sources.append({'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        return load(path)
    generator = read('generator_confirmation_r3/target_manifest.json')
    gd = read('generator_development_r3/target_manifest.json')
    controls = set(generator['control_rows'])
    gen = {'truth': generator['truth'], 'eligible_targets': len(generator['eligible']),
           'development_targets': len(generator['development']), 'confirmation_targets': len(generator['confirmation']),
           'split_overlap': len(set(generator['development']) & set(generator['confirmation'])),
           'control_cells': len(controls), 'response_genes': len(generator['columns']),
           'source_mask': generator['source_mask'], 'preparation_same_across_runs': gd == generator,
           'versions': generator['versions']}
    for split in ['development', 'confirmation']:
        selected = generator[split]
        row_sets = [set(generator['target_rows'][t]) for t in selected]
        gen[split + '_truth_cells'] = describe([len(r) for r in row_sets])
        gen[split + '_overlap_with_controls'] = sum(len(r & controls) for r in row_sets)
        gen[split + '_truth_rows_unique'] = sum(map(len, row_sets)) == len(set().union(*row_sets))
    stack = read('neural/stack_a_scoring_r2/evaluation_manifest.json')
    st = {'development_targets': len(stack['targets']),
          'all_in_generator_development': set(stack['targets']) <= set(generator['development']),
          'overlap_generator_confirmation': len(set(stack['targets']) & set(generator['confirmation'])),
          'truth': stack['truth'], 'pretraining_holdout_verified': stack['pretraining_holdout_verified'],
          'versions': stack['versions']}
    ctx = np.load(DATA / 'row_context.npy', allow_pickle=False)
    target = np.load(DATA / 'row_target.npy', allow_pickle=False)
    with (DATA / 'contexts.csv').open(encoding='utf-8', newline='') as f:
        context_rows = list(csv.DictReader(f))
    folds, all_test, seen_contexts = [], [], set()
    for family in ['k562', 'cd4', 'orion', 'ipsc', 'rpe1']:
        path = f'kaggle_lead_monitor/r6/seed1/neural_seed1_r1/folds/C_{family}_s1/manifest.json'
        manifest = read(path)
        plan = manifest['design']
        tr, refit = set(plan['train']), set(plan['refit'])
        validation = set().union(*(set(v) for v in plan['validation'].values()))
        test = set().union(*(set(v) for v in plan['test'].values()))
        hidden = set(plan['hidden_contexts'])
        test_ctx = set(map(int, ctx[list(test)]))
        all_test += list(test)
        seen_contexts.update(test_ctx)
        folds.append({'family': family, 'regime': manifest['options']['regime'],
                      'train_rows': len(tr), 'refit_rows': len(refit), 'validation_rows': len(validation),
                      'test_rows': len(test), 'test_contexts': len(test_ctx),
                      'test_train_overlap': len(test & tr), 'test_refit_overlap': len(test & refit),
                      'validation_train_overlap': len(validation & tr),
                      'hidden_context_rows_in_train': int(np.isin(ctx[list(tr)], list(hidden)).sum()),
                      'hidden_context_rows_in_refit': int(np.isin(ctx[list(refit)], list(hidden)).sum()),
                      'validation_family': plan['validation_family'],
                      'hidden_targets_count': len(plan['hidden_targets']),
                      'truth_target_is_seen_elsewhere_count': len(set(target[list(test)]) & set(target[list(refit)]))})
    nn_data = read('kaggle_neural_r1/input_metadata/manifest.json')
    nn = {'folds': folds, 'target_context_pairs': len(all_test),
          'unique_targets': len(set(map(int, target[all_test]))), 'contexts': len(seen_contexts),
          'families': len(folds), 'test_rows_unique': len(all_test) == len(set(all_test)),
          'stored_dataset_counts': nn_data['counts'], 'stored_genes_rule': nn_data['stored_genes_rule'],
          'active_test_context_names': [context_rows[c]['context'] for c in sorted(seen_contexts)]}
    result = {'claim': 'Metadata/split audit only; no scores or expression arrays read',
              'generator': gen, 'stack': st, 'neural': nn, 'evidence': sources}
    out.mkdir()
    (out / 'population.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
