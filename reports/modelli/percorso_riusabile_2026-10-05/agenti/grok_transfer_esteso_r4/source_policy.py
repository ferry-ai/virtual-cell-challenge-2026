"""One biological source gets one mix weight. Donor and partition tables do not vote."""
from __future__ import annotations

import sys

import numpy as np

from pins import REPO

sys.path.insert(0, str(REPO / 'src'))
from vcc2026.multisource import AxisTable  # noqa: E402


def _align(parts):
    targets = []
    seen = set()
    for part in parts:
        for target in part.targets:
            if target not in seen:
                seen.add(target)
                targets.append(target)
    width = parts[0].shrunk.shape[1]
    if any(part.shrunk.shape[1] != width for part in parts):
        raise ValueError('subcontexts have different gene axes')
    return targets


def _weighted(parts, name, *, equal):
    targets = _align(parts)
    width = parts[0].shrunk.shape[1]
    acc = np.zeros((len(targets), width), dtype=np.float64)
    weight = np.zeros((len(targets), width), dtype=np.float64)
    cells = np.zeros(len(targets), dtype=np.float64)
    for part in parts:
        index = {target: position for position, target in enumerate(part.targets)}
        for row, target in enumerate(targets):
            if target not in index:
                continue
            present = np.isfinite(part.shrunk[index[target]])
            vote = 1.0 if equal else float(part.n_cells[index[target]])
            acc[row, present] += vote * part.shrunk[index[target], present]
            weight[row, present] += vote
            cells[row] += float(part.n_cells[index[target]])
    values = np.full_like(acc, np.nan)
    np.divide(acc, weight, out=values, where=weight > 0)
    finite_cells = np.where(np.isfinite(cells), cells, 0.0)
    return AxisTable(name, targets, values.astype(np.float32), values.astype(np.float32),
                     np.full_like(values, np.nan, dtype=np.float32), finite_cells,
                     {'transfer_source_id': name, 'collapsed_from': [part.name for part in parts]})


def collapse_subcontexts(parts, source_id):
    """Cell-weight donors inside a condition, then equal-weight conditions."""
    if len(parts) == 1 and parts[0].name == source_id:
        return parts[0]
    by_condition = {}
    for part in parts:
        by_condition.setdefault(str(part.meta.get('condition', part.name)), []).append(part)
    conditions = [_weighted(group, source_id + '::' + condition, equal=False)
                  for condition, group in sorted(by_condition.items())]
    collapsed = _weighted(conditions, source_id, equal=True)
    collapsed.meta['policy'] = 'donors cell-weighted within condition; conditions equal-weighted'
    collapsed.meta['conditions'] = sorted(by_condition)
    return collapsed
