"""Original source mix: gamma 0 inside CD4, gamma 1 across sources.

mix() is the same formula as vcc2026.multisource.mix. The kernel copy does not
import vcc2026. Condition tables are mixed at gamma 0, raw and shrunk apart,
which is script 98's cd4_mix. The saved model then mixes sources at gamma 1
and reliability 100. An r4 fragment contributes one vote after every BIO table
in the selected statistics file has been read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


class MixBlocked(ValueError):
    """An expected input is missing or would be counted twice."""


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


class Table:
    """One source on the official axis. Unmeasured entries are NaN, never a vote for zero."""

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
    """Reliability-weighted mean of ``slot - gamma * common``.

    This is vcc2026.multisource.mix, including the default reliability of 100.
    Where no source measured a pair the effect is 0 and the weight is 0.
    """
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


def condition_mix(tables, reliability_scale=100.0):
    """Script 98 cd4_mix: gamma 0, raw and shrunk mixed separately.

    Targets with no positive weight are dropped. A mix of fewer than the three
    culture conditions is not named cd4_mix; the caller decides that.
    """
    if any(tab.name.startswith('cd4_half') for tab in tables):
        raise MixBlocked('cd4_half tables are diagnostic and stay out of cd4_mix')
    targets = _union(tables)
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
        'how': 'reliability-weighted mean of the conditions, gamma 0; shrunk and raw mixed separately',
        'gamma': 0.0, 'reliability_scale': reliability_scale,
        'aggregated_after_shrink': False,
    })


def final_mix(tables, *, gamma=1.0, reliability_scale=100.0, weight=1.0):
    """Gamma-1 mix across sources. Raw and shrunk stay separate. Amplitude is not applied."""
    names = [tab.name for tab in tables]
    if len(names) != len(set(names)):
        raise MixBlocked('a source would vote twice: ' + ','.join(names))
    widths = {tab.shrunk.shape[1] for tab in tables}
    if len(widths) != 1:
        raise MixBlocked('sources do not share an axis width')
    targets = sorted(_union(tables))
    weights = {name: weight for name in names}
    shrunk_eff, shrunk_w = mix(tables, targets, weights=weights, gamma=gamma,
                               reliability_scale=reliability_scale, slot='shrunk')
    raw_tables = []
    missing_raw = []
    for tab in tables:
        if tab.raw is None:
            missing_raw.append(tab.name)
            continue
        raw_tables.append(Table(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells, tab.meta))
    if raw_tables:
        raw_eff, raw_w = mix(raw_tables, targets, weights=weights, gamma=gamma,
                             reliability_scale=reliability_scale, slot='shrunk')
    else:
        raw_eff = np.zeros_like(shrunk_eff)
        raw_w = np.zeros_like(shrunk_w)
    return {
        'targets': targets,
        'shrunk': shrunk_eff.astype(np.float64),
        'shrunk_weight': shrunk_w,
        'raw': raw_eff.astype(np.float64),
        'raw_weight': raw_w,
        'shrunk_measured': np.where(shrunk_w > 0, shrunk_eff, np.nan).astype(np.float32),
        'raw_measured': np.where(raw_w > 0, raw_eff, np.nan).astype(np.float32),
        'sources': names,
        'raw_not_in_fragment': missing_raw,
        'gamma': gamma,
        'reliability_scale': reliability_scale,
        'weight': weight,
        'amplitude_applied': False,
    }


def _load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def find_source_model(root, slug):
    root = Path(root)
    name = slug.split('/')[-1]
    direct = [root / name]
    matches = []
    for base in direct:
        if base.is_dir():
            matches.extend(base.rglob('source_model.json'))
    if not matches:
        matches = [path for path in root.rglob('source_model.json') if name in path.as_posix()]
    return matches


def select_fragment(output):
    """Use the derived statistics file with the most kept rows, and every BIO table in it."""
    output = Path(output)
    effects_path = output / 'effects.json'
    if not effects_path.is_file():
        raise MixBlocked('effects.json missing in ' + str(output))
    effects = _load_json(effects_path)
    receipts = []
    for path in sorted((output / 'splits').glob('*/receipt.json')) if (output / 'splits').is_dir() else []:
        receipt = _load_json(path)
        receipt['_path'] = path.relative_to(output).as_posix()
        receipts.append(receipt)
    derived = [item for item in receipts if item.get('status') == 'derived' and item.get('file')]
    if not derived:
        raise MixBlocked('no derived split receipt in ' + str(output))
    maximum = max(int(item['n_rows_kept']) for item in derived)
    chosen_ids = {item['statistics_id'] for item in derived if int(item['n_rows_kept']) == maximum}
    if len(chosen_ids) != 1:
        raise MixBlocked('ambiguous statistics at n_rows_kept ' + str(maximum) + ': ' + ','.join(sorted(chosen_ids)))
    chosen_id = next(iter(chosen_ids))
    listed = [item for item in effects.get('statistics') or [] if item.get('id') == chosen_id]
    if len(listed) != 1 or not listed[0].get('file'):
        raise MixBlocked('effects.json does not list statistics ' + chosen_id)
    spec = listed[0]
    pack = output / spec['file']
    if not pack.is_file():
        raise MixBlocked('statistics file missing: ' + spec['file'])
    loaded = np.load(pack)
    tables = []
    meta_tables = list(spec.get('tables') or [])
    indices = sorted({int(key.split('_', 1)[0]) for key in loaded.files if key[:1].isdigit()})
    if indices != list(range(len(meta_tables))):
        raise MixBlocked('statistics tables and arrays disagree: ' + spec['file'])
    arrays = list(spec.get('arrays') or [])
    has_raw = 'raw' in arrays
    for index, meta in enumerate(meta_tables):
        shrunk = np.asarray(loaded[f'{index}_shrunk'], dtype=np.float32)
        raw = np.asarray(loaded[f'{index}_raw'], dtype=np.float32) if has_raw else None
        se = np.asarray(loaded[f'{index}_se'], dtype=np.float32) if f'{index}_se' in loaded.files else None
        n_cells = np.asarray(loaded[f'{index}_n_cells'])
        if shrunk.shape[0] != len(meta['targets']) or len(n_cells) != len(meta['targets']):
            raise MixBlocked('table length mismatch in ' + meta['name'])
        tables.append(Table(meta['name'], meta['targets'], shrunk, raw, se, n_cells, meta.get('meta') or {}))
    others = []
    for item in receipts:
        if item.get('statistics_id') == chosen_id and item.get('status') == 'derived':
            continue
        others.append({key: item.get(key) for key in
                       ('split', 'regime', 'held_group', 'fold', 'status', 'statistics_id', 'file', 'n_rows_kept')})
    return {'statistics_id': chosen_id, 'file': spec['file'], 'sha256': sha256_file(pack),
            'bytes': pack.stat().st_size, 'n_tables': len(tables), 'arrays': arrays,
            'has_raw': has_raw, 'tables': tables, 'not_used_fold': others,
            'n_rows_kept': maximum, 'axis_sha256': effects.get('axis_sha256'),
            'blocked_tokens': effects.get('blocked_tokens') or {}}


def collapse_fragment(selection, source_id, reliability_scale=100.0):
    """Every BIO table is read, then the source receives one gamma-0 vote.

    r4 already shrank each BIO group, so this collapse is aggregated_after_shrink.
    It is not the script-98 condition=None pool. Raw is not copied from shrunk.
    """
    tables = selection['tables']
    if not tables:
        raise MixBlocked(source_id + ' has no BIO table')
    if not selection['has_raw']:
        raw_note = 'raw_not_in_fragment'
        # Gamma-0 mix needs a slot. Build shrunk-only by giving mix a raw of NaN
        # that is never selected: collapse shrunk, leave raw unset.
        targets = _union(tables)
        eff, weight = mix(tables, targets, gamma=0.0, reliability_scale=reliability_scale, slot='shrunk')
        have = (weight > 0).any(axis=1)
        order = [target for target, keep in zip(targets, have) if keep]
        cells = [sum(float(tab.n_cells[tab.index()[target]]) for tab in tables if target in tab.index())
                 for target in order]
        mixed = np.where(weight > 0, eff, np.nan).astype(np.float32)[have]
        table = Table(source_id, order, mixed, None, np.full_like(mixed, np.nan), np.asarray(cells), {
            'from': [tab.name for tab in tables], 'raw': raw_note,
            'aggregated_after_shrink': True, 'gamma': 0.0,
            'how': 'reliability-weighted mean of BIO tables already shrunk by the fragment',
        })
        return table
    renamed = [Table(tab.name, tab.targets, tab.shrunk, tab.raw, tab.se, tab.n_cells, tab.meta) for tab in tables]
    mixed = condition_mix(renamed, reliability_scale=reliability_scale)
    mixed.name = source_id
    mixed.meta['aggregated_after_shrink'] = True
    mixed.meta['how'] = 'reliability-weighted mean of BIO tables already shrunk by the fragment; raw and shrunk separate'
    mixed.meta['from'] = [tab.name for tab in tables]
    return mixed


def load_joint(output):
    output = Path(output)
    model = _load_json(output / 'source_model.json')
    if model.get('kind') != 'cd4_condition_joint':
        raise MixBlocked('not a CD4 condition joint: ' + str(output))
    if model.get('status', 'derived') == 'blocked':
        raise MixBlocked('joint status is blocked')
    status_path = output / 'status.json'
    if status_path.is_file():
        status = _load_json(status_path)
        if status.get('status') != 'derived':
            raise MixBlocked('joint status is ' + str(status.get('status')))
    pack = np.load(output / 'effects.npz')
    targets = [str(item) for item in pack['targets'].tolist()]
    table = Table(model['transfer_source_id'], targets, pack['shrunk'], pack['raw'], pack['se'],
                  pack['n_cells'], {'aggregated_after_shrink': False, 'kind': model['kind']})
    return table, {'file': 'effects.npz', 'sha256': sha256_file(output / 'effects.npz'),
                   'bytes': (output / 'effects.npz').stat().st_size,
                   'axis_sha256': model.get('axis_sha256'), 'condition': model.get('condition'),
                   'schedule': model.get('schedule'), 'n_targets': len(targets)}


def locate_output(root, slug):
    matches = find_source_model(root, slug)
    if len(matches) != 1:
        raise MixBlocked(slug + ' source_model.json found ' + str(len(matches)))
    return matches[0].parent


def build_incremental(root, expected, *, gamma=1.0, reliability_scale=100.0, weight=1.0,
                      required_conditions=('Rest', 'Stim8hr', 'Stim48hr')):
    """Mount cloud outputs. cd4_mix exists only when all three condition joints exist."""
    root = Path(root)
    used = []
    missing = []
    joints = []
    fragments = []
    for item in expected:
        try:
            output = locate_output(root, item['slug'])
        except MixBlocked as error:
            missing.append({'slug': item['slug'], 'role': item['role'], 'error': str(error)})
            continue
        if item['role'] == 'cd4_condition':
            table, provenance = load_joint(output)
            if table.name != 'cd4_' + item['condition']:
                raise MixBlocked('joint name is ' + table.name + ' for ' + item['condition'])
            provenance.update({'slug': item['slug'], 'role': 'cd4_condition'})
            joints.append((item['condition'], table, provenance))
        elif item['role'] == 'fragment':
            selection = select_fragment(output)
            table = collapse_fragment(selection, item['transfer_source_id'], reliability_scale)
            provenance = {'slug': item['slug'], 'role': 'fragment',
                          'transfer_source_id': item['transfer_source_id'],
                          'statistics_id': selection['statistics_id'], 'file': selection['file'],
                          'sha256': selection['sha256'], 'n_tables': selection['n_tables'],
                          'n_rows_kept': selection['n_rows_kept'], 'not_used_fold': selection['not_used_fold'],
                          'has_raw': selection['has_raw'], 'blocked_tokens': selection['blocked_tokens'],
                          'axis_sha256': selection['axis_sha256'],
                          'aggregated_after_shrink': True}
            fragments.append((table, provenance))
        else:
            raise MixBlocked('unknown role ' + item['role'])
        used.append(item['slug'])
    expected_conditions = list(required_conditions)
    found_conditions = [condition for condition, _, _ in joints]
    if any(slug['role'] == 'cd4_condition' and slug['slug'] not in used for slug in expected):
        cd4 = None
        cd4_gap = 'cd4_mix not built; a condition joint is missing'
    elif found_conditions != [condition for condition in expected_conditions if any(c == condition for c, _, _ in joints)]:
        cd4 = None
        cd4_gap = 'cd4_mix not built'
    else:
        by_condition = {condition: table for condition, table, _ in joints}
        if [condition for condition in expected_conditions if condition not in by_condition]:
            cd4 = None
            cd4_gap = 'cd4_mix not built; missing ' + ','.join(
                condition for condition in expected_conditions if condition not in by_condition)
        elif len(by_condition) != len(expected_conditions):
            cd4 = None
            cd4_gap = 'cd4_mix not built from a partial condition set'
        else:
            ordered = [by_condition[condition] for condition in expected_conditions]
            cd4 = condition_mix(ordered, reliability_scale=reliability_scale)
            cd4_gap = None
    if missing or cd4 is None:
        return {'status': 'blocked', 'missing': missing, 'cd4_mix': None, 'cd4_gap': cd4_gap,
                'used': used, 'fragments': [item[1] for item in fragments],
                'joints': [item[2] for item in joints], 'model': None}
    sources = [cd4] + [table for table, _ in fragments]
    model = final_mix(sources, gamma=gamma, reliability_scale=reliability_scale, weight=weight)
    return {'status': 'mixed', 'missing': [], 'cd4_gap': None, 'cd4_mix': cd4, 'model': model,
            'sources': sources, 'used': used, 'fragments': [item[1] for item in fragments],
            'joints': [item[2] for item in joints]}


def write_release(output, built, manifest):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if built['status'] != 'mixed':
        (output / 'status.json').write_text(_dump({
            'kind': 'incremental_extended_release', 'status': 'blocked',
            'missing': built['missing'], 'cd4_gap': built['cd4_gap'],
            'used': built['used'], 'fit_admitted': False,
            'claims_complete_training': False, 'claims_complete_corpus': False,
            'loss': None, 'optimizer': None,
        }), encoding='utf-8')
        return
    model = built['model']
    np.savez_compressed(
        output / 'effects.npz',
        targets=np.asarray(model['targets']),
        shrunk=model['shrunk_measured'], raw=model['raw_measured'],
        shrunk_weight=np.asarray(model['shrunk_weight'], dtype=np.float64),
        raw_weight=np.asarray(model['raw_weight'], dtype=np.float64))
    for table in built['sources']:
        folder = output / 'sources'
        folder.mkdir(exist_ok=True)
        payload = {'targets': np.asarray(table.targets), 'shrunk': table.shrunk, 'n_cells': table.n_cells}
        if table.raw is not None:
            payload['raw'] = table.raw
        np.savez_compressed(folder / (table.name + '.npz'), **payload)
    (output / 'manifest.json').write_text(_dump(manifest), encoding='utf-8')
    (output / 'source_model.json').write_text(_dump({
        'kind': 'incremental_extended_release',
        'sources': model['sources'], 'gamma': model['gamma'],
        'reliability_scale': model['reliability_scale'], 'weight': model['weight'],
        'amplitude_applied': False, 'effect': 'shrunk',
        'raw_not_in_fragment': model['raw_not_in_fragment'],
        'fit_admitted': False, 'claims_complete_training': False, 'claims_complete_corpus': False,
        'loss': None, 'optimizer': None,
        'reason': 'partial extended release; named inputs that are absent do not vote',
    }), encoding='utf-8')
    (output / 'fit_receipt.json').write_text(_dump({
        'kind': 'linear_pseudobulk_fit_receipt', 'loss': None, 'optimizer': None,
        'loss_applicable': False,
        'reason': 'the linear transfer has no gradient loss and no optimizer state',
        'fit_admitted': False, 'claims_complete_training': False, 'claims_complete_corpus': False,
    }), encoding='utf-8')
    artifacts = [{'path': path.relative_to(output).as_posix(), 'sha256': sha256_file(path),
                  'bytes': path.stat().st_size}
                 for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'checkpoint.json']
    (output / 'checkpoint.json').write_text(_dump({'files': artifacts, 'claims_complete_training': False}),
                                            encoding='utf-8')
    (output / 'status.json').write_text(_dump({
        'kind': 'incremental_extended_release', 'status': 'mixed',
        'n_sources': len(model['sources']), 'n_targets': len(model['targets']),
        'fit_admitted': False, 'claims_complete_training': False, 'claims_complete_corpus': False,
        'loss': None, 'optimizer': None,
    }), encoding='utf-8')


def main():
    params = json.loads(Path('params.json').read_text(encoding='utf-8'))
    root = Path(params.get('input_root', '/kaggle/input'))
    output = Path(params.get('output_root', '/kaggle/working/model'))
    built = build_incremental(
        root, params['expected'], gamma=params['final_mix']['gamma'],
        reliability_scale=params['final_mix']['reliability_scale'],
        weight=params['final_mix']['weight'])
    manifest = {
        'kind': 'incremental_extended_release',
        'expected': params['expected'],
        'used_mounts': built['used'],
        'missing_mounts': built['missing'],
        'cd4_gap': built['cd4_gap'],
        'joints': built['joints'],
        'fragments': built['fragments'],
        'not_in_this_mix': params.get('not_in_this_mix') or [],
        'final_mix': params['final_mix'],
        'axis': params.get('axis'),
        'cis': params.get('cis'),
        'emission': params.get('emission'),
        'coverage_contract': params.get('coverage_contract'),
        'storage_sha256': params.get('storage_sha256'),
        'training_ready': False,
        'fit_admitted': False,
        'claims_complete_training': False,
        'claims_complete_corpus': False,
        'loss': None,
        'optimizer': None,
        'k562_essential_replaces_k562': False,
    }
    if built['status'] == 'mixed':
        manifest['sources_in_final_mix'] = built['model']['sources']
        manifest['raw_not_in_fragment'] = built['model']['raw_not_in_fragment']
        manifest['cd4_mix_from'] = built['cd4_mix'].meta['from']
        manifest['aggregated_after_shrink'] = {
            'cd4_mix': False,
            'fragments': True,
        }
    write_release(output, built, manifest)


if __name__ == '__main__':
    main()
