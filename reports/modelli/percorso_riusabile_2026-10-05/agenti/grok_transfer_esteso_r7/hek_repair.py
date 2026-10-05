"""Recompute only HEK J:A549:f4. The production HEK statistic is not rewritten."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ONLY_SPLIT = 'J:A549:f4'


class RepairBlocked(RuntimeError):
    pass


def _dump(payload):
    def convert(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(type(value).__name__)
    return json.dumps(payload, indent=1, default=convert)


def run(root, params, output):
    import cloud_job
    from estimator_core import estimate_source
    import split_rule
    if params.get('only_split') != ONLY_SPLIT:
        raise RepairBlocked('this package computes only ' + ONLY_SPLIT)
    split = split_rule.Split('J', 'A549', 4)
    if split.name != ONLY_SPLIT:
        raise RepairBlocked('split identity changed')
    unit = params['unit']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    axis = params['axis']
    axis_path = cloud_job.locate(root, axis['relative_path'], 'gene_names.csv')
    if cloud_job.sha256_file(axis_path) != axis['sha256']:
        raise RepairBlocked('axis hash mismatch')
    genes = cloud_job.read_axis(axis_path)
    if len(genes) != int(axis['genes']):
        raise RepairBlocked('axis length mismatch')
    count_path = cloud_job.locate(root, unit['relative_path'], 'count_sum.npz')
    rows_path = cloud_job.locate(root, unit['relative_path'], 'rows.csv')
    mask_path = cloud_job.locate(root, unit['relative_path'], 'mask.npz')
    for path, key in ((count_path, 'count_sum_sha256'), (rows_path, 'rows_sha256'), (mask_path, 'mask_sha256')):
        expected = unit.get(key)
        if expected and cloud_job.sha256_file(path) != expected:
            raise RepairBlocked(path.name + ' hash mismatch')
    rows = pd.read_csv(rows_path)
    counts = np.asarray(np.load(count_path)['value'], dtype=np.float64)
    mask = np.asarray(np.load(mask_path)['value'], dtype=bool)
    if counts.shape != mask.shape or len(rows) != counts.shape[0]:
        raise RepairBlocked('HEK rows, count_sum and mask disagree')
    cloud_job.assert_matrix_budget(counts.shape[0], counts.shape[1], params['ram_budget_bytes'])
    decisions, crosswalk = cloud_job.resolve_rows(
        rows, genes, dict(unit.get('control_labels') or {'NTC': 'non-targeting'}))
    keep, dropped = cloud_job.surviving_positions(rows, decisions, split, [])
    hidden = {part for decision in decisions if decision['kind'] == 'gene'
              for part in decision['components'] if split.target_held(part)}
    if not keep:
        raise RepairBlocked('the split kept no row; controls were not invented')
    subset = rows.reset_index(drop=True).iloc[list(keep)].reset_index(drop=True)
    result = estimate_source(
        subset, counts[list(keep)], mask[list(keep)], genes, unit['transfer_source_id'],
        modality=unit['modality'], held_groups=(split.held_group,), hidden_targets=sorted(hidden),
        crosswalk=crosswalk, control_cache=unit.get('control_cache'))
    saved = {}
    tables = []
    for index, table in enumerate(result['tables']):
        for name in ('shrunk', 'raw', 'se'):
            if name not in table:
                raise RepairBlocked('estimator table lacks ' + name)
            saved[f'{index}_{name}'] = np.asarray(table[name], dtype=np.float32)
        saved[f'{index}_n_cells'] = np.asarray(table['n_cells'])
        tables.append({'name': table['name'], 'targets': table['targets'], 'meta': table['meta']})
    stat_id = 'hek-j-a549-f4'
    folder = output / 'statistics'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (stat_id + '.npz')
    np.savez_compressed(path, **saved)
    if path.stat().st_size > int(params['output_budget_bytes']):
        path.unlink()
        raise RepairBlocked('the one split exceeds the output budget; arrays were not downgraded')
    receipt = {'split': split.name, 'regime': 'J', 'held_group': 'A549', 'fold': 4, 'status': 'derived',
               'statistics_id': stat_id, 'file': 'statistics/' + stat_id + '.npz',
               'arrays': ['shrunk', 'raw', 'se'], 'n_rows_kept': len(keep), 'n_tables': len(tables),
               'dropped_rows': len(dropped), 'claims_complete_training': False,
               'replaces_production': False}
    receipt_dir = output / 'splits' / 'J_A549_f4'
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / 'receipt.json').write_text(_dump(receipt), encoding='utf-8')
    (output / 'effects.json').write_text(_dump({
        'production': False, 'only_split': split.name, 'axis_sha256': axis['sha256'],
        'statistics': [{'id': stat_id, 'file': receipt['file'], 'arrays': receipt['arrays'], 'tables': tables}],
    }), encoding='utf-8')
    (output / 'source_model.json').write_text(_dump({
        'kind': 'split_repair', 'unit': unit['unit'], 'transfer_source_id': unit['transfer_source_id'],
        'line_group': unit['line_group'], 'only_split': split.name, 'replaces_production': False,
        'axis_sha256': axis['sha256'], 'fit_ready': False, 'fit_admitted': False,
    }), encoding='utf-8')
    (output / 'status.json').write_text(_dump({
        'status': 'derived', 'only_split': split.name, 'kind': 'split_repair',
        'claims_complete_training': False, 'fit_ready': False,
    }), encoding='utf-8')


def main():
    params = json.loads(Path('params.json').read_text(encoding='utf-8'))
    run(params.get('input_root', '/kaggle/input'), params, params.get('output_root', '/kaggle/working'))


if __name__ == '__main__':
    main()
