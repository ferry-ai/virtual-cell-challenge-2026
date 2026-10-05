"""Count-sum effects on a full biological identity. Numpy and pandas only.

A gene is estimated only on the intersection of the masks of the rows that are
summed and of their matched controls. Unmeasured entries stay out of the
library size. They are never filled with zero and then rescued by a mask.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

BIO = ('study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry')
GROUP = ('study', 'context', 'condition', 'modality', 'chemistry')
CONTROL_LABELS = {'NTC': 'non-targeting'}
CALL = {
    'phi': 0.2,
    'min_control_frac': 1e-6,
    'min_cells': 10.0,
    'pseudo': 0.5,
    'pseudo_scale': 'constant',
    'min_expected': 1.0,
}


class MissingComponents(ValueError):
    """A perturbed row has no explicit component list."""


def z_shrink(eff, se, k=4.0):
    eff = np.asarray(eff, dtype=np.float64)
    se = np.asarray(se, dtype=np.float64)
    z2 = np.divide(eff * eff, se ** 2, out=np.zeros_like(eff, dtype=np.float64), where=se > 0)
    return eff * z2 / (z2 + k)


def effects_from_pseudobulk(X, obs, genes, *, targets, condition=None, phi=0.2,
                            min_control_frac=1e-6, min_cells=10.0, pseudo=0.5,
                            pseudo_scale='constant', min_expected=0.0):
    """Same call as vcc2026.multisource.effects_from_pseudobulk, without scipy."""
    if pseudo_scale not in ('constant', 'library'):
        raise ValueError('pseudo_scale must be constant or library')
    if not min_expected >= 0:
        raise ValueError('min_expected must be >= 0')
    X = np.asarray(X, dtype=np.float64)
    genes = np.asarray(genes).astype(str)
    obs = obs.reset_index(drop=True)
    target_col = obs['target'].to_numpy().astype(str)
    donor_col = obs['donor'].to_numpy().astype(str)
    cells_col = obs['n_cells'].to_numpy().astype(np.float64)
    use = np.ones(len(obs), dtype=bool) if condition is None else (obs['condition'].to_numpy() == condition)
    is_ntc = target_col == 'non-targeting'
    donors = sorted(set(donor_col[use]))

    def colsum(mask):
        return X[mask].sum(axis=0, dtype=np.float64)

    ctrl = {}
    for donor in donors:
        mask = use & is_ntc & (donor_col == donor)
        if not mask.any():
            continue
        ctrl[donor] = (colsum(mask), float(cells_col[mask].sum()))
    if not ctrl:
        raise ValueError('no matched non-targeting controls')
    pooled = sum(item[0] for item in ctrl.values())
    total = float(pooled.sum())
    if total <= 0:
        raise ValueError('control library is empty')
    ctrl_frac = pooled / total
    usable = ctrl_frac >= min_control_frac
    rows_s, rows_r, rows_se, ncell, kept = [], [], [], [], []
    for target in targets:
        eff_sum = np.zeros(genes.size)
        var_sum = np.zeros(genes.size)
        wsum = 0.0
        wvec = np.zeros(genes.size) if min_expected > 0 else None
        for donor, (cs, cn) in ctrl.items():
            mask = use & (target_col == target) & (donor_col == donor)
            if not mask.any():
                continue
            n_t = float(cells_col[mask].sum())
            if n_t < min_cells:
                continue
            st = colsum(mask)
            if pseudo_scale == 'library':
                ref = min(float(st.sum()), float(cs.sum()))
                pt, pc = pseudo * (st.sum() / ref), pseudo * (cs.sum() / ref)
            else:
                pt = pc = pseudo
            effect = np.log((st + pt) / st.sum()) - np.log((cs + pc) / cs.sum())
            variance = 1.0 / (st + pt) + phi / n_t + 1.0 / (cs + pc) + phi / cn
            if wvec is None:
                eff_sum += n_t * effect
                var_sum += n_t ** 2 * variance
            else:
                evidence = cs * (st.sum() / cs.sum()) >= min_expected
                eff_sum += np.where(evidence, n_t * effect, 0.0)
                var_sum += np.where(evidence, n_t ** 2 * variance, 0.0)
                wvec += np.where(evidence, n_t, 0.0)
            wsum += n_t
        if wsum <= 0:
            continue
        if wvec is None:
            eff = eff_sum / wsum
            se = np.sqrt(var_sum) / wsum
        else:
            has = wvec > 0
            eff = np.where(has, eff_sum / np.where(has, wvec, 1.0), np.nan)
            se = np.where(has, np.sqrt(var_sum) / np.where(has, wvec, 1.0), np.nan)
        shrunk = np.where(usable, z_shrink(eff, se), 0.0)
        rows_s.append(shrunk.astype(np.float32))
        rows_r.append(np.where(usable, eff, 0.0).astype(np.float32))
        rows_se.append(se.astype(np.float32))
        ncell.append(int(wsum))
        kept.append(target)
    meta = {'condition': condition, 'donors': donors, 'phi': phi,
            'n_control_cells': int(sum(item[1] for item in ctrl.values())),
            'se_model': f'quasi-Poisson phi={phi}, donor-weighted',
            'min_expected': min_expected}
    return {'genes': genes, 'targets': kept, 'shrunk': np.vstack(rows_s) if kept else np.zeros((0, genes.size), np.float32),
            'raw': np.vstack(rows_r) if kept else np.zeros((0, genes.size), np.float32),
            'se': np.vstack(rows_se) if kept else np.zeros((0, genes.size), np.float32),
            'n_cells': np.array(ncell), 'control_mean': ctrl_frac, 'meta': meta}


def _blank(value):
    if value is None:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def parse_components(raw):
    if isinstance(raw, (list, tuple)):
        if not raw:
            raise ValueError('empty target_components')
        return [str(part) for part in raw]
    if isinstance(raw, str) and raw.strip().startswith('['):
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or not parsed:
            raise ValueError('target_components must be a non-empty list')
        return [str(part) for part in parsed]
    raise ValueError('refusing to split compound components on punctuation')


def component_list(row, crosswalk=None):
    label = CONTROL_LABELS.get(str(row['target']), str(row['target']))
    if label == 'non-targeting':
        return []
    if 'target_components' in row.index and not _blank(row['target_components']):
        return parse_components(row['target_components'])
    if crosswalk is not None and str(row['target']) in crosswalk:
        parts = list(crosswalk[str(row['target'])])
        if not parts:
            raise MissingComponents('empty crosswalk entry for ' + str(row['target']))
        return [str(part) for part in parts]
    raise MissingComponents('target_components required before filtering: ' + str(row['target']))


def _require_columns(rows):
    missing = set(BIO + ('target', 'n', 'line_group')) - set(rows.columns)
    if missing:
        raise ValueError('rows missing ' + ','.join(sorted(missing)))


def _components_first(rows, crosswalk):
    """Resolve every perturbed row before any count is read."""
    found = []
    for position, row in rows.reset_index(drop=True).iterrows():
        found.append((position, component_list(row, crosswalk)))
    return found


def partition_rows(rows, held_groups, hidden_targets, crosswalk=None):
    held, hidden = set(map(str, held_groups)), set(map(str, hidden_targets))
    listed = _components_first(rows, crosswalk)
    keep, dropped = [], []
    frame = rows.reset_index(drop=True)
    for position, parts in listed:
        row = frame.loc[position]
        reason = None
        if str(row['line_group']) in held:
            reason = 'held_group'
        elif set(parts) & hidden:
            reason = 'hidden_component'
        if reason:
            dropped.append({'row': int(position), 'reason': reason, 'target': str(row['target']),
                            'line_group': str(row['line_group']), 'components': parts})
        else:
            keep.append(int(position))
    return keep, dropped


def _label(value):
    return CONTROL_LABELS.get(str(value), str(value))


def _cache_index(control_cache):
    indexed = {}
    if not control_cache:
        return indexed
    for item in control_cache:
        key = tuple(str(item[field]) for field in BIO)
        indexed.setdefault(key, []).append(item)
    return indexed


def _align(item, genes):
    source_genes = [str(gene) for gene in item['genes']]
    position = {gene: index for index, gene in enumerate(source_genes)}
    counts = np.zeros(len(genes), dtype=np.float64)
    mask = np.zeros(len(genes), dtype=bool)
    source_counts = np.asarray(item['counts'], dtype=np.float64)
    source_mask = np.asarray(item['mask'], dtype=bool)
    for index, gene in enumerate(genes):
        if gene in position:
            counts[index] = source_counts[position[gene]]
            mask[index] = source_mask[position[gene]]
    return counts, mask


def _scatter(result, columns, n_genes):
    """Place the original arrays on the axis. Low-control genes are NaN as in AxisTable.from_source."""
    out = {key: np.full((len(result['targets']), n_genes), np.nan, dtype=np.float32)
           for key in ('shrunk', 'raw', 'se')}
    if len(columns):
        for key in out:
            usable = np.asarray(result['control_mean']) >= CALL['min_control_frac']
            out[key][:, columns[usable]] = np.asarray(result[key], dtype=np.float32)[:, usable]
    return out


def _one_target(counts, mask, frame, genes, target, columns_budget):
    """Match effects_from_pseudobulk: ctrl_frac uses every control donor.

    A donor with controls and no target still enters the control pool. Only the
    effect skips that donor. The column intersection includes those control rows
    so the pool is not reduced to donors that also carry the target.
    """
    labels = frame['target'].map(_label).to_numpy()
    donors = sorted(frame['donor_or_clone'].astype(str).unique())
    control_rows = []
    for donor in donors:
        donor_at = frame['donor_or_clone'].astype(str).to_numpy() == donor
        control_at = np.flatnonzero(donor_at & (labels == 'non-targeting'))
        if not len(control_at):
            continue
        control_rows.append((donor, control_at, float(frame.iloc[control_at]['n'].sum())))
    eligible = []
    for donor, control_at, n_control in control_rows:
        donor_at = frame['donor_or_clone'].astype(str).to_numpy() == donor
        target_at = np.flatnonzero(donor_at & (labels == target))
        n_target = float(frame.iloc[target_at]['n'].sum()) if len(target_at) else 0.0
        if len(target_at) and n_target >= CALL['min_cells']:
            eligible.append((donor, target_at, n_target))
    if not control_rows or not eligible:
        return None
    intersection = np.ones(counts.shape[1], dtype=bool)
    for donor, control_at, n_control in control_rows:
        intersection &= mask[control_at].all(axis=0)
    for donor, target_at, n_target in eligible:
        intersection &= mask[target_at].all(axis=0)
    columns = np.flatnonzero(intersection)
    if not len(columns):
        return None
    if columns.size > columns_budget:
        raise MemoryError('intersection exceeds the column budget')
    pieces, obs_rows, used = [], [], []
    for donor, target_at, n_target in eligible:
        pieces.append(counts[target_at][:, columns].sum(axis=0))
        obs_rows.append({'target': target, 'donor': donor, 'condition': 'group', 'n_cells': n_target})
        used.append(donor)
    for donor, control_at, n_control in control_rows:
        pieces.append(counts[control_at][:, columns].sum(axis=0))
        obs_rows.append({'target': 'non-targeting', 'donor': donor, 'condition': 'group', 'n_cells': n_control})
    result = effects_from_pseudobulk(
        np.vstack(pieces), pd.DataFrame(obs_rows), genes[columns], targets=[target],
        condition='group', **CALL)
    if result['meta'].get('min_expected') != 1.0 or 'pseudo_scale' in result['meta']:
        raise ValueError('estimator contract was not the corrected t25 call')
    if not result['targets']:
        return None
    return _scatter(result, columns, counts.shape[1]), int(result['n_cells'][0]), used


def estimate_source(rows, count_sum, gene_mask, genes, source_name, *, modality,
                    held_groups=(), hidden_targets=(), crosswalk=None, control_cache=None):
    rows = rows.reset_index(drop=True)
    _require_columns(rows)
    keep, dropped = partition_rows(rows, held_groups, hidden_targets, crosswalk)
    count_sum = np.asarray(count_sum, dtype=np.float64)
    genes = [str(gene) for gene in genes]
    if count_sum.ndim != 2 or count_sum.shape != (len(rows), len(genes)):
        raise ValueError('count_sum shape does not match rows and genes')
    gene_mask = np.asarray(gene_mask, dtype=bool)
    if gene_mask.shape == (len(genes),):
        gene_mask = np.broadcast_to(gene_mask, count_sum.shape).copy()
    if gene_mask.shape != count_sum.shape:
        raise ValueError('mask shape does not match count_sum')
    if not np.isfinite(count_sum).all() or (count_sum < 0).any():
        raise ValueError('invalid counts')
    counts = rows['n'].to_numpy(dtype=float)
    if not np.isfinite(counts).all() or (counts < 0).any():
        raise ValueError('invalid n_cells')
    kept = rows.iloc[keep].reset_index(drop=True)
    count_sum = count_sum[keep]
    gene_mask = gene_mask[keep]
    if set(kept['line_group'].astype(str)) & set(map(str, held_groups)):
        raise ValueError('held group survived partition')
    if not kept.empty and set(kept['modality'].astype(str)) != {modality}:
        raise ValueError('modality is not partitioned: ' + ','.join(sorted(set(kept['modality'].astype(str)))))
    cache = _cache_index(control_cache)
    tables, omitted = [], []
    if kept.empty:
        raise ValueError('no row survived partition')
    for key, part in kept.groupby(list(GROUP), sort=True):
        identity = dict(zip(GROUP, key if isinstance(key, tuple) else (key,)))
        positions = kept.index.get_indexer(part.index)
        part = part.reset_index(drop=True)
        part_counts = count_sum[positions]
        part_mask = gene_mask[positions]
        labels = part['target'].map(_label)
        donors = sorted(part['donor_or_clone'].astype(str).unique())
        extra_counts, extra_mask, extra_rows = [], [], []
        for donor in donors:
            local = (part['donor_or_clone'].astype(str) == donor) & (labels == 'non-targeting')
            if local.any():
                continue
            bio = (identity['study'], identity['context'], donor, identity['condition'],
                   identity['modality'], identity['chemistry'])
            matched = cache.get(bio, [])
            if not matched:
                continue
            for item in matched:
                aligned_counts, aligned_mask = _align(item, genes)
                extra_counts.append(aligned_counts)
                extra_mask.append(aligned_mask)
                extra_rows.append({**{field: identity[field] for field in GROUP},
                                   'donor_or_clone': donor, 'target': 'NTC', 'n': item['n'],
                                   'line_group': str(part['line_group'].iloc[0])})
        if extra_rows:
            part = pd.concat([part, pd.DataFrame(extra_rows)], ignore_index=True)
            part_counts = np.vstack([part_counts, np.vstack(extra_counts)])
            part_mask = np.vstack([part_mask, np.vstack(extra_mask)])
        wanted = sorted(set(part['target'].map(_label)) - {'non-targeting'})
        from pathlib import Path
        panel = set(json.loads(Path('params.json').read_text())['target_panel'])
        wanted = [target for target in wanted if target in panel]
        if not (part['target'].map(_label) == 'non-targeting').any():
            omitted.append({**identity, 'reason': 'no_matched_controls'})
            continue
        shrunk, raw, se, n_cells, targets, donor_used = [], [], [], [], [], {}
        for target in wanted:
            estimated = _one_target(part_counts, part_mask, part, np.asarray(genes), target, part_counts.shape[1])
            if estimated is None:
                omitted.append({**identity, 'target': target, 'reason': 'no_measured_intersection'})
                continue
            scattered, cells, used = estimated
            targets.append(target)
            shrunk.append(scattered['shrunk'][0])
            raw.append(scattered['raw'][0])
            se.append(scattered['se'][0])
            n_cells.append(cells)
            donor_used[target] = used
        if not targets:
            continue
        present = sorted(part['donor_or_clone'].astype(str).unique())
        meta = {**identity, 'donors': present, 'donor_cells': {
                    donor: float(part.loc[part['donor_or_clone'].astype(str) == donor, 'n'].sum())
                    for donor in present},
                'matrix': 'count_sum', 'transfer_source_id': source_name,
                'called_with': dict(CALL), 'control_label_map': dict(CONTROL_LABELS),
                'donors_used': donor_used}
        name = '::'.join([source_name, *[identity[field] for field in GROUP]])
        tables.append({'name': name, 'targets': targets,
                       'shrunk': np.vstack(shrunk), 'raw': np.vstack(raw), 'se': np.vstack(se),
                       'n_cells': np.asarray(n_cells), 'meta': meta, 'genes': list(genes)})
    if not tables:
        raise ValueError('no biological context produced a measured target; controls were not invented')
    return {'tables': tables, 'dropped_rows': dropped, 'omitted': omitted}


def assert_matrix_budget(n_rows, n_genes, budget=6 * 1024 ** 3):
    need = int(n_rows) * int(n_genes) * 8
    if need > budget:
        raise MemoryError(f'count_sum needs {need} bytes; budget is {budget}')
    return need
