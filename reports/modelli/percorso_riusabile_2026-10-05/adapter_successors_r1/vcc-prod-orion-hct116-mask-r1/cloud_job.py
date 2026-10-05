"""Derive count_sum effects for every frozen C/J split. No mean_proportion and no push."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from estimator_core import MissingComponents, assert_matrix_budget, estimate_source
from split_rule import LINE_GROUPS, N_FOLDS, PROVENANCE, REGIMES, SALT, Split, frozen_splits

SEPARATORS = ('+', ',', ';', '|', '/', ' ')
NOT_A_GENE = {'UNASSIGNED', 'UNASSIGNED'.lower(), 'NA', 'NaN', 'nan', 'None', 'NULL', 'null', ''}
ENSG = re.compile(r'^ENSG\d+(?:\.\d+)?$')
POLICY_NAME = 'bound_axis_membership'


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
    needle = str(relative).strip('/').replace('\\', '/')
    matches = [path for path in Path(root).rglob(name) if needle in path.as_posix()]
    if len(matches) != 1:
        raise FileNotFoundError(name + ' under ' + needle + ': found ' + str(len(matches)))
    return matches[0]


def require_identity(path, expected_sha, expected_bytes):
    if path.stat().st_size != int(expected_bytes) or sha256_file(path) != expected_sha:
        raise ValueError('identity mismatch for ' + path.name)
    return path


def code_hashes():
    here = Path(__file__).resolve().parent
    return {name: sha256_file(here / name) for name in ('estimator_core.py', 'cloud_job.py', 'split_rule.py')}


def read_axis(path):
    frame = pd.read_csv(path)
    if 'gene_name' not in frame.columns:
        raise ValueError('gene_names.csv has no gene_name column')
    names = [str(value) for value in frame['gene_name'].tolist()]
    if not names or len(names) != len(set(names)) or any(not name for name in names):
        raise ValueError('axis is empty, duplicated or contains a blank name')
    if names == [str(index) for index in range(len(names))]:
        raise ValueError('positional column labels are not a gene axis')
    return names


def require_splits(spec):
    if spec.get('salt') != SALT or int(spec.get('n_folds', 0)) != N_FOLDS:
        raise ValueError('split spec is not the frozen splits.py contract')
    if list(spec.get('regimes', [])) != list(REGIMES):
        raise ValueError('regimes are not C and J')
    if list(spec.get('line_groups', [])) != list(LINE_GROUPS):
        raise ValueError('line groups differ from registry.py TABLES')
    if spec.get('provenance') != PROVENANCE:
        raise ValueError('split provenance differs')
    return [split for split in frozen_splits() if split.name == 'C:A549']


def classify_token(target, genes, control_labels):
    """A separator-free token is a gene only when the source map puts it on the bound axis."""
    raw = str(target)
    mapped = control_labels.get(raw)
    if raw in ('NTC', 'non-targeting') or mapped == 'non-targeting':
        return {'kind': 'control', 'components': []}
    if raw.strip() == '' or raw.upper() == 'UNASSIGNED' or raw in NOT_A_GENE:
        return {'kind': 'blocked', 'reason': 'unassigned_or_blank_is_not_a_gene', 'components': []}
    if raw == 'control' and mapped != 'non-targeting':
        return {'kind': 'blocked', 'reason': 'control_label_not_in_source_map', 'components': []}
    if any(mark in raw for mark in SEPARATORS):
        return {'kind': 'blocked', 'reason': 'compound_without_source_component_map', 'components': []}
    if ENSG.fullmatch(raw):
        return {'kind': 'blocked', 'reason': 'ensembl_id_not_on_bound_symbol_axis', 'components': []}
    if raw in genes:
        return {'kind': 'gene', 'components': [raw], 'evidence': 'exact_symbol_on_bound_axis'}
    return {'kind': 'blocked', 'reason': 'opaque_token_not_on_bound_axis', 'components': []}


def resolve_rows(rows, genes, control_labels):
    """Return a crosswalk for rows that may enter statistics, and the blocked ones."""
    gene_set = set(genes)
    decisions = []
    crosswalk = {}
    for position, row in rows.reset_index(drop=True).iterrows():
        if 'target_components' in rows.columns and str(row['target']) not in ('NTC', 'non-targeting'):
            raw = row['target_components']
            blank = raw is None or (isinstance(raw, float) and np.isnan(raw)) or str(raw).strip() == ''
            if blank:
                decisions.append({'kind': 'blocked', 'reason': 'missing_components', 'components': []})
                continue
            try:
                from estimator_core import parse_components
                parts = parse_components(raw)
            except (ValueError, json.JSONDecodeError) as error:
                decisions.append({'kind': 'blocked', 'reason': 'unparseable_components:' + str(error),
                                  'components': []})
                continue
            bad = [part for part in parts if part not in gene_set or part.upper() == 'UNASSIGNED' or ENSG.fullmatch(part)]
            if bad:
                decisions.append({'kind': 'blocked', 'reason': 'component_not_on_bound_axis', 'components': parts})
                continue
            crosswalk[str(row['target'])] = parts
            decisions.append({'kind': 'gene', 'components': parts, 'evidence': 'source_target_components'})
            continue
        decision = classify_token(row['target'], gene_set, control_labels)
        if decision['kind'] == 'gene':
            crosswalk[str(row['target'])] = decision['components']
        decisions.append(decision)
    return decisions, crosswalk


def surviving_positions(rows, decisions, split: Split, global_hidden):
    """Exclusions and components, before any statistic."""
    hidden = set(map(str, global_hidden))
    keep, dropped = [], []
    frame = rows.reset_index(drop=True)
    for position, decision in enumerate(decisions):
        row = frame.loc[position]
        group = str(row['line_group'])
        parts = list(decision.get('components') or [])
        if decision['kind'] == 'blocked':
            reason = decision['reason']
        elif split.regime in ('C', 'J') and group == split.held_group:
            reason = 'held_group'
        elif any(part in hidden for part in parts):
            reason = 'global_hidden_component'
        elif decision['kind'] == 'control':
            reason = None
        elif any(split.target_held(part) for part in parts) or not split.row_allowed(group, parts[0]):
            reason = 'hidden_component'
        else:
            reason = None
        if reason:
            dropped.append({'row': int(position), 'reason': reason, 'target': str(row['target']),
                            'line_group': group})
        else:
            keep.append(int(position))
    return keep, dropped


def _slug(name):
    return name.replace(':', '_').replace('/', '_')


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def _dump(payload):
    return json.dumps(payload, indent=1, default=_json_default)


def _resume(output, unit, job):
    """Return the saved status when the checkpoint hashes still match."""
    checkpoint_path = Path(output) / 'checkpoint.json'
    status_path = Path(output) / 'status.json'
    if not checkpoint_path.is_file() or not status_path.is_file():
        return None
    checkpoint = json.loads(checkpoint_path.read_text(encoding='utf-8'))
    if checkpoint.get('unit') != unit.get('unit'):
        return None
    if checkpoint.get('count_sum_sha256') != unit.get('count_sum_sha256'):
        return None
    if checkpoint.get('axis_sha256') != (job.get('axis') or {}).get('sha256'):
        return None
    if checkpoint.get('code_sha256') != job.get('code_sha256'):
        return None
    for item in checkpoint.get('files') or []:
        file_path = Path(output) / item['path']
        if not file_path.is_file() or sha256_file(file_path) != item['sha256']:
            return None
    status = json.loads(status_path.read_text(encoding='utf-8'))
    status['resumed_from_checkpoint'] = True
    status['claims_complete_training'] = False
    return status


def derive_unit(root, output, unit, job):
    """Hash and bind the axis, then estimate each distinct exclusion. A partial pack is not a fit."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    resumed = _resume(output, unit, job)
    if resumed is not None:
        return resumed
    status = {'unit': unit['unit'], 'status': 'blocked', 'transfer_source_id': unit.get('transfer_source_id'),
              'claims_complete_training': False, 'kind': 'technical_preparation'}
    try:
        if job.get('claims_complete_training') or unit.get('claims_complete_training'):
            raise ValueError('a derivation is not the extended fit')
        if job.get('matrix') != 'count_sum':
            raise ValueError('matrix is not count_sum')
        expected_code = job.get('code_sha256') or {}
        actual_code = code_hashes()
        if actual_code != expected_code:
            raise ValueError('code hash mismatch: ' + ','.join(sorted(actual_code)))
        splits = require_splits(job['splits'])
        axis_pin = job['axis']
        axis_path = require_identity(
            locate(root, axis_pin['relative_path'], 'gene_names.csv'),
            axis_pin['sha256'], axis_pin['bytes'])
        genes = read_axis(axis_path)
        if len(genes) != int(axis_pin['genes']) or sha256_file(axis_path) != axis_pin['sha256']:
            raise ValueError('axis binding does not match the pin')
        count_path = require_identity(locate(root, unit['relative_path'], 'count_sum.npz'),
                                      unit['count_sum_sha256'], unit['count_sum_bytes'])
        rows_path = require_identity(locate(root, unit['relative_path'], 'rows.csv'),
                                     unit['rows_sha256'], unit['rows_bytes'])
        mask_path = require_identity(locate(root, unit['relative_path'], 'mask.npz'),
                                     unit['mask_sha256'], unit['mask_bytes'])
        rows = pd.read_csv(rows_path)
        if unit.get('rows') is not None and len(rows) != int(unit['rows']):
            raise ValueError('row count differs from the storage pin')
        groups = sorted(set(rows['line_group'].astype(str)))
        if groups != [unit['line_group']]:
            raise ValueError('line_group is ' + ','.join(groups) + '; expected ' + unit['line_group'])
        mask = np.load(mask_path)['value']
        assert_matrix_budget(mask.shape[0], mask.shape[1], job['ram_budget_bytes'])
        if mask.shape[1] != len(genes):
            raise ValueError('mask width does not match the bound axis')
        counts = np.asarray(np.load(count_path)['value'], dtype=np.float64)
        if counts.shape != mask.shape:
            raise ValueError('count_sum and mask shapes differ')
        controls = dict(unit.get('control_labels') or {'NTC': 'non-targeting'})
        decisions, crosswalk = resolve_rows(rows, genes, controls)
        global_hidden = list(job.get('global_hidden_targets') or [])
        grouped = {}
        split_rows = []
        for split in splits:
            keep, dropped = surviving_positions(rows, decisions, split, global_hidden)
            key = tuple(keep)
            grouped.setdefault(key, {'keep': keep, 'representative': split, 'splits': []})
            grouped[key]['splits'].append((split, dropped))
            split_rows.append(key)
        budget = int(job['output_budget_bytes'])
        written = 0
        statistics = {}
        blocked_output = []
        for key, group in grouped.items():
            if not key:
                statistics[key] = {'statistics_id': 'excluded', 'tables': [], 'arrays': []}
                continue
            projected = len(job['target_panel']) * len(genes) * 4
            arrays = ['shrunk', 'raw', 'se'] if projected * 3 <= budget - written else ['shrunk']
            if projected * len(arrays) > budget - written:
                blocked_output.append(group['representative'].name)
                continue
            subset = rows.reset_index(drop=True).iloc[list(key)].reset_index(drop=True)
            representative = group['representative']
            hidden = set(global_hidden)
            if representative.regime == 'J':
                hidden.update(part for decision in decisions if decision['kind'] == 'gene'
                              for part in decision['components'] if representative.target_held(part))
            try:
                result = estimate_source(
                    subset, counts[list(key)], mask[list(key)], genes, unit['transfer_source_id'],
                    modality=unit['modality'], held_groups=(representative.held_group,),
                    hidden_targets=sorted(hidden), crosswalk=crosswalk,
                    control_cache=unit.get('control_cache'))
            except ValueError as error:
                if 'no biological context produced a measured target' not in str(error):
                    raise
                statistics[key] = {'statistics_id': 'no_measured_target', 'tables': [], 'arrays': [],
                                   'n_rows_estimated': len(key)}
                continue
            stat_id = hashlib.sha256(','.join(str(i) for i in key).encode('utf-8')).hexdigest()[:16]
            pack = output / 'statistics' / (stat_id + '.npz')
            pack.parent.mkdir(parents=True, exist_ok=True)
            saved = {}
            for index, table in enumerate(result['tables']):
                for array_name in arrays:
                    saved[f'{index}_{array_name}'] = np.asarray(table[array_name], dtype=np.float32)
                saved[f'{index}_n_cells'] = np.asarray(table['n_cells'])
            np.savez_compressed(pack, **saved)
            written += pack.stat().st_size
            meta = [{'name': table['name'], 'targets': table['targets'], 'meta': table['meta']}
                    for table in result['tables']]
            statistics[key] = {'statistics_id': stat_id, 'file': 'statistics/' + stat_id + '.npz',
                               'tables': meta, 'arrays': arrays, 'dropped_inside_estimator': result['dropped_rows'],
                               'omitted': result['omitted'], 'n_rows_estimated': len(key)}
        receipts = []
        for split in splits:
            keep, dropped = surviving_positions(rows, decisions, split, global_hidden)
            key = tuple(keep)
            if key not in statistics:
                receipt = {'split': split.name, 'regime': split.regime, 'held_group': split.held_group,
                           'fold': split.fold, 'status': 'blocked_output', 'claims_complete_training': False,
                           'n_rows_kept': len(keep)}
            else:
                stat = statistics[key]
                if not keep:
                    split_status = 'excluded_before_statistics'
                elif stat['statistics_id'] == 'no_measured_target':
                    split_status = 'no_measured_target'
                else:
                    split_status = 'derived'
                receipt = {'split': split.name, 'regime': split.regime, 'held_group': split.held_group,
                           'fold': split.fold, 'status': split_status,
                           'statistics_id': stat['statistics_id'], 'file': stat.get('file'),
                           'arrays': stat.get('arrays', []), 'n_rows_kept': len(keep),
                           'n_tables': len(stat.get('tables') or []),
                           'targets': [target for table in stat.get('tables') or [] for target in table['targets']],
                           'dropped_reasons': {reason: int(count) for reason, count in
                                               pd.Series([item['reason'] for item in dropped]).value_counts().items()}
                           if dropped else {},
                           'estimated_under_split': group_representative_name(grouped[key]),
                           'identical_keep_shared': grouped[key]['representative'].name != split.name,
                           'claims_complete_training': False, 'matrix': 'count_sum',
                           'axis_sha256': axis_pin['sha256'], 'n_genes': len(genes)}
            folder = output / 'splits' / _slug(split.name)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'receipt.json').write_text(_dump(receipt), encoding='utf-8')
            receipts.append(receipt)
        blocked_tokens = [item for item in 
                          ({'target': str(rows.reset_index(drop=True).loc[i, 'target']), 'reason': decisions[i]['reason']}
                           for i in range(len(decisions)) if decisions[i]['kind'] == 'blocked')]
        # unique tokens
        seen = {}
        for item in blocked_tokens:
            seen.setdefault(item['target'], item['reason'])
        effects = {'matrix': 'count_sum', 'axis_sha256': axis_pin['sha256'], 'n_genes': len(genes),
                   'official_index': 'gene_names.csv row order', 'blocked_tokens': seen,
                   'statistics': [{'id': item['statistics_id'], 'file': item.get('file'), 'arrays': item.get('arrays'),
                                   'tables': item.get('tables')}
                                  for item in statistics.values() if item.get('statistics_id') != 'excluded']}
        (output / 'effects.json').write_text(_dump(effects), encoding='utf-8')
        (output / 'axis.json').write_text(_dump({
            'sha256': axis_pin['sha256'], 'genes': len(genes), 'first': genes[0], 'last': genes[-1],
            'dataset': axis_pin.get('dataset'), 'bytes': axis_pin['bytes']}), encoding='utf-8')
        state = 'derived'
        if blocked_output:
            state = 'partial_output_budget'
        status.update({'status': state, 'n_splits': len(receipts),
                       'n_statistics': sum(1 for item in statistics.values() if item.get('file')),
                       'blocked_output_splits': blocked_output, 'blocked_token_count': len(seen),
                       'output_bytes': written, 'claims_complete_training': False,
                       'claims_complete_corpus': False})
        (output / 'fit_receipt.json').write_text(_dump({
            'kind': 'linear_pseudobulk_fit_receipt', 'unit': unit['unit'],
            'transfer_source_id': unit.get('transfer_source_id'), 'line_group': unit.get('line_group'),
            'matrix': 'count_sum', 'effect': 'shrunk', 'recipe': job.get('recipe'),
            'loss': None, 'optimizer': None, 'loss_applicable': False,
            'reason': 't25 linear refit has no gradient loss and no optimizer state',
            'n_statistics': status['n_statistics'], 'output_bytes': written,
            'claims_complete_training': False, 'claims_complete_corpus': False,
        }), encoding='utf-8')
        (output / 'source_model.json').write_text(_dump({
            'kind': 'source_effect_fragment', 'unit': unit['unit'],
            'transfer_source_id': unit.get('transfer_source_id'), 'line_group': unit.get('line_group'),
            'role': unit.get('role', 'transfer'), 'admitted_model': bool(unit.get('admitted_model', True)),
            'exclude_only_when_held': bool(unit.get('exclude_only_when_held', True)),
            'training_vote': unit.get('training_vote'), 'replaces_k562': bool(unit.get('replaces_k562', False)),
            'distinct_study_pending_anchor': bool(unit.get('distinct_study_pending_anchor', False)),
            'matrix': 'count_sum', 'effect': 'shrunk', 'axis_sha256': axis_pin['sha256'],
            'n_genes': len(genes), 'statistics': effects['statistics'], 'recipe': job.get('recipe'),
            'claims_complete_training': False, 'claims_complete_corpus': False,
            'optimizer': None, 'loss': None,
        }), encoding='utf-8')
        artifacts = []
        for path in sorted(output.rglob('*')):
            if path.is_file() and path.name not in ('checkpoint.json', 'status.json'):
                artifacts.append({'path': path.relative_to(output).as_posix(),
                                  'sha256': sha256_file(path), 'bytes': path.stat().st_size})
        (output / 'checkpoint.json').write_text(_dump({
            'unit': unit['unit'], 'count_sum_sha256': unit.get('count_sum_sha256'),
            'axis_sha256': axis_pin['sha256'], 'code_sha256': job.get('code_sha256'),
            'files': artifacts, 'claims_complete_training': False,
        }), encoding='utf-8')
    except MemoryError as error:
        status.update({'status': 'blocked_ram', 'error': str(error)})
    except (MissingComponents, ValueError, FileNotFoundError, OSError, KeyError) as error:
        status.update({'status': 'blocked', 'error': str(error)})
    (output / 'status.json').write_text(_dump(status), encoding='utf-8')
    return status


def group_representative_name(group):
    return group['representative'].name


def validate_pack(output):
    output = Path(output)
    if (output / 'mean_proportion.npz').exists():
        raise ValueError('refusing a pack that contains mean_proportion')
    status = json.loads((output / 'status.json').read_text(encoding='utf-8'))
    if status.get('status') not in ('derived', 'partial_output_budget'):
        raise ValueError('pack is not a derived effect table')
    if status.get('claims_complete_training'):
        raise ValueError('derivation claims the extended fit')
    payload = json.loads((output / 'effects.json').read_text(encoding='utf-8'))
    if payload.get('matrix') != 'count_sum':
        raise ValueError('pack matrix is not count_sum')
    for item in payload.get('statistics') or []:
        if not item.get('file'):
            continue
        loaded = np.load(output / item['file'])
        if 'value' in loaded.files and not any(name.endswith('_shrunk') for name in loaded.files):
            raise ValueError('pack looks like a raw count matrix')
    return status


def main():
    params = json.loads(Path('params.json').read_text(encoding='utf-8'))
    root = Path(params.get('input_root', '/kaggle/input'))
    out = Path(params.get('output_root', '/kaggle/working/effects'))
    statuses = [derive_unit(root, out / unit['unit'], unit, params) for unit in params['units']]
    Path('/kaggle/working/job_status.json').write_text(_dump(statuses), encoding='utf-8')


if __name__ == '__main__':
    main()
