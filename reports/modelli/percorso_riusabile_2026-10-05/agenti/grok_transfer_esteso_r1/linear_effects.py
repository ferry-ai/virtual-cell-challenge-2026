"""Count-sum effects with the corrected t25 estimator.

Matched donor controls, constant pseudocount, min_expected 1. A gene the controls
do not support is unmeasured. Mean proportions are refused. Conditions are not pooled.
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

from pins import CONTROL_LABELS, ESTIMATOR, REPO

sys.path.insert(0, str(REPO / 'src'))
from vcc2026.multisource import AxisTable, effects_from_pseudobulk  # noqa: E402

_CALL = {key: ESTIMATOR[key] for key in
         ('phi', 'min_control_frac', 'min_cells', 'pseudo', 'pseudo_scale', 'min_expected')}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_count_sum(path, sha256, nbytes):
    if path.name != 'count_sum.npz':
        raise ValueError('refusing matrix ' + path.name + '; count_sum is required')
    if path.stat().st_size != nbytes or sha256_file(path) != sha256:
        raise ValueError('count_sum identity mismatch')
    loaded = np.load(path)
    if list(loaded.files) != ['value']:
        raise ValueError('unexpected count_sum keys')
    return np.asarray(loaded['value'], dtype=np.float64)


def component_list(row):
    if 'target_components' not in row.index:
        return [str(row['target'])]
    raw = row['target_components']
    if raw is None or raw == '' or (isinstance(raw, float) and np.isnan(raw)):
        return [str(row['target'])]
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


def partition_rows(rows, held_groups, hidden_targets):
    held, hidden = set(map(str, held_groups)), set(map(str, hidden_targets))
    keep, dropped = [], []
    for position, (_, row) in enumerate(rows.reset_index(drop=True).iterrows()):
        reason = None
        if str(row['line_group']) in held:
            reason = 'held_group'
        elif set(component_list(row)) & hidden:
            reason = 'hidden_component'
        if reason:
            dropped.append({'row': position, 'reason': reason, 'target': str(row['target']),
                            'line_group': str(row['line_group'])})
        else:
            keep.append(position)
    return keep, dropped


def _require_columns(rows):
    required = {'study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry',
                'target', 'n', 'line_group'}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError('rows missing ' + ','.join(sorted(missing)))
    counts = rows['n'].to_numpy(dtype=float)
    if not np.isfinite(counts).all() or (counts < 0).any():
        raise ValueError('invalid n_cells')


def _measured(rows, mask, targets):
    """A gene counts only where every summed target row and control row measured it."""
    mapped = rows['target'].map(lambda value: CONTROL_LABELS.get(str(value), str(value)))
    donors = sorted(rows['donor_or_clone'].astype(str).unique())
    ok = np.zeros((len(targets), mask.shape[1]), dtype=bool)
    for index, target in enumerate(targets):
        for donor in donors:
            donor_ok = rows['donor_or_clone'].astype(str) == donor
            target_at = np.flatnonzero((mapped == target) & donor_ok)
            control_at = np.flatnonzero((mapped == 'non-targeting') & donor_ok)
            if not len(target_at) or not len(control_at):
                continue
            ok[index] |= mask[target_at].all(axis=0) & mask[control_at].all(axis=0)
    return ok


def estimate_source(rows, count_sum, gene_mask, genes, source_name, *, modality,
                    held_groups=(), hidden_targets=()):
    rows = rows.reset_index(drop=True)
    _require_columns(rows)
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
    keep, dropped = partition_rows(rows, held_groups, hidden_targets)
    kept = rows.iloc[keep].reset_index(drop=True)
    count_sum = np.where(gene_mask[keep], count_sum[keep], 0.0)
    gene_mask = gene_mask[keep]
    if set(kept['line_group'].astype(str)) & set(map(str, held_groups)):
        raise ValueError('held group survived partition')
    modalities = set(kept['modality'].astype(str))
    if not kept.empty and modalities != {modality}:
        raise ValueError('modality is not partitioned: ' + ','.join(sorted(modalities)))
    tables, omitted = [], []
    for condition, part in kept.groupby('condition', sort=True):
        positions = kept.index.get_indexer(part.index)
        obs = pd.DataFrame({
            'target': part['target'].map(lambda value: CONTROL_LABELS.get(str(value), str(value))).to_numpy(),
            'donor': part['donor_or_clone'].astype(str).to_numpy(),
            'condition': part['condition'].astype(str).to_numpy(),
            'n_cells': part['n'].to_numpy(dtype=float),
        })
        wanted = sorted(set(obs['target']) - {'non-targeting'})
        if not (obs['target'] == 'non-targeting').any():
            raise ValueError('no matched non-targeting controls for condition ' + str(condition))
        source = effects_from_pseudobulk(
            count_sum[positions], obs, genes, targets=wanted, condition=str(condition), **_CALL)
        if source.meta.get('min_expected') != 1.0 or 'pseudo_scale' in source.meta:
            raise ValueError('estimator contract was not the corrected t25 call')
        omitted.extend(sorted(set(wanted) - set(source.targets)))
        if not source.targets:
            continue
        table = AxisTable.from_source(f'{source_name}::{condition}', source, genes)
        measured = _measured(part.reset_index(drop=True), gene_mask[positions], list(table.targets))
        for key in ('shrunk', 'raw', 'se'):
            values = np.array(getattr(table, key), dtype=np.float32, copy=True)
            values[~measured] = np.nan
            setattr(table, key, values)
        table.meta = dict(source.meta)
        table.meta.update({'matrix': 'count_sum', 'called_with': dict(ESTIMATOR),
                           'control_label_map': dict(CONTROL_LABELS), 'condition': str(condition)})
        tables.append(table)
    if not tables:
        raise ValueError('no condition produced a measured target; scarce controls block this source')
    return {'tables': tables, 'dropped_rows': dropped, 'omitted_targets': omitted}
