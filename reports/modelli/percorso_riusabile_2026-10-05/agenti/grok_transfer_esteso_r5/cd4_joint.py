"""One CD4 condition, all donors, one shrinkage.

Script 98 estimates each culture condition with every donor inside the same
effects_from_pseudobulk call. Shrinkage happens after the donor-weighted mean.
This module compacts saved count_sum banks to that call. It does not estimate
a donor alone and then average already-shrunk effects.
"""
from __future__ import annotations

import gc
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from estimator_core import assert_matrix_budget, effects_from_pseudobulk

SEPARATORS = ('+', ',', ';', '|', '/', ' ')
NOT_A_GENE = {'UNASSIGNED', 'NA', 'NAN', 'NONE', 'NULL'}
CALL_KEYS = ('phi', 'min_control_frac', 'min_cells', 'pseudo', 'pseudo_scale', 'min_expected')


class JointBlocked(ValueError):
    """The condition cannot be estimated without dropping a pinned donor or a rule."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def classify_label(raw, control_labels, verified_control_map=None):
    """Perturbation id from the producer label. Separators are not split.

    A symbol or ENSG that is absent from the expression axis stays a
    perturbation id. UNASSIGNED, a blank and an unverified 'control' are blocked.
    """
    text = str(raw)
    mapped = (control_labels or {}).get(text)
    if text in ('NTC', 'non-targeting') or mapped == 'non-targeting':
        return {'kind': 'control', 'label': 'non-targeting', 'reason': None}
    if text.strip() == '' or text.upper() in NOT_A_GENE:
        return {'kind': 'blocked', 'label': text, 'reason': 'unassigned_or_blank'}
    verified = (verified_control_map or {}).get(text)
    if text == 'control':
        if verified == 'non-targeting':
            return {'kind': 'control', 'label': 'non-targeting', 'reason': 'verified_control_map'}
        return {'kind': 'blocked', 'label': text, 'reason': 'control_token_not_in_verified_source_map'}
    if any(mark in text for mark in SEPARATORS):
        return {'kind': 'blocked', 'label': text, 'reason': 'separator_not_split'}
    return {'kind': 'perturbation', 'label': text, 'reason': None}


def _json_list(raw):
    if isinstance(raw, (list, tuple)):
        return [str(part) for part in raw]
    if isinstance(raw, str) and raw.strip().startswith('['):
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(part) for part in parsed]
    return None


def row_decisions(frame, control_labels, verified_control_map, global_hidden):
    """Classify every row before any count is summed. Hidden labels are removed here."""
    hidden = set(map(str, global_hidden or []))
    decisions = []
    has_components = 'target_components' in frame.columns
    for position, row in frame.reset_index(drop=True).iterrows():
        decision = classify_label(row['target'], control_labels, verified_control_map)
        components = []
        if has_components and decision['kind'] == 'perturbation':
            raw = row['target_components']
            blank = raw is None or (isinstance(raw, float) and np.isnan(raw)) or str(raw).strip() == ''
            if not blank:
                try:
                    components = _json_list(raw)
                except json.JSONDecodeError:
                    components = None
                if components is None:
                    decision = {'kind': 'blocked', 'label': decision['label'],
                                'reason': 'components_present_but_not_a_json_list'}
                    components = []
                elif any(part.strip() == '' or part.upper() in NOT_A_GENE for part in components):
                    decision = {'kind': 'blocked', 'label': decision['label'],
                                'reason': 'opaque_component'}
        if decision['kind'] == 'perturbation' and (
                decision['label'] in hidden or any(part in hidden for part in components)):
            decision = {'kind': 'blocked', 'label': decision['label'],
                        'reason': 'global_hidden_before_statistics'}
        decision = dict(decision)
        decision['row'] = int(position)
        decision['components'] = components
        decisions.append(decision)
    return decisions


def _sum_rows(counts, idx):
    acc = np.zeros(counts.shape[1], dtype=np.float64)
    for start in range(0, len(idx), 256):
        acc += counts[idx[start:start + 256]].sum(axis=0, dtype=np.float64)
    return acc


def compact_kept(counts, frame, decisions):
    """Sum count_sum inside donor x label. Columns are not dropped."""
    donor_column = 'donor_or_clone' if 'donor_or_clone' in frame.columns else 'donor'
    if donor_column not in frame.columns or 'n' not in frame.columns:
        raise JointBlocked('rows need donor_or_clone (or donor) and n')
    donors = frame[donor_column].astype(str).to_numpy()
    n_cells = frame['n'].to_numpy(dtype=np.float64)
    groups = {}
    blocked = []
    for decision in decisions:
        if decision['kind'] == 'blocked':
            blocked.append({'row': decision['row'], 'target': str(frame.iloc[decision['row']]['target']),
                            'reason': decision['reason']})
            continue
        key = (donors[decision['row']], decision['label'])
        groups.setdefault(key, []).append(decision['row'])
    records = []
    matrix = np.zeros((len(groups), counts.shape[1]), dtype=np.float64)
    for row_index, key in enumerate(sorted(groups)):
        idx = np.asarray(groups[key], dtype=int)
        matrix[row_index] = _sum_rows(counts, idx)
        records.append({'donor': key[0], 'target': key[1], 'n_cells': float(n_cells[idx].sum())})
    donors_with_controls = sorted({item['donor'] for item in records if item['target'] == 'non-targeting'})
    donors_without_controls = sorted({item['donor'] for item in records if item['donor'] not in set(donors_with_controls)})
    return matrix, records, {
        'donor_column': donor_column,
        'blocked_rows': blocked,
        'donors_with_controls': donors_with_controls,
        'donors_without_controls': donors_without_controls,
        'n_rows_in': int(len(frame)),
        'n_rows_compact': int(len(records)),
    }


def prepare_bank_frame(frame, genes, condition, control_labels, verified_control_map, global_hidden,
                       line_group_expected='CD4T'):
    """Keep one condition. Extra conditions are listed and stay out of the pool."""
    if 'condition' not in frame.columns or 'target' not in frame.columns:
        raise JointBlocked('rows need condition and target')
    if 'line_group' in frame.columns:
        found = sorted(set(frame['line_group'].astype(str)))
        if found != [line_group_expected]:
            raise JointBlocked('line_group is ' + ','.join(found) + '; expected ' + line_group_expected)
        line_group = found[0]
    else:
        line_group = None
    observed = sorted(set(frame['condition'].astype(str)))
    chosen = frame['condition'].astype(str) == str(condition)
    if not bool(chosen.any()):
        raise JointBlocked('no rows for condition ' + str(condition) + '; observed ' + ','.join(observed))
    kept = frame.loc[chosen].reset_index(drop=True)
    decisions = row_decisions(kept, control_labels, verified_control_map, global_hidden)
    return kept, decisions, {
        'line_group': line_group,
        'line_group_column_absent': line_group is None,
        'conditions_observed': observed,
        'conditions_excluded': [item for item in observed if item != str(condition)],
        'n_rows_condition': int(len(kept)),
    }


def _check_contract(result):
    meta = result['meta']
    if meta.get('min_expected') != 1.0 or 'pseudo_scale' in meta:
        raise JointBlocked('estimator contract was not the corrected t25 call')


def _call(matrix, records, genes, targets, call):
    obs = pd.DataFrame({
        'target': [item['target'] for item in records],
        'donor': [item['donor'] for item in records],
        'condition': 'group',
        'n_cells': [item['n_cells'] for item in records],
    })
    assert_matrix_budget(matrix.shape[0], matrix.shape[1])
    result = effects_from_pseudobulk(matrix, obs, genes, targets=targets, condition='group', **call)
    _check_contract(result)
    return result


def _vector(item, count_of):
    if count_of is not None:
        return np.asarray(count_of(item), dtype=np.float64)
    return np.asarray(item['counts'], dtype=np.float64)


def effects_from_records(records, genes, targets, call, budget, count_of=None):
    """One call when the compact stack fits. Otherwise one call per target.

    A per-target call still contains every donor's controls and that target's
    rows. Targets do not share a shrinkage state, and the control fraction is
    the same pool, so the arrays match one call on the full stack.
    """
    genes = np.asarray(genes).astype(str)
    if not records:
        raise JointBlocked('no compact rows')
    n_genes = int(genes.size)
    probe = _vector(records[0], count_of)
    if len(probe) != n_genes:
        raise JointBlocked('compact width does not match the axis')
    stack_bytes = len(records) * n_genes * 8
    wanted = list(targets)

    def matrix_for(group):
        return np.vstack([_vector(item, count_of) for item in group])

    if stack_bytes <= int(budget):
        result = _call(matrix_for(records), records, genes, wanted, call)
        result['schedule'] = 'one_call'
        result['compact_bytes'] = stack_bytes
        return result
    controls = [item for item in records if item['target'] == 'non-targeting']
    by_target = {}
    for item in records:
        if item['target'] != 'non-targeting':
            by_target.setdefault(item['target'], []).append(item)
    shrunk, raw, se, n_cells, kept = [], [], [], [], []
    control_mean = None
    donors = None
    n_control_cells = None
    for target in wanted:
        group = controls + by_target.get(target, [])
        if not any(item['target'] == target for item in group):
            continue
        result = _call(matrix_for(group), group, genes, [target], call)
        if not result['targets']:
            continue
        if control_mean is None:
            control_mean = np.asarray(result['control_mean'], dtype=np.float64)
            donors = list(result['meta']['donors'])
            n_control_cells = result['meta'].get('n_control_cells')
        elif not np.allclose(control_mean, result['control_mean'], rtol=0, atol=0):
            raise JointBlocked('control pool changed between targets')
        shrunk.append(result['shrunk'][0])
        raw.append(result['raw'][0])
        se.append(result['se'][0])
        n_cells.append(int(result['n_cells'][0]))
        kept.append(target)
    if not kept:
        raise JointBlocked('no measured target; controls were not invented')
    meta = {'condition': 'group', 'donors': donors, 'phi': call['phi'],
            'n_control_cells': n_control_cells, 'min_expected': call['min_expected'],
            'se_model': f"quasi-Poisson phi={call['phi']}, donor-weighted",
            'schedule': 'per_target_equivalent'}
    return {'genes': genes, 'targets': kept, 'shrunk': np.vstack(shrunk), 'raw': np.vstack(raw),
            'se': np.vstack(se), 'n_cells': np.asarray(n_cells), 'control_mean': control_mean,
            'meta': meta, 'schedule': 'per_target_equivalent', 'compact_bytes': stack_bytes}


def to_axis_arrays(result, min_control_frac=1e-6):
    """Match AxisTable.from_source: low-control genes are NaN, not a vote for zero."""
    usable = np.asarray(result['control_mean'], dtype=np.float64) >= min_control_frac
    out = {key: np.full(result[key].shape, np.nan, dtype=np.float32) for key in ('shrunk', 'raw', 'se')}
    for key in out:
        out[key][:, usable] = np.asarray(result[key], dtype=np.float32)[:, usable]
    return out


def assert_mask_policy(counts, mask):
    """A false mask may hide only zeros. Nonzero hidden counts block the bank.

    Columns are not removed: dropping them would change the library size and
    the control fraction.
    """
    mask = np.asarray(mask, dtype=bool)
    if mask.shape == (counts.shape[1],):
        mask = np.broadcast_to(mask, counts.shape)
    if mask.shape != counts.shape:
        raise JointBlocked('mask shape does not match count_sum')
    for start in range(0, counts.shape[0], 256):
        stop = start + 256
        if np.any((counts[start:stop] != 0) & ~mask[start:stop]):
            raise JointBlocked('count_sum is nonzero where mask is false')
    return mask.shape


def locate(root, relative, name):
    direct = Path(root) / relative / name
    if direct.is_file():
        return direct
    needle = str(relative).strip('/').replace('\\', '/')
    matches = [path for path in Path(root).rglob(name) if needle in path.as_posix()]
    if len(matches) != 1:
        raise JointBlocked(name + ' under ' + needle + ': found ' + str(len(matches)))
    return matches[0]


def require_identity(path, expected_sha, expected_bytes):
    if Path(path).stat().st_size != int(expected_bytes) or sha256_file(path) != expected_sha:
        raise JointBlocked('identity mismatch for ' + Path(path).name)
    return Path(path)


def _dump(payload):
    def convert(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(type(value).__name__)
    return json.dumps(payload, indent=1, default=convert)


def read_axis(path):
    frame = pd.read_csv(path)
    if 'gene_name' not in frame.columns:
        raise JointBlocked('gene_names.csv has no gene_name column')
    names = [str(value) for value in frame['gene_name'].tolist()]
    if not names or len(names) != len(set(names)) or any(not name for name in names):
        raise JointBlocked('axis is empty, duplicated or contains a blank name')
    if names == [str(index) for index in range(len(names))]:
        raise JointBlocked('positional column labels are not a gene axis')
    return names


def call_dict(params):
    raw = dict(params['estimator'])
    if set(raw) != set(CALL_KEYS):
        raise JointBlocked('estimator keys are not the t25 call')
    if raw['pseudo_scale'] != 'constant' or float(raw['min_expected']) != 1.0:
        raise JointBlocked('estimator is not the corrected t25 call')
    return {key: raw[key] for key in CALL_KEYS}


def load_compact_bank(root, pin, genes, condition, params, budget):
    """Hash one pinned bank, compact it, and drop the full matrix."""
    count_path = require_identity(locate(root, pin['relative_path'], 'count_sum.npz'),
                                  pin['count_sum_sha256'], pin['count_sum_bytes'])
    if count_path.name != 'count_sum.npz':
        raise JointBlocked('refusing a matrix that is not count_sum')
    rows_path = require_identity(locate(root, pin['relative_path'], 'rows.csv'),
                                 pin['rows_sha256'], pin['rows_bytes'])
    mask_path = require_identity(locate(root, pin['relative_path'], 'mask.npz'),
                                 pin['mask_sha256'], pin['mask_bytes'])
    proportion = count_path.with_name('mean_proportion.npz')
    frame = pd.read_csv(rows_path)
    if pin.get('rows') is not None and len(frame) != int(pin['rows']):
        raise JointBlocked('row count differs from the storage pin')
    kept, decisions, report = prepare_bank_frame(
        frame, genes, condition, params.get('control_labels') or {'NTC': 'non-targeting'},
        params.get('verified_control_map') or {}, params.get('global_hidden_targets') or [],
        params.get('line_group_expected') or 'CD4T')
    mask = np.load(mask_path)['value']
    assert_matrix_budget(mask.shape[0], mask.shape[1], budget)
    if mask.shape[1] != len(genes):
        raise JointBlocked('mask width does not match the bound axis')
    counts = np.asarray(np.load(count_path)['value'], dtype=np.float64)
    if counts.shape != mask.shape:
        raise JointBlocked('count_sum and mask shapes differ')
    if not np.isfinite(counts).all() or (counts < 0).any():
        raise JointBlocked('invalid counts')
    mask_shape = assert_mask_policy(counts, mask)
    del mask
    positions = np.flatnonzero(frame['condition'].astype(str).to_numpy() == str(condition))
    if len(positions) != len(kept):
        raise JointBlocked('condition filter did not match the prepared frame')
    # A single-condition bank is the whole matrix. Slicing it would copy another
    # full count_sum beside the one already under the 6 GiB guard.
    subset = counts if len(positions) == len(counts) else counts[positions]
    matrix, records, compact_report = compact_kept(subset, kept, decisions)
    del counts
    gc.collect()
    report.update(compact_report)
    report.update({'unit': pin['unit'], 'kernel': pin['kernel'], 'relative_path': pin['relative_path'],
                   'version': pin.get('version'), 'receipt_sha256': pin.get('receipt_sha256'),
                   'count_sum_sha256': pin['count_sum_sha256'], 'rows_sha256': pin['rows_sha256'],
                   'mask_sha256': pin['mask_sha256'], 'mask_shape': list(mask_shape),
                   'mean_proportion_present_not_used': proportion.is_file(),
                   'mean_proportion_hashed': False})
    for item in records:
        item['unit'] = pin['unit']
    return matrix, records, report


def attach_counts(records, matrix):
    attached = []
    for index, item in enumerate(records):
        attached.append({**item, 'counts': np.asarray(matrix[index], dtype=np.float64)})
    return attached


class CountMap:
    """Read compact rows back from per-bank float64 files without stacking them."""

    def __init__(self):
        self._open = {}

    def __call__(self, item):
        path = item['file']
        if path not in self._open:
            self._open[path] = np.load(path, mmap_mode='r')
        return np.asarray(self._open[path][int(item['row'])], dtype=np.float64)

    def close(self):
        for array in self._open.values():
            mapped = getattr(array, '_mmap', None)
            if mapped is not None:
                mapped.close()
        self._open.clear()
        gc.collect()


def spill_compact(directory, unit, matrix, records):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (unit + '.npy')
    np.save(path, np.asarray(matrix, dtype=np.float64))
    light = []
    for index, item in enumerate(records):
        light.append({'donor': item['donor'], 'target': item['target'], 'n_cells': item['n_cells'],
                      'unit': item.get('unit'), 'file': str(path), 'row': index})
    return light


def write_condition(output, result, axis_arrays, manifest):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output / 'effects.npz',
        shrunk=axis_arrays['shrunk'], raw=axis_arrays['raw'], se=axis_arrays['se'],
        n_cells=np.asarray(result['n_cells']),
        targets=np.asarray(result['targets']),
        control_mean=np.asarray(result['control_mean'], dtype=np.float64))
    (output / 'manifest.json').write_text(_dump(manifest), encoding='utf-8')
    (output / 'source_model.json').write_text(_dump({
        'kind': 'cd4_condition_joint', 'condition': manifest['condition'],
        'transfer_source_id': 'cd4_' + manifest['condition'],
        'donors': manifest['donors_present'], 'schedule': result['schedule'],
        'aggregated_after_shrink': False,
        'shrink_scope': 'all_donors_one_condition',
        'matrix': 'count_sum', 'effect': 'shrunk',
        'axis_sha256': manifest['axis']['sha256'], 'n_genes': manifest['axis']['n_genes'],
        'n_targets': len(result['targets']),
        'claims_complete_training': False, 'claims_complete_corpus': False, 'fit_admitted': False,
        'loss': None, 'optimizer': None,
    }), encoding='utf-8')
    (output / 'fit_receipt.json').write_text(_dump({
        'kind': 'linear_pseudobulk_fit_receipt', 'condition': manifest['condition'],
        'matrix': 'count_sum', 'effect': 'shrunk', 'loss': None, 'optimizer': None,
        'loss_applicable': False,
        'reason': 'the linear transfer has no gradient loss and no optimizer state',
        'claims_complete_training': False, 'claims_complete_corpus': False, 'fit_admitted': False,
    }), encoding='utf-8')
    (output / 'axis.json').write_text(_dump(manifest['axis']), encoding='utf-8')
    artifacts = []
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.name not in ('checkpoint.json', 'status.json'):
            artifacts.append({'path': path.relative_to(output).as_posix(),
                              'sha256': sha256_file(path), 'bytes': path.stat().st_size})
    (output / 'checkpoint.json').write_text(_dump({
        'condition': manifest['condition'], 'axis_sha256': manifest['axis']['sha256'],
        'code_sha256': manifest.get('code_sha256'), 'files': artifacts,
        'claims_complete_training': False,
    }), encoding='utf-8')


def run_condition(root, output, params):
    """Estimate one condition from every pinned donor bank, or write BLOCKED."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    status = {'kind': 'cd4_condition_joint', 'condition': params.get('condition'),
              'status': 'blocked', 'claims_complete_training': False,
              'claims_complete_corpus': False, 'fit_admitted': False,
              'loss': None, 'optimizer': None}
    try:
        if params.get('claims_complete_training') or params.get('fit_admitted'):
            raise JointBlocked('a condition joint is not the extended fit')
        if params.get('matrix') != 'count_sum':
            raise JointBlocked('matrix is not count_sum')
        call = call_dict(params)
        budget = int(params['ram_budget_bytes'])
        axis_pin = params['axis']
        axis_path = require_identity(locate(root, axis_pin['relative_path'], 'gene_names.csv'),
                                     axis_pin['sha256'], axis_pin['bytes'])
        genes = read_axis(axis_path)
        if len(genes) != int(axis_pin['genes']) or sha256_file(axis_path) != axis_pin['sha256']:
            raise JointBlocked('axis binding does not match the pin')
        actual_code = {name: sha256_file(Path(name)) for name in params['code_sha256']}
        if actual_code != params['code_sha256']:
            raise JointBlocked('code hash mismatch')
        pins = list(params['donors'])
        if len(pins) != 4:
            raise JointBlocked('the joint requires the four pinned donor banks')
        scratch = Path(params['scratch_dir']) if params.get('scratch_dir') else Path(tempfile.mkdtemp(prefix='cd4joint-'))
        mapper = CountMap()
        reports = []
        records = []
        try:
            for pin in pins:
                matrix, compact, report = load_compact_bank(
                    root, pin, genes, params['condition'], params, budget)
                if not compact:
                    raise JointBlocked('pinned bank has no kept rows: ' + pin['unit'])
                assert_matrix_budget(matrix.shape[0], matrix.shape[1], budget)
                records.extend(spill_compact(scratch, pin['unit'], matrix, compact))
                del matrix
                gc.collect()
                reports.append(report)
            present = sorted({item['donor'] for item in records})
            targets = sorted({item['target'] for item in records if item['target'] != 'non-targeting'})
            if not targets:
                raise JointBlocked('no perturbation rows; controls were not invented')
            projected = len(targets) * len(genes) * 4 * 3
            if projected > int(params['output_budget_bytes']):
                raise JointBlocked('uncompressed effects exceed the output budget')
            result = effects_from_records(records, genes, targets, call, budget, count_of=mapper)
        finally:
            mapper.close()
            shutil.rmtree(scratch, ignore_errors=True)
        axis_arrays = to_axis_arrays(result, call['min_control_frac'])
        manifest = {
            'kind': 'cd4_condition_joint', 'condition': params['condition'],
            'expected_donors': [pin['unit'] for pin in pins],
            'used_donors': [pin['unit'] for pin in pins],
            'donors_present': present,
            'banks': reports,
            'schedule': result['schedule'], 'compact_bytes': result['compact_bytes'],
            'aggregated_after_shrink': False,
            'target_order': 'sorted perturbation labels; off-axis symbols and ENSG kept',
            'n_targets': len(result['targets']),
            'blocked_rows': [row for report in reports for row in report['blocked_rows']],
            'donors_without_controls': sorted({donor for report in reports
                                               for donor in report['donors_without_controls']}),
            'axis': {'sha256': axis_pin['sha256'], 'n_genes': len(genes),
                     'first': genes[0], 'last': genes[-1], 'bytes': axis_pin['bytes'],
                     'ordering': 'gene_name CSV row order, zero based official_index'},
            'estimator': call, 'code_sha256': params['code_sha256'],
            'mean_proportion_used_as_effect': False,
            'claims_complete_training': False, 'fit_admitted': False,
            'loss': None, 'optimizer': None,
        }
        write_condition(output, result, axis_arrays, manifest)
        status.update({'status': 'derived', 'schedule': result['schedule'], 'n_targets': len(result['targets']),
                       'n_donors': len(present), 'compact_bytes': result['compact_bytes']})
    except MemoryError as error:
        status.update({'status': 'blocked_ram', 'error': str(error)})
    except (JointBlocked, ValueError, FileNotFoundError, OSError, KeyError) as error:
        status.update({'status': 'blocked', 'error': str(error)})
    (output / 'status.json').write_text(_dump(status), encoding='utf-8')
    return status


def main():
    params = json.loads(Path('params.json').read_text(encoding='utf-8'))
    root = Path(params.get('input_root', '/kaggle/input'))
    output = Path(params.get('output_root', '/kaggle/working/effects')) / params['condition']
    status = run_condition(root, output, params)
    Path('/kaggle/working/job_status.json').write_text(_dump(status), encoding='utf-8')


if __name__ == '__main__':
    main()
