"""Production mix by frozen split identity. Does not import vcc2026.

The production statistic of a source is the one file shared by every regime-C
receipt whose held group is not that source's line. A larger ``n_rows_kept``
does not choose it. J receipts and the line-held C receipt are validation.
They are never filled with zero when the statistic is missing. A fragment
whose production arrays omit raw or se is not an exact source and does not vote.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import pool_adapter
import split_rule

REQUIRED_ARRAYS = ('shrunk', 'raw', 'se')
CONDITIONS = ('Rest', 'Stim8hr', 'Stim48hr')


class MixBlocked(ValueError):
    """The mount, the split identity, or the arrays cannot vote."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _dump(payload):
    def convert(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(type(value).__name__)
    return json.dumps(payload, indent=1, default=convert)


def frozen_manifest():
    """The 72 C/J names, bound before any statistics file is chosen."""
    return [{'name': split.name, 'regime': split.regime, 'held_group': split.held_group, 'fold': split.fold}
            for split in split_rule.frozen_splits()]


def assert_frozen_manifest(manifest):
    if list(manifest) != frozen_manifest():
        raise MixBlocked('split manifest is not the frozen C/J list')


class Table:
    """One source on the official axis. Unmeasured entries are NaN."""

    def __init__(self, name, targets, shrunk, raw, se, n_cells, meta=None):
        self.name = name
        self.targets = list(targets)
        self.shrunk = np.asarray(shrunk, dtype=np.float32)
        self.raw = None if raw is None else np.asarray(raw, dtype=np.float32)
        self.se = None if se is None else np.asarray(se, dtype=np.float32)
        self.n_cells = np.asarray(n_cells)
        self.meta = dict(meta or {})

    def index(self):
        return {target: index for index, target in enumerate(self.targets)}

    def common(self, slot='shrunk'):
        rows = self.shrunk if slot == 'shrunk' else self.raw
        n = np.isfinite(rows).sum(axis=0)
        total = np.nansum(rows, axis=0, dtype=np.float64)
        return np.divide(total, n, out=np.zeros(rows.shape[1], dtype=np.float64), where=n > 0)


def mix(tables, targets, *, weights=None, gamma=0.0, reliability_scale=100.0, common=None, slot='shrunk'):
    """Same formula as vcc2026.multisource.mix. Reliability is n_cells, not SE."""
    if not tables:
        raise MixBlocked('mix received no tables')
    weights = weights or {}
    width = tables[0].shrunk.shape[1] if slot == 'shrunk' else tables[0].raw.shape[1]
    num = np.zeros((len(targets), width))
    den = np.zeros((len(targets), width))
    for tab in tables:
        source_weight = float(weights.get(tab.name, 1.0))
        if source_weight <= 0:
            continue
        rows = tab.shrunk if slot == 'shrunk' else tab.raw
        if rows is None:
            raise MixBlocked(tab.name + ' has no ' + slot + ' array')
        centre = None if common is None else common.get(tab.name)
        if centre is None:
            centre = tab.common(slot)
        centre = np.nan_to_num(np.asarray(centre, dtype=np.float64))
        idx = tab.index()
        for i, target in enumerate(targets):
            j = idx.get(target)
            if j is None:
                continue
            row = rows[j].astype(np.float64)
            ok = np.isfinite(row)
            reliability = tab.n_cells[j] / (tab.n_cells[j] + reliability_scale)
            num[i, ok] += source_weight * reliability * (row[ok] - gamma * centre[ok])
            den[i, ok] += source_weight * reliability
    out = np.divide(num, den, out=np.zeros_like(num), where=den > 0)
    return out, den


def _union(tables):
    found = []
    seen = set()
    for tab in tables:
        for target in tab.targets:
            if target not in seen:
                seen.add(target)
                found.append(target)
    return found


def project_table(table, panel):
    """Slice a saved statistic onto the original panel before any centering."""
    if not panel:
        raise MixBlocked('the original panel is required before centering')
    full_bytes = int(table.shrunk.nbytes + table.raw.nbytes + table.se.nbytes)
    projected = pool_adapter.project_rows(
        table.targets, table.shrunk, table.raw, table.se, table.n_cells, panel)
    meta = dict(table.meta)
    meta.update({'projected_to_panel': True, 'aggregated_after_shrink': False,
                 'n_targets_full': projected['n_targets_full'],
                 'n_targets_on_panel': len(projected['targets']),
                 'unused_targets': projected['unused_targets'],
                 'panel_targets_missing': projected['panel_targets_missing'],
                 'input_array_bytes': full_bytes})
    return Table(table.name, projected['targets'], projected['shrunk'], projected['raw'],
                 projected['se'], projected['n_cells'], meta)


def _require_projected(tables):
    missing = [tab.name for tab in tables if not tab.meta.get('projected_to_panel')]
    if missing:
        raise MixBlocked('centering before the original panel projection: ' + ','.join(missing))


def condition_mix(tables, panel, reliability_scale=100.0):
    """Gamma 0 on the original panel. Raw and shrunk stay apart."""
    _require_projected(tables)
    if any(tab.name.startswith('cd4_half') for tab in tables):
        raise MixBlocked('cd4_half tables are diagnostic and stay out of the mix')
    if any(tab.raw is None or tab.se is None for tab in tables):
        raise MixBlocked('se or raw absent; refusing an inexact mix')
    targets = list(panel)
    eff, weight = mix(tables, targets, gamma=0.0, reliability_scale=reliability_scale, slot='shrunk')
    raw_tables = [Table(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells, tab.meta) for tab in tables]
    eff_raw, weight_raw = mix(raw_tables, targets, gamma=0.0, reliability_scale=reliability_scale, slot='shrunk')
    have = (weight > 0).any(axis=1)
    order = [target for target, keep in zip(targets, have) if keep]
    cells = []
    for target in order:
        total = 0.0
        for tab in tables:
            if target in tab.index():
                total += float(tab.n_cells[tab.index()[target]])
        cells.append(total)
    mixed = np.where(weight > 0, eff, np.nan).astype(np.float32)[have]
    mixed_raw = np.where(weight_raw > 0, eff_raw, np.nan).astype(np.float32)[have]
    return Table('cd4_mix', order, mixed, mixed_raw, np.full_like(mixed, np.nan), np.asarray(cells), {
        'from': [tab.name for tab in tables],
        'how': 'reliability-weighted mean, gamma 0; shrunk and raw mixed separately',
        'gamma': 0.0, 'reliability_scale': reliability_scale,
        'aggregated_after_shrink': False, 'projected_to_panel': True,
        'panel_order': True,
    })


def final_mix(tables, panel, *, gamma=1.0, reliability_scale=100.0, weight=1.0):
    """One gamma-1 mix on the original panel. Amplitude and cis are not applied here."""
    _require_projected(tables)
    names = [tab.name for tab in tables]
    if len(names) != len(set(names)):
        raise MixBlocked('a source would vote twice: ' + ','.join(names))
    widths = {tab.shrunk.shape[1] for tab in tables}
    if len(widths) != 1:
        raise MixBlocked('sources do not share an axis width')
    targets = list(panel)
    weights = {name: weight for name in names}
    shrunk_eff, shrunk_w = mix(tables, targets, weights=weights, gamma=gamma,
                               reliability_scale=reliability_scale, slot='shrunk')
    missing_raw = [tab.name for tab in tables if tab.raw is None]
    if missing_raw:
        raise MixBlocked('raw absent on ' + ','.join(missing_raw))
    raw_tables = [Table(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells, tab.meta) for tab in tables]
    raw_eff, raw_w = mix(raw_tables, targets, weights=weights, gamma=gamma,
                         reliability_scale=reliability_scale, slot='shrunk')
    return {
        'targets': targets,
        'shrunk': shrunk_eff.astype(np.float64),
        'shrunk_weight': shrunk_w,
        'raw': raw_eff.astype(np.float64),
        'raw_weight': raw_w,
        'shrunk_measured': np.where(shrunk_w > 0, shrunk_eff, np.nan).astype(np.float32),
        'raw_measured': np.where(raw_w > 0, raw_eff, np.nan).astype(np.float32),
        'sources': names,
        'gamma': gamma,
        'reliability_scale': reliability_scale,
        'weight': weight,
        'source_weights': weights,
        'amplitude_applied': False,
        'cis_applied': False,
        'effects_scale_applied': False,
    }


def _load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def find_source_model(root, slug):
    root = Path(root)
    name = slug.split('/')[-1]
    matches = []
    base = root / name
    if base.is_dir():
        matches.extend(base.rglob('source_model.json'))
    if not matches:
        matches = [path for path in root.rglob('source_model.json') if name in path.as_posix()]
    return matches


def locate_output(root, slug):
    matches = find_source_model(root, slug)
    if len(matches) != 1:
        raise MixBlocked(slug + ' source_model.json found ' + str(len(matches)))
    return matches[0].parent


def _receipts(output):
    folder = output / 'splits'
    if not folder.is_dir():
        raise MixBlocked('splits directory missing in ' + str(output))
    found = []
    for path in sorted(folder.glob('*/receipt.json')):
        receipt = _load_json(path)
        receipt['_path'] = path.relative_to(output).as_posix()
        found.append(receipt)
    return found


def joint_validation_vote(split):
    """The full CD4 joint did not drop held groups or J targets. It is not a validation effect."""
    if split['held_group'] == 'CD4T' or split['regime'] == 'J':
        return {'vote': False, 'reason': 'production_joint_not_reused_as_validation', 'contribution': 'absent'}
    if split['regime'] == 'C':
        return {'vote': True, 'reason': 'c_split_does_not_hold_cd4t', 'contribution': 'full_joint'}
    raise MixBlocked('unknown regime ' + str(split.get('regime')))


def select_production(output, line_group, manifest):
    """Choose the production file by split identity. ``n_rows_kept`` is only a consistency check."""
    output = Path(output)
    receipts = _receipts(output)
    by_split = {}
    for item in receipts:
        name = item.get('split')
        if name in by_split:
            raise MixBlocked('duplicate receipt for ' + str(name))
        by_split[name] = item
    manifest_names = [item['name'] for item in manifest]
    if len(manifest_names) != len(set(manifest_names)):
        raise MixBlocked('duplicate name in the bound split manifest')
    production_names = [item['name'] for item in manifest
                        if item['regime'] == 'C' and item['fold'] is None and item['held_group'] != line_group]
    if not production_names:
        raise MixBlocked('the bound manifest has no production split for ' + line_group)
    chosen = []
    for name in production_names:
        item = by_split.get(name)
        if item is None or item.get('status') != 'derived' or not item.get('statistics_id') or not item.get('file'):
            raise MixBlocked('production split ' + name + ' is not a derived statistic')
        chosen.append(item)
    identities = {(item['statistics_id'], item['file'], tuple(item.get('arrays') or []), int(item['n_rows_kept']))
                  for item in chosen}
    if len(identities) != 1:
        raise MixBlocked('production identity conflict: ' + ','.join(sorted(item[0] for item in identities)))
    statistics_id, filename, arrays, n_rows = next(iter(identities))
    if any(name not in arrays for name in REQUIRED_ARRAYS):
        raise MixBlocked('se or raw absent; refusing an inexact source model: ' + ','.join(arrays))
    effects_path = output / 'effects.json'
    if not effects_path.is_file():
        raise MixBlocked('effects.json missing')
    effects = _load_json(effects_path)
    listed = [item for item in effects.get('statistics') or [] if item.get('id') == statistics_id]
    if len(listed) != 1 or listed[0].get('file') != filename:
        raise MixBlocked('effects.json does not list production statistics ' + statistics_id)
    spec = listed[0]
    if any(name not in (spec.get('arrays') or []) for name in REQUIRED_ARRAYS):
        raise MixBlocked('effects.json production arrays are inexact')
    pack = output / spec['file']
    if not pack.is_file():
        raise MixBlocked('statistics file missing: ' + spec['file'])
    loaded = np.load(pack)
    meta_tables = list(spec.get('tables') or [])
    indices = sorted({int(key.split('_', 1)[0]) for key in loaded.files if key[:1].isdigit()})
    if indices != list(range(len(meta_tables))):
        raise MixBlocked('statistics tables and arrays disagree: ' + spec['file'])
    tables = []
    for index, meta in enumerate(meta_tables):
        for array_name in REQUIRED_ARRAYS:
            key = f'{index}_{array_name}'
            if key not in loaded.files:
                raise MixBlocked('se or raw absent in ' + spec['file'])
        shrunk = np.asarray(loaded[f'{index}_shrunk'], dtype=np.float32)
        raw = np.asarray(loaded[f'{index}_raw'], dtype=np.float32)
        se = np.asarray(loaded[f'{index}_se'], dtype=np.float32)
        n_cells = np.asarray(loaded[f'{index}_n_cells'])
        if shrunk.shape[0] != len(meta['targets']) or len(n_cells) != len(meta['targets']):
            raise MixBlocked('table length mismatch in ' + meta['name'])
        tables.append(Table(meta['name'], meta['targets'], shrunk, raw, se, n_cells, meta.get('meta') or {}))
    ignored = []
    for item in receipts:
        if item.get('status') == 'derived' and item.get('n_rows_kept') is not None:
            ignored.append(int(item['n_rows_kept']))
    bindings = []
    for spec_split in manifest:
        name = spec_split['name']
        if spec_split['held_group'] == line_group:
            bindings.append({**spec_split, 'vote': False, 'reason': 'excluded_when_held', 'contribution': 'absent'})
            continue
        item = by_split.get(name)
        if item is None or item.get('status') != 'derived' or not item.get('file'):
            bindings.append({**spec_split, 'vote': False, 'reason': 'validation_statistic_missing',
                             'status': None if item is None else item.get('status'), 'contribution': 'absent',
                             'repairable': item is not None and item.get('status') == 'blocked_output'})
            continue
        if any(array_name not in (item.get('arrays') or []) for array_name in REQUIRED_ARRAYS):
            bindings.append({**spec_split, 'vote': False, 'reason': 'validation_arrays_incomplete',
                             'contribution': 'absent'})
            continue
        bindings.append({**spec_split, 'vote': True, 'statistics_id': item['statistics_id'], 'file': item['file'],
                         'reason': 'split_receipt', 'contribution': 'split_statistic'})
    return {'statistics_id': statistics_id, 'file': spec['file'], 'sha256': sha256_file(pack),
            'bytes': pack.stat().st_size, 'n_tables': len(tables), 'arrays': list(arrays),
            'tables': tables, 'n_rows_kept': n_rows,
            'max_n_rows_kept_ignored': max(ignored) if ignored else None,
            'selection_rule': 'split_identity', 'validation': bindings,
            'axis_sha256': effects.get('axis_sha256'),
            'blocked_tokens': effects.get('blocked_tokens') or {}}


def collapse_fragment(selection, unit, reliability_scale=100.0):
    """One pre-shrink table keeps its SE. Several already-shrunk tables are not a script-98 pool."""
    del reliability_scale
    tables = selection['tables']
    if len(tables) != 1:
        raise MixBlocked(unit + ' has ' + str(len(tables)) + ' tables; refusing a post-shrink average')
    tab = tables[0]
    if tab.se is None or tab.raw is None:
        raise MixBlocked('se or raw absent on ' + unit)
    return Table(unit, tab.targets, tab.shrunk, tab.raw, tab.se, tab.n_cells, {
        'unit': unit, 'from_table': tab.name, 'aggregated_after_shrink': False,
        'how': 'single table; SE kept; no post-shrink average',
    })


def one_vote(tables, reliability_scale=100.0):
    """Each transfer_source_id votes once. H1 is one pooled table, not two shrunk fragments."""
    del reliability_scale
    groups = {}
    order = []
    for tab in tables:
        source_id = tab.meta['transfer_source_id']
        if source_id not in groups:
            order.append(source_id)
            groups[source_id] = []
        groups[source_id].append(tab)
    voted = []
    for source_id in order:
        items = groups[source_id]
        if len(items) != 1:
            raise MixBlocked('source would vote twice: ' + source_id)
        items[0].name = source_id
        voted.append(items[0])
    return voted


def load_split_repair(output, item):
    """One held-out statistic. It never replaces the production identity."""
    output = Path(output)
    receipts = _receipts(output)
    wanted = item.get('split')
    matched = [receipt for receipt in receipts if receipt.get('split') == wanted]
    if len(matched) != 1:
        raise MixBlocked('repair receipts for ' + str(wanted) + ': ' + str(len(matched)))
    receipt = matched[0]
    if receipt.get('status') != 'derived' or not receipt.get('file'):
        raise MixBlocked('repair split is not derived')
    if any(name not in (receipt.get('arrays') or []) for name in REQUIRED_ARRAYS):
        raise MixBlocked('repair arrays are inexact')
    pack = output / receipt['file']
    if not pack.is_file():
        raise MixBlocked('repair statistic missing')
    loaded = np.load(pack)
    if any('0_' + name not in loaded.files for name in REQUIRED_ARRAYS):
        raise MixBlocked('repair file lacks raw, shrunk or se')
    return {**receipt, 'slug': item['slug'], 'unit': item.get('repairs_unit')}


def apply_split_repairs(validation, repairs, unit):
    by_split = {}
    for repair in repairs:
        if repair.get('unit') != unit:
            continue
        by_split[repair['split']] = repair
    rebound = []
    for binding in validation:
        repair = by_split.get(binding['name']) if binding.get('repairable') else None
        if repair is None:
            rebound.append(binding)
            continue
        rebound.append({**binding, 'vote': True, 'statistics_id': repair['statistics_id'],
                        'file': repair['file'], 'reason': 'repaired_split_statistic',
                        'contribution': 'split_statistic', 'repair_slug': repair['slug']})
    return rebound


def load_joint(output):
    output = Path(output)
    model = _load_json(output / 'source_model.json')
    if model.get('kind') != 'cd4_condition_joint':
        raise MixBlocked('not a CD4 condition joint: ' + str(output))
    if model.get('global_hidden_targets'):
        raise MixBlocked('joint global_hidden_targets is not empty')
    status = _load_json(output / 'status.json')
    if status.get('status') != 'derived':
        raise MixBlocked('joint status is ' + str(status.get('status')))
    pack = np.load(output / 'effects.npz')
    for key in ('shrunk', 'raw', 'se', 'n_cells', 'targets'):
        if key not in pack.files:
            raise MixBlocked('joint effects.npz lacks ' + key)
    targets = [str(item) for item in pack['targets'].tolist()]
    table = Table(model['transfer_source_id'], targets, pack['shrunk'], pack['raw'], pack['se'],
                  pack['n_cells'], {'aggregated_after_shrink': False, 'kind': model['kind'],
                                    'from': [model['transfer_source_id']]})
    return table, {'file': 'effects.npz', 'sha256': sha256_file(output / 'effects.npz'),
                   'bytes': (output / 'effects.npz').stat().st_size,
                   'axis_sha256': model.get('axis_sha256'), 'condition': model.get('condition'),
                   'schedule': model.get('schedule'), 'n_targets': len(targets),
                   'global_hidden_targets': model.get('global_hidden_targets') or []}


def _fragment_status(output, admission):
    status = _load_json(output / 'status.json')
    state = status.get('status')
    if admission == 'required' and state != 'derived':
        raise MixBlocked('required source status is ' + str(state))
    if state not in ('derived', 'partial_output_budget'):
        raise MixBlocked('source status is ' + str(state))
    return status


def _retained_bytes(tables):
    total = 0
    for table in tables:
        total += int(table.shrunk.nbytes) + int(table.raw.nbytes)
        if table.se is not None:
            total += int(table.se.nbytes)
    return total


def build_incremental(root, expected, manifest, *, axis_sha256, panel, ram_budget_bytes,
                      gamma=1.0, reliability_scale=100.0, weight=1.0):
    """Bind the split manifest first. A missing required mount writes no model."""
    assert_frozen_manifest(manifest)
    root = Path(root)
    missing = []
    pending = []
    refused = []
    joints = []
    fragments = []
    repairs = []
    for item in expected:
        if item.get('role') == 'split_repair':
            try:
                output = locate_output(root, item['slug'])
                repairs.append(load_split_repair(output, item))
            except MixBlocked as error:
                pending.append({'slug': item['slug'], 'role': item['role'], 'error': str(error)})
            continue
        try:
            output = locate_output(root, item['slug'])
        except MixBlocked as error:
            record = {'slug': item['slug'], 'role': item['role'], 'error': str(error)}
            if item['admission'] == 'required':
                missing.append(record)
            else:
                pending.append(record)
            continue
        if item['role'] == 'cd4_condition':
            try:
                table, provenance = load_joint(output)
            except MixBlocked as error:
                missing.append({'slug': item['slug'], 'role': item['role'], 'error': str(error)})
                continue
            if table.name != 'cd4_' + item['condition']:
                raise MixBlocked('joint name is ' + table.name + ' for ' + item['condition'])
            if provenance['axis_sha256'] != axis_sha256:
                raise MixBlocked('joint axis hash mismatch for ' + item['condition'])
            table = project_table(table, panel)
            provenance.update({'slug': item['slug'], 'role': 'cd4_condition',
                               'input_array_bytes': table.meta['input_array_bytes'],
                               'n_targets_full': table.meta['n_targets_full'],
                               'n_targets_on_panel': table.meta['n_targets_on_panel'],
                               'unused_target_count': len(table.meta['unused_targets'])})
            joints.append((item['condition'], table, provenance))
            continue
        try:
            state = _fragment_status(output, item['admission'])
            model = _load_json(output / 'source_model.json')
            if model.get('line_group') != item['line_group']:
                raise MixBlocked('line_group mismatch for ' + item['slug'])
            if model.get('transfer_source_id') != item['transfer_source_id']:
                raise MixBlocked('transfer_source_id mismatch for ' + item['slug'])
            selection = select_production(output, item['line_group'], manifest)
            if selection['axis_sha256'] != axis_sha256:
                raise MixBlocked('fragment axis hash mismatch for ' + item['slug'])
            table = project_table(collapse_fragment(selection, item['unit'], reliability_scale), panel)
        except MixBlocked as error:
            record = {'slug': item['slug'], 'role': item['role'], 'error': str(error)}
            if item['admission'] == 'required':
                return {'status': 'blocked_production_identity', 'missing': missing, 'pending': pending,
                        'refused': refused + [record], 'model': None, 'cd4_mix': None,
                        'cd4_gap': None, 'fragments': [], 'joints': [item[2] for item in joints]}
            refused.append(record)
            continue
        table.meta['transfer_source_id'] = item['transfer_source_id']
        table.meta['training_vote'] = model.get('training_vote')
        table.meta['unit'] = item['unit']
        table.meta['line_group'] = item['line_group']
        provenance = {'slug': item['slug'], 'role': item['role'], 'unit': item['unit'],
                      'transfer_source_id': item['transfer_source_id'], 'line_group': item['line_group'],
                      'statistics_id': selection['statistics_id'], 'file': selection['file'],
                      'sha256': selection['sha256'], 'n_tables': selection['n_tables'],
                      'n_rows_kept': selection['n_rows_kept'],
                      'max_n_rows_kept_ignored': selection['max_n_rows_kept_ignored'],
                      'selection_rule': 'split_identity', 'arrays': selection['arrays'],
                      'axis_sha256': selection['axis_sha256'],
                      'source_status': state.get('status'),
                      'blocked_output_splits': state.get('blocked_output_splits') or [],
                      'validation': apply_split_repairs(selection['validation'], repairs, item['unit']),
                      'aggregated_after_shrink': False,
                      'n_targets_full': table.meta['n_targets_full'],
                      'n_targets_on_panel': table.meta['n_targets_on_panel'],
                      'unused_target_count': len(table.meta['unused_targets']),
                      'input_array_bytes': table.meta['input_array_bytes']}
        fragments.append((table, provenance))
    if missing:
        return {'status': 'blocked_missing_mount', 'missing': missing, 'pending': pending, 'refused': refused,
                'model': None, 'cd4_mix': None, 'cd4_gap': 'cd4_mix not built',
                'fragments': [item[1] for item in fragments], 'joints': [item[2] for item in joints]}
    by_condition = {condition: table for condition, table, _ in joints}
    if [condition for condition in CONDITIONS if condition not in by_condition]:
        return {'status': 'blocked_missing_mount', 'missing': missing, 'pending': pending, 'refused': refused,
                'model': None, 'cd4_mix': None,
                'cd4_gap': 'cd4_mix not built; missing ' + ','.join(
                    condition for condition in CONDITIONS if condition not in by_condition),
                'fragments': [item[1] for item in fragments], 'joints': [item[2] for item in joints]}
    cd4 = condition_mix([by_condition[condition] for condition in CONDITIONS], panel, reliability_scale)
    cd4.meta['transfer_source_id'] = 'cd4_mix'
    sources = one_vote([table for table, _ in fragments], reliability_scale)
    sources = [cd4] + sources
    retained = _retained_bytes(sources + [by_condition[condition] for condition in CONDITIONS])
    if retained > int(ram_budget_bytes):
        return {'status': 'blocked_ram', 'missing': missing, 'pending': pending, 'refused': refused,
                'model': None, 'cd4_mix': None, 'cd4_gap': None,
                'retained_bytes': retained, 'ram_budget_bytes': int(ram_budget_bytes),
                'fragments': [item[1] for item in fragments], 'joints': [item[2] for item in joints]}
    model = final_mix(sources, panel, gamma=gamma, reliability_scale=reliability_scale, weight=weight)
    return {'status': 'mixed_accepted_gate', 'missing': [], 'pending': pending, 'refused': refused,
            'cd4_gap': None, 'cd4_mix': cd4, 'model': model, 'sources': sources,
            'joint_tables': [by_condition[condition] for condition in CONDITIONS],
            'fragments': [item[1] for item in fragments], 'joints': [item[2] for item in joints]}


def _cache_array(folder, table):
    meta = dict(table.meta)
    meta.pop('validation', None)
    payload = {'targets': np.asarray(table.targets), 'shrunk': table.shrunk, 'raw': table.raw,
               'se': table.se, 'n_cells': table.n_cells, 'meta': np.array(json.dumps(meta))}
    np.savez_compressed(folder / (table.name + '.npz'), **payload)


def _planned_bytes(model, sources):
    total = model['shrunk_measured'].nbytes + model['raw_measured'].nbytes
    total += np.asarray(model['shrunk_weight']).nbytes + np.asarray(model['raw_weight']).nbytes
    for table in sources:
        total += table.shrunk.nbytes + table.raw.nbytes + table.se.nbytes
    return int(total)


def write_release(output, built, manifest, *, output_budget_bytes, catalogue_gaps):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    common = {
        'kind': 'incremental_partial_extended_release',
        'fit_admitted': False, 'fit_ready': False,
        'all_compatible_admitted': False, 'claims_complete_training': False,
        'claims_complete_corpus': False, 'is_final_d053_catalogue': False,
        'training_ready': False, 'loss': None, 'optimizer': None,
        'catalogue_gaps': catalogue_gaps,
    }
    if built['status'] != 'mixed_accepted_gate' or built['model'] is None:
        (output / 'status.json').write_text(_dump({
            **common, 'status': built['status'], 'missing': built['missing'], 'pending': built['pending'],
            'refused': built['refused'], 'cd4_gap': built['cd4_gap'], 'usable_export': False,
        }), encoding='utf-8')
        return
    model = built['model']
    planned = _planned_bytes(model, built['sources'])
    if planned > output_budget_bytes:
        (output / 'status.json').write_text(_dump({
            **common, 'status': 'blocked_output_budget', 'planned_bytes': planned, 'usable_export': False,
        }), encoding='utf-8')
        return
    np.savez_compressed(
        output / 'effects.npz',
        targets=np.asarray(model['targets']),
        shrunk=model['shrunk_measured'], raw=model['raw_measured'],
        shrunk_weight=np.asarray(model['shrunk_weight'], dtype=np.float64),
        raw_weight=np.asarray(model['raw_weight'], dtype=np.float64))
    cache = output / 'cache'
    cache.mkdir(exist_ok=True)
    for table in built['sources']:
        _cache_array(cache, table)
    for table in built.get('joint_tables') or []:
        _cache_array(cache, table)
    inventory = {}
    for table in list(built['sources']) + list(built.get('joint_tables') or []):
        inventory[table.name] = {'n_targets_on_panel': len(table.targets),
                                 'n_targets_full': table.meta.get('n_targets_full'),
                                 'unused_targets': table.meta.get('unused_targets') or [],
                                 'panel_targets_missing': table.meta.get('panel_targets_missing') or []}
    (output / 'panel_inventory.json').write_text(_dump(inventory), encoding='utf-8')
    (output / 'manifest.json').write_text(_dump(manifest), encoding='utf-8')
    voted = list(model['sources'])
    usable = True
    (output / 'source_model.json').write_text(_dump({
        **common, 'status': 'mixed_accepted_gate', 'sources': voted,
        'admitted_partial': voted, 'pending': built['pending'], 'refused': built['refused'],
        'gamma': model['gamma'], 'reliability_scale': model['reliability_scale'],
        'weight': model['weight'], 'source_weights': model['source_weights'],
        'amplitude_applied': False, 'cis_applied': False, 'effects_scale_applied': False,
        'effect': 'shrunk', 'selection_rule': 'split_identity',
        'usable_export': usable,
        'reason': 'partial extended release; a file on disk is not fit_ready',
    }), encoding='utf-8')
    (output / 'fit_receipt.json').write_text(_dump({
        'kind': 'linear_pseudobulk_fit_receipt', 'loss': None, 'optimizer': None,
        'loss_applicable': False,
        'reason': 'the linear transfer has no gradient loss and no optimizer state',
        **common, 'usable_export': usable, 'sources': voted,
    }), encoding='utf-8')
    artifacts = [{'path': path.relative_to(output).as_posix(), 'sha256': sha256_file(path),
                  'bytes': path.stat().st_size}
                 for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'checkpoint.json']
    (output / 'checkpoint.json').write_text(_dump({'files': artifacts, 'claims_complete_training': False,
                                                   'selection_rule': 'split_identity'}), encoding='utf-8')
    (output / 'status.json').write_text(_dump({
        **common, 'status': 'mixed_accepted_gate', 'n_sources': len(voted),
        'n_targets': len(model['targets']), 'usable_export': usable,
        'admitted_partial': voted, 'pending': built['pending'], 'refused': built['refused'],
    }), encoding='utf-8')


def _validation_document(manifest_splits, built):
    cd4 = []
    for split in manifest_splits:
        vote = joint_validation_vote(split)
        cd4.append({**split, **vote})
    sources = {}
    for item in built['fragments']:
        sources[item['unit']] = item['validation']
    return {'selection_rule': 'split_identity', 'cd4': cd4, 'sources': sources,
            'missing_contribution_is': 'absent', 'missing_contribution_is_not': 0}


def main():
    params = json.loads(Path('params.json').read_text(encoding='utf-8'))
    if 'pseudo_scale' in (params.get('final_mix') or {}):
        raise MixBlocked('pseudo_scale is not a mix field')
    manifest = params['split_manifest']
    panel_pin = params['panel']
    panel = [str(item) for item in panel_pin['targets']]
    digest = hashlib.sha256('\n'.join(panel).encode('utf-8')).hexdigest()
    if digest != panel_pin['panel_sha256'] or len(panel) != int(panel_pin['n']) or len(panel) != len(set(panel)):
        raise MixBlocked('panel pin mismatch')
    built = build_incremental(
        Path(params.get('input_root', '/kaggle/input')), params['expected'], manifest,
        axis_sha256=params['axis']['sha256'], panel=panel,
        ram_budget_bytes=int(params['ram_budget_bytes']),
        gamma=params['final_mix']['gamma'],
        reliability_scale=params['final_mix']['reliability_scale'], weight=params['final_mix']['weight'])
    document = {
        'kind': 'incremental_partial_extended_release',
        'expected': [{key: item[key] for key in item if key != 'split_manifest'} for item in params['expected']],
        'pending_mounts': built['pending'], 'refused': built['refused'], 'missing_mounts': built['missing'],
        'cd4_gap': built['cd4_gap'], 'joints': built['joints'],
        'fragments': [{key: value for key, value in item.items() if key != 'validation'} for item in built['fragments']],
        'final_mix': params['final_mix'], 'axis': params.get('axis'), 'cis': params.get('cis'),
        'emission': params.get('emission'), 'storage_sha256': params.get('storage_sha256'),
        'catalogue_gaps': params.get('catalogue_gaps') or [],
        'training_ready': False, 'fit_admitted': False, 'fit_ready': False,
        'all_compatible_admitted': False, 'claims_complete_training': False,
        'claims_complete_corpus': False, 'loss': None, 'optimizer': None,
        'k562_essential_replaces_k562': False,
        'stage100_reads': 'cache/<voted source>.npz',
        'stage100_does_not_read': 'effects.npz',
        'amplitude_applied': False, 'cis_applied': False, 'effects_scale_applied': False,
    }
    if built['status'] == 'mixed_accepted_gate':
        document['sources_in_final_mix'] = built['model']['sources']
        document['source_weights'] = built['model']['source_weights']
        document['cd4_mix_from'] = built['cd4_mix'].meta['from']
        document['validation'] = _validation_document(manifest, built)
    output = Path(params.get('output_root', '/kaggle/working/model'))
    write_release(output, built, document, output_budget_bytes=int(params['output_budget_bytes']),
                  catalogue_gaps=params.get('catalogue_gaps') or [])
    if built['status'] == 'mixed_accepted_gate':
        # The condition tables are the CD4 parts. Their SE stays in the joint mount.
        # Saving them again would copy matrices that are already the mounted inputs.
        (output / 'cache_contract.json').write_text(_dump({
            'format': 'scripts/98 save_table keys targets, shrunk, raw, se, n_cells, meta',
            'effect': 'shrunk', 'amplitude_applied': False, 'cis_applied': False,
            'effects_scale_applied': False,
            'next': 'scripts/100_build_context_effects.py reads cache, applies amplitude 1.576 and cis once',
            'then': 'scripts/45_generate_prediction.py read_effects applies effects_scale 1.5 once',
            'do_not_pass_effects_npz_as_a_source': True,
            'voted_sources': built['model']['sources'],
        }), encoding='utf-8')


if __name__ == '__main__':
    main()
