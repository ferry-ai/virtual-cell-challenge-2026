"""Pool compatible count rows, then one effects_from_pseudobulk. No post-shrink average."""
from __future__ import annotations

import numpy as np

CALL = {
    'phi': 0.2,
    'min_control_frac': 1e-6,
    'min_cells': 10.0,
    'pseudo': 0.5,
    'pseudo_scale': 'constant',
    'min_expected': 1.0,
}


def z_shrink(eff, se, k=4.0):
    eff = np.asarray(eff, dtype=np.float64)
    se = np.asarray(se, dtype=np.float64)
    z2 = np.divide(eff * eff, se ** 2, out=np.zeros_like(eff, dtype=np.float64), where=se > 0)
    return eff * z2 / (z2 + k)


def effects_from_pseudobulk(X, obs, genes, *, targets, condition=None, phi=0.2,
                            min_control_frac=1e-6, min_cells=10.0, pseudo=0.5,
                            pseudo_scale='constant', min_expected=0.0):
    """Same arithmetic as vcc2026.multisource.effects_from_pseudobulk, without scipy."""
    if pseudo_scale not in ('constant', 'library'):
        raise ValueError('pseudo_scale must be constant or library')
    if not min_expected >= 0:
        raise ValueError('min_expected must be >= 0')
    matrix = np.asarray(X, dtype=np.float64)
    genes = np.asarray(genes).astype(str)
    target_col = np.asarray(obs['target']).astype(str)
    donor_col = np.asarray(obs['donor']).astype(str)
    cells_col = np.asarray(obs['n_cells'], dtype=np.float64)
    use = np.ones(len(target_col), dtype=bool) if condition is None else (
        np.asarray(obs['condition']).astype(str) == condition)
    is_ntc = target_col == 'non-targeting'
    donors = sorted(set(donor_col[use]))

    def colsum(mask):
        return matrix[mask].sum(axis=0, dtype=np.float64)

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
                pt, pc = pseudo * (float(st.sum()) / ref), pseudo * (float(cs.sum()) / ref)
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
        rows_s.append(np.where(usable, z_shrink(eff, se), 0.0).astype(np.float32))
        rows_r.append(np.where(usable, eff, 0.0).astype(np.float32))
        rows_se.append(se.astype(np.float32))
        ncell.append(int(wsum))
        kept.append(target)
    return {'genes': genes, 'targets': kept,
            'shrunk': np.vstack(rows_s) if kept else np.zeros((0, genes.size), np.float32),
            'raw': np.vstack(rows_r) if kept else np.zeros((0, genes.size), np.float32),
            'se': np.vstack(rows_se) if kept else np.zeros((0, genes.size), np.float32),
            'n_cells': np.asarray(ncell), 'control_mean': ctrl_frac,
            'meta': {'condition': condition, 'donors': donors, 'phi': phi,
                     'min_expected': min_expected, 'pseudo': pseudo, 'min_cells': min_cells}}


def _key(record):
    counts = np.ascontiguousarray(record['counts'], dtype=np.float64)
    return (str(record['donor']), str(record['target']), float(record['n_cells']), counts.tobytes())


def pool_records(banks):
    """Keep every distinct perturbation row. Keep one copy of an identical control row."""
    seen_control = set()
    seen_perturbation = set()
    pooled = []
    dropped_duplicate_controls = 0
    for bank in banks:
        for record in bank:
            counts = np.ascontiguousarray(record['counts'], dtype=np.float64)
            item = {'donor': str(record['donor']), 'target': str(record['target']),
                    'n_cells': float(record['n_cells']), 'counts': counts}
            identity = _key(item)
            if item['target'] == 'non-targeting':
                if identity in seen_control:
                    dropped_duplicate_controls += 1
                    continue
                seen_control.add(identity)
            elif identity in seen_perturbation:
                raise ValueError('duplicate perturbation row for ' + item['target'])
            else:
                seen_perturbation.add(identity)
            pooled.append(item)
    if not pooled:
        raise ValueError('no rows to pool')
    return pooled, {'duplicate_controls_dropped': dropped_duplicate_controls,
                    'n_rows': len(pooled), 'pooled_before_shrink': True}


def place_on_axis(result, axis_genes, min_control_frac=1e-6):
    index = {str(gene): position for position, gene in enumerate(axis_genes)}
    usable = np.asarray(result['control_mean'], dtype=np.float64) >= min_control_frac
    width = len(index)
    placed = {key: np.full((len(result['targets']), width), np.nan, np.float32)
              for key in ('shrunk', 'raw', 'se')}
    for column, gene in enumerate(np.asarray(result['genes']).astype(str)):
        position = index.get(gene)
        if position is None or not bool(usable[column]):
            continue
        for key in placed:
            placed[key][:, position] = np.asarray(result[key], dtype=np.float32)[:, column]
    return placed


def estimate_pooled(records, genes, targets, *, effects_fn=None, condition=None):
    """One call on the pooled rows. ``condition=None`` is the script-98 extra call."""
    if effects_fn is None:
        effects_fn = effects_from_pseudobulk
    matrix = np.vstack([np.asarray(item['counts'], dtype=np.float64) for item in records])
    obs = {'target': [item['target'] for item in records],
           'donor': [item['donor'] for item in records],
           'n_cells': [item['n_cells'] for item in records],
           'condition': ['group'] * len(records)}
    result = effects_fn(matrix, obs, genes, targets=list(targets), condition=condition, **CALL)
    if hasattr(result, 'targets'):
        result = {'genes': np.asarray(result.genes).astype(str), 'targets': list(result.targets),
                  'shrunk': np.asarray(result.shrunk), 'raw': np.asarray(result.raw),
                  'se': np.asarray(result.se), 'n_cells': np.asarray(result.n_cells),
                  'control_mean': np.asarray(result.control_mean), 'meta': dict(result.meta)}
    placed = place_on_axis(result, genes)
    return {'targets': result['targets'], 'n_cells': np.asarray(result['n_cells']),
            'shrunk': placed['shrunk'], 'raw': placed['raw'], 'se': placed['se'],
            'control_mean': np.asarray(result['control_mean'], dtype=np.float64),
            'meta': result['meta'], 'pooled_before_shrink': True, 'aggregated_after_shrink': False}


def project_rows(targets, shrunk, raw, se, n_cells, panel):
    """Panel order, measured rows only. Off-panel rows are an inventory, never zeros."""
    index = {str(name): position for position, name in enumerate(targets)}
    panel = [str(name) for name in panel]
    present = [name for name in panel if name in index]
    rows = [index[name] for name in present]
    panel_set = set(panel)
    unused = [str(name) for name in targets if str(name) not in panel_set]
    missing = [name for name in panel if name not in index]

    def take(array):
        array = np.asarray(array)
        if not rows:
            width = array.shape[1] if array.ndim == 2 else 0
            return np.zeros((0, width), dtype=np.float32)
        return np.asarray(array[rows], dtype=np.float32)

    cells = np.asarray(n_cells)
    return {'targets': present, 'shrunk': take(shrunk), 'raw': take(raw), 'se': take(se),
            'n_cells': cells[rows] if rows else np.asarray([], dtype=np.float64),
            'unused_targets': unused, 'panel_targets_missing': missing,
            'n_targets_full': len(list(targets)), 'projected_to_panel': True}


def estimate_spilled(records, genes, targets, *, budget_bytes, effects_fn=None, condition=None):
    """One call when the compact stack fits. Otherwise one call per target.

    Each per-target call still contains every donor's controls. The control
    fraction is that same pool, so the arrays match one call on the full stack.
    """
    genes = [str(gene) for gene in genes]
    stack_bytes = len(records) * len(genes) * 8
    wanted = [str(item) for item in targets]
    if stack_bytes <= int(budget_bytes):
        result = estimate_pooled(records, genes, wanted, effects_fn=effects_fn, condition=condition)
        result['schedule'] = 'one_call'
        result['compact_bytes'] = stack_bytes
        return result
    controls = [item for item in records if item['target'] == 'non-targeting']
    if not controls:
        raise ValueError('no matched non-targeting controls')
    by_target = {}
    for item in records:
        if item['target'] != 'non-targeting':
            by_target.setdefault(item['target'], []).append(item)
    pieces = []
    control_mean = None
    for target in wanted:
        if target not in by_target:
            continue
        group = controls + by_target[target]
        group_bytes = len(group) * len(genes) * 8
        if group_bytes > int(budget_bytes):
            raise ValueError('one target plus its controls exceeds the RAM budget')
        result = estimate_pooled(group, genes, [target], effects_fn=effects_fn, condition=condition)
        if not result['targets']:
            continue
        current = np.asarray(result['control_mean'], dtype=np.float64)
        if control_mean is None:
            control_mean = current
        elif not np.allclose(control_mean, current, rtol=0, atol=0):
            raise ValueError('control pool changed between targets')
        pieces.append(result)
    if not pieces:
        raise ValueError('no measured target')
    return {'targets': [target for piece in pieces for target in piece['targets']],
            'n_cells': np.concatenate([np.asarray(piece['n_cells']) for piece in pieces]),
            'shrunk': np.vstack([piece['shrunk'] for piece in pieces]),
            'raw': np.vstack([piece['raw'] for piece in pieces]),
            'se': np.vstack([piece['se'] for piece in pieces]),
            'control_mean': control_mean, 'meta': pieces[0]['meta'],
            'pooled_before_shrink': True, 'aggregated_after_shrink': False,
            'schedule': 'per_target_equivalent', 'compact_bytes': stack_bytes}
