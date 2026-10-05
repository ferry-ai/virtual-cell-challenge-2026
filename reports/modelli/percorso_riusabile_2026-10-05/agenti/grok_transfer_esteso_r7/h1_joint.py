"""Joint H1 train+val count_sum. Rows pool before one shrinkage call. H1 test stays out."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import pool_adapter
import split_rule

LINE = 'H1'
RAM_BUDGET = 6 * 1024 ** 3
OUTPUT_BUDGET = 10 * 1024 ** 3


class JointBlocked(RuntimeError):
    pass


def _dump(payload):
    def convert(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(type(value).__name__)
    return json.dumps(payload, indent=1, default=convert)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def locate(root, relative, name):
    direct = Path(root) / relative / name
    if direct.is_file():
        return direct
    needle = relative.replace('\\', '/')
    matches = [path for path in Path(root).rglob(name) if needle in path.as_posix()]
    if len(matches) != 1:
        raise JointBlocked(needle + '/' + name + ' found ' + str(len(matches)))
    return matches[0]


def _check_hash(path, pin, key):
    expected = pin.get(key)
    if expected and sha256_file(path) != expected:
        raise JointBlocked(path.name + ' hash mismatch for ' + str(pin.get('unit')))


def _genes(root, params):
    if params.get('genes'):
        return [str(gene) for gene in params['genes']]
    axis = params['axis']
    path = locate(root, axis['relative_path'], 'gene_names.csv')
    if sha256_file(path) != axis['sha256']:
        raise JointBlocked('axis hash mismatch')
    frame = pd.read_csv(path)
    column = 'gene_name' if 'gene_name' in frame.columns else frame.columns[0]
    genes = frame[column].astype(str).tolist()
    if len(genes) != int(axis['genes']):
        raise JointBlocked('axis length mismatch')
    return genes


def load_bank(root, pin):
    if pin.get('unit') == 'h1_test':
        raise JointBlocked('H1 test is protected')
    count_path = locate(root, pin['relative_path'], 'count_sum.npz')
    rows_path = locate(root, pin['relative_path'], 'rows.csv')
    mask_path = locate(root, pin['relative_path'], 'mask.npz')
    _check_hash(count_path, pin, 'count_sum_sha256')
    _check_hash(rows_path, pin, 'rows_sha256')
    _check_hash(mask_path, pin, 'mask_sha256')
    rows = pd.read_csv(rows_path, keep_default_na=False)
    if set(rows['line_group'].astype(str)) != {LINE}:
        raise JointBlocked(str(pin.get('unit')) + ' line_group is not only H1')
    blob = ' '.join(rows['study'].astype(str).unique()) if 'study' in rows.columns else ''
    if 'h1_test' in blob:
        raise JointBlocked('H1 test rows are in ' + str(pin.get('unit')))
    counts = np.asarray(np.load(count_path)['value'], dtype=np.float64)
    mask = np.asarray(np.load(mask_path)['value'], dtype=bool)
    if counts.shape != mask.shape or len(rows) != counts.shape[0]:
        raise JointBlocked(str(pin.get('unit')) + ' rows, count_sum and mask disagree')
    if counts.shape[0] * counts.shape[1] * 8 > RAM_BUDGET:
        raise JointBlocked(str(pin.get('unit')) + ' count_sum exceeds the RAM budget')
    return {'unit': pin['unit'], 'rows': rows.reset_index(drop=True), 'counts': counts, 'mask': mask,
            'count_sha256': sha256_file(count_path), 'rows_sha256': sha256_file(rows_path),
            'mask_sha256': sha256_file(mask_path)}


def _panel(params):
    pin = params['panel']
    panel = [str(item) for item in pin['targets']]
    digest = hashlib.sha256('\n'.join(panel).encode('utf-8')).hexdigest()
    if digest != pin['panel_sha256'] or len(panel) != int(pin['n']) or len(panel) != len(set(panel)):
        raise JointBlocked('panel pin mismatch')
    return panel


def classify(target, panel):
    """A panel symbol stays a perturbation id even when it is not an expression column."""
    text = str(target)
    if text in {'NTC', 'non-targeting'}:
        return 'non-targeting'
    if any(mark in text for mark in ('+', ',', ';', '|', '/', ' ')):
        return None
    if text.upper() == 'UNASSIGNED':
        return None
    if text in panel:
        return text
    return 'off_panel'


def keep_positions(bank, split, panel):
    keep = []
    frame = bank['rows']
    for position, row in frame.iterrows():
        if split.regime in ('C', 'J') and str(row['line_group']) == split.held_group:
            continue
        label = classify(row['target'], panel)
        if label is None or label == 'off_panel':
            continue
        if label != 'non-targeting' and not split.row_allowed(LINE, label):
            continue
        keep.append(int(position))
    return keep


def inventory_of(banks, panel):
    unused = []
    seen_unused = set()
    present = set()
    blocked = 0
    panel_set = set(panel)
    for bank in banks:
        for raw in bank['rows']['target'].astype(str):
            label = classify(raw, panel_set)
            if label is None:
                blocked += 1
            elif label == 'off_panel' and raw not in seen_unused:
                seen_unused.add(raw)
                unused.append(raw)
            elif label not in ('non-targeting',):
                present.add(label)
    return {'unused_targets': unused, 'blocked_token_rows': blocked,
            'panel_targets_present': [name for name in panel if name in present]}


def records_for(bank, positions):
    frame = bank['rows']
    grouped = {}
    for position in positions:
        raw = str(frame.loc[position, 'target'])
        mapped = 'non-targeting' if raw in {'NTC', 'non-targeting'} else raw
        donor = str(frame.loc[position, 'donor_or_clone'])
        grouped.setdefault((donor, mapped), []).append(position)
    records = []
    for donor, mapped in sorted(grouped):
        idx = np.asarray(grouped[(donor, mapped)], dtype=int)
        records.append({'donor': donor, 'target': mapped,
                        'n_cells': float(frame.loc[idx, 'n'].to_numpy(dtype=np.float64).sum()),
                        'counts': bank['counts'][idx].sum(axis=0, dtype=np.float64)})
    return records


def intersection(banks, positions_by_unit):
    columns = None
    for bank in banks:
        positions = positions_by_unit[bank['unit']]
        if not positions:
            continue
        mask = bank['mask'][np.asarray(positions, dtype=int)].all(axis=0)
        columns = mask if columns is None else (columns & mask)
    if columns is None or not columns.any():
        raise JointBlocked('mask intersection is empty')
    return columns


def estimate_keep(banks, positions_by_unit, genes, panel):
    columns = intersection(banks, positions_by_unit)
    parts = []
    for bank in banks:
        positions = positions_by_unit[bank['unit']]
        if positions:
            parts.append(records_for(bank, positions))
    pooled, info = pool_adapter.pool_records(parts)
    panel_set = set(panel)
    used = []
    for record in pooled:
        if record['target'] != 'non-targeting' and record['target'] not in panel_set:
            continue
        item = dict(record)
        item['counts'] = np.asarray(record['counts'])[columns]
        used.append(item)
    wanted = [name for name in panel if any(item['target'] == name for item in used)]
    info = dict(info)
    info['n_columns'] = int(columns.sum())
    info['n_panel_targets'] = len(wanted)
    if not wanted:
        empty = {key: np.zeros((0, len(genes)), np.float32) for key in ('shrunk', 'raw', 'se')}
        info['schedule'] = 'no_panel_target'
        return empty, {'targets': [], 'n_cells': np.asarray([])}, info
    subset = [gene for gene, keep in zip(genes, columns) if keep]
    estimated = pool_adapter.estimate_spilled(
        used, subset, wanted, budget_bytes=RAM_BUDGET, condition=None)
    scattered = {key: np.full((len(estimated['targets']), len(genes)), np.nan, np.float32)
                 for key in ('shrunk', 'raw', 'se')}
    for key in scattered:
        scattered[key][:, columns] = np.asarray(estimated[key], dtype=np.float32)
    info['schedule'] = estimated.get('schedule')
    info['compact_bytes'] = estimated.get('compact_bytes')
    return scattered, estimated, info


def _write_stat(folder, stat_id, scattered, estimated):
    path = folder / 'statistics' / (stat_id + '.npz')
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path, **{'0_shrunk': scattered['shrunk'], '0_raw': scattered['raw'], '0_se': scattered['se'],
                 '0_n_cells': np.asarray(estimated['n_cells'])})
    return path


def run(root, params, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    banks_pin = params['banks']
    if [item['unit'] for item in banks_pin] != ['h1_train', 'h1_val']:
        raise JointBlocked('H1 joint banks must be h1_train then h1_val')
    banks = [load_bank(root, pin) for pin in banks_pin]
    genes = _genes(root, params)
    panel = _panel(params)
    panel_set = set(panel)
    if any(bank['counts'].shape[1] != len(genes) for bank in banks):
        raise JointBlocked('count_sum width is not the bound axis')
    splits = split_rule.frozen_splits()
    production_names = [item.name for item in splits if item.regime == 'C' and item.fold is None and item.held_group != LINE]
    production_keeps = {}
    for name in production_names:
        split = next(item for item in splits if item.name == name)
        production_keeps[name] = {bank['unit']: keep_positions(bank, split, panel_set) for bank in banks}
    identities = {tuple((unit, tuple(positions)) for unit, positions in sorted(keep.items()))
                  for keep in production_keeps.values()}
    if len(identities) != 1:
        raise JointBlocked('production keep sets disagree')
    groups = {}
    for split in splits:
        positions = {bank['unit']: keep_positions(bank, split, panel_set) for bank in banks}
        key = tuple((unit, tuple(positions[unit])) for unit in sorted(positions))
        groups.setdefault(key, {'positions': positions, 'splits': []})['splits'].append(split)
    written = 0
    statistics = {}
    blocked = []
    for key, group in groups.items():
        positions = group['positions']
        n_rows = sum(len(item) for item in positions.values())
        if n_rows == 0:
            statistics[key] = {'statistics_id': 'excluded', 'arrays': [], 'n_rows': 0, 'targets': []}
            continue
        n_targets = 0
        present = set()
        for bank in banks:
            frame = bank['rows']
            for position in positions[bank['unit']]:
                label = classify(frame.loc[position, 'target'], panel_set)
                if label not in (None, 'non-targeting', 'off_panel'):
                    present.add(label)
        n_targets = len(present)
        projected = n_targets * len(genes) * 4 * 3
        if n_targets == 0:
            statistics[key] = {'statistics_id': 'no_panel_target', 'arrays': [], 'n_rows': n_rows, 'targets': []}
            continue
        if projected > OUTPUT_BUDGET - written:
            for split in group['splits']:
                blocked.append(split.name)
            continue
        stat_id = hashlib.sha256(repr(key).encode('utf-8')).hexdigest()[:16]
        scattered, estimated, info = estimate_keep(banks, positions, genes, panel)
        path = _write_stat(output, stat_id, scattered, estimated)
        written += path.stat().st_size
        if written > OUTPUT_BUDGET:
            path.unlink()
            for split in group['splits']:
                blocked.append(split.name)
            continue
        statistics[key] = {'statistics_id': stat_id, 'file': 'statistics/' + stat_id + '.npz',
                           'arrays': ['shrunk', 'raw', 'se'], 'n_rows': n_rows,
                           'targets': estimated['targets'], 'info': info}
    receipts = []
    for split in splits:
        positions = {bank['unit']: keep_positions(bank, split, panel_set) for bank in banks}
        key = tuple((unit, tuple(positions[unit])) for unit in sorted(positions))
        stat = statistics.get(key)
        if split.name in blocked or stat is None:
            status = 'blocked_output'
            stat = {}
        elif stat['statistics_id'] == 'excluded':
            status = 'excluded_before_statistics'
        elif stat['statistics_id'] == 'no_panel_target':
            status = 'no_panel_target'
        else:
            status = 'derived'
        receipt = {'split': split.name, 'regime': split.regime, 'held_group': split.held_group,
                   'fold': split.fold, 'status': status, 'statistics_id': stat.get('statistics_id'),
                   'file': stat.get('file'), 'arrays': stat.get('arrays') or [],
                   'n_rows_kept': sum(len(item) for item in positions.values()),
                   'n_tables': 1 if status == 'derived' else 0,
                   'claims_complete_training': False, 'matrix': 'count_sum',
                   'pooled_before_shrink': True}
        folder = output / 'splits' / split.name.replace(':', '_')
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'receipt.json').write_text(_dump(receipt), encoding='utf-8')
        receipts.append(receipt)
    production = [item for item in receipts if item['split'] in production_names]
    if any(item['status'] != 'derived' or item['arrays'] != ['shrunk', 'raw', 'se'] for item in production):
        if any(item['status'] == 'no_panel_target' for item in production):
            status_name = 'blocked_no_panel_targets'
        else:
            status_name = 'blocked_output_budget'
    else:
        status_name = 'derived'
    listed = []
    seen = set()
    for item in statistics.values():
        if item.get('file') and item['statistics_id'] not in seen:
            seen.add(item['statistics_id'])
            listed.append({'id': item['statistics_id'], 'file': item['file'], 'arrays': item['arrays'],
                           'tables': [{'name': 'h1', 'targets': item['targets'],
                                       'meta': {'pooled_before_shrink': True, 'aggregated_after_shrink': False}}]})
    inventory = inventory_of(banks, panel)
    (output / 'effects.json').write_text(_dump({
        'matrix': 'count_sum', 'axis_sha256': params['axis_sha256'], 'n_genes': len(genes),
        'panel_sha256': params['panel']['panel_sha256'], 'panel_n': len(panel),
        'pooled_before_shrink': True, 'statistics': listed,
    }), encoding='utf-8')
    model = {'kind': 'pooled_before_shrink', 'unit': 'h1', 'transfer_source_id': 'h1',
             'line_group': LINE, 'training_vote': False, 'aggregated_after_shrink': False,
             'banks': ['h1_train', 'h1_val'], 'h1_test_included': False,
             'axis_sha256': params['axis_sha256'], 'global_hidden_targets': [],
             'panel_sha256': params['panel']['panel_sha256'], 'panel_n': len(panel),
             'panel_targets_present': inventory['panel_targets_present'],
             'unused_targets': inventory['unused_targets'],
             'blocked_token_rows': inventory['blocked_token_rows'],
             'off_panel_not_in_statistic': True,
             'count_bytes': [int(bank['counts'].nbytes) for bank in banks],
             'bank_hashes': [{key: bank[key] for key in ('unit', 'count_sha256', 'rows_sha256', 'mask_sha256')}
                             for bank in banks]}
    (output / 'source_model.json').write_text(_dump(model), encoding='utf-8')
    (output / 'status.json').write_text(_dump({
        'status': status_name, 'unit': 'h1', 'transfer_source_id': 'h1', 'kind': 'pooled_before_shrink',
        'blocked_output_splits': blocked, 'claims_complete_training': False, 'fit_ready': False,
        'fit_admitted': False, 'n_splits': len(receipts),
    }), encoding='utf-8')
    return status_name


def main():
    params = json.loads(Path('params.json').read_text(encoding='utf-8'))
    if params.get('pseudo_scale') not in (None, 'constant') or params.get('min_expected') not in (None, 1, 1.0):
        raise JointBlocked('refusing a changed estimator contract')
    run(params.get('input_root', '/kaggle/input'), params, params.get('output_root', '/kaggle/working'))


if __name__ == '__main__':
    main()
