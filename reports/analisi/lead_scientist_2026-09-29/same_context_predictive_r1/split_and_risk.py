"""Metadata-only guide splits and streaming held-out prediction risk; no model fit."""
from collections import Counter, defaultdict
import hashlib

import numpy as np

SEED = 20260929


def key(kind, value):
    return hashlib.sha256(f'{SEED}|{kind}|{value}'.encode('utf-8')).hexdigest()


def make_plan(channels, guide_names, guide_targets, official_targets, prior_targets, genes):
    if len(channels) != 16 or len(set(channels)) != 16:
        raise ValueError('Expected 16 distinct channels')
    if len(guide_names) != len(guide_targets) or len(set(guide_names)) != len(guide_names):
        raise ValueError('Invalid guide axes')
    if len(official_targets) != 300 or len(set(official_targets)) != 300:
        raise ValueError('Expected the complete 300-target panel')
    groups = defaultdict(list)
    for guide, target in zip(guide_names, guide_targets):
        groups[target].append(guide)
    eligible = set(prior_targets) - set(official_targets) - {'non-targeting'}
    calibration = sorted((t for t in eligible if len(groups[t]) >= 4), key=lambda t: key('target', t))[:512]
    role = {g: 'fit' for g in guide_names}
    coverage = {}
    for label, targets in [('calibration', calibration), ('test', official_targets)]:
        for target in targets:
            ordered = sorted(groups[target], key=lambda g: key('guide', g))
            n_reserved = 2 if len(ordered) >= 4 else 1 if len(ordered) == 3 else 0
            for guide in ordered[:n_reserved]:
                role[guide] = label
            coverage[target] = {'guides': len(ordered), 'reserved': n_reserved,
                                'fit': len(ordered) - n_reserved, 'correction_eligible': n_reserved > 0}
    ordered = sorted(channels, key=lambda c: key('channel', c))
    channel_role = {c: ('fit' if i < 8 else 'calibration' if i < 12 else 'test')
                    for i, c in enumerate(ordered)}
    ordered_genes = sorted(set(genes), key=lambda g: key('response-gene', g))
    midpoint = len(ordered_genes) // 2
    return {'seed': SEED, 'channel_role': channel_role, 'guide_role': role,
            'guide_target': dict(zip(guide_names, guide_targets)),
            'calibration_targets': calibration, 'test_targets': list(official_targets),
            'tuning_genes': ordered_genes[:midpoint], 'evaluation_genes': ordered_genes[midpoint:],
            'coverage': coverage}


def assign_cells(plan, channel, barcode_indices, guide_names, carried):
    """One role/focal guide per cell; retain exclusion reasons for every discarded cell."""
    if carried.shape != (len(barcode_indices), len(guide_names)) or not carried.has_sorted_indices:
        raise ValueError('CSR dimensions/order invalid')
    if len(set(map(int, barcode_indices))) != len(barcode_indices):
        raise ValueError('Duplicate cell barcode index within a channel')
    phase = plan['channel_role'][channel]
    guide_roles = [plan['guide_role'][g] for g in guide_names]
    guide_targets = [plan['guide_target'][g] for g in guide_names]
    focal = np.full(len(barcode_indices), -1, np.int32)
    keep_training = np.zeros(len(barcode_indices), bool)
    counts = Counter()
    for row, barcode in enumerate(barcode_indices):
        gs = carried.indices[carried.indptr[row]:carried.indptr[row + 1]]
        reserved = [g for g in gs if guide_roles[g] != 'fit']
        if phase == 'fit':
            keep_training[row] = not reserved
            counts['training_kept' if not reserved else 'training_excluded_reserved_guide'] += 1
            continue
        if any(guide_roles[g] != phase for g in reserved):
            counts['excluded_other_reserved_partition'] += 1
            continue
        if not reserved:
            counts['no_reserved_focal_guide'] += 1
            continue
        fitting_targets = {guide_targets[g] for g in gs if guide_roles[g] == 'fit'}
        candidates = [g for g in reserved if guide_targets[g] not in fitting_targets]
        if not candidates:
            counts['excluded_focal_target_has_fitting_guide'] += 1
            continue
        if len(candidates) > 1:
            counts['multiple_focal_candidates_assigned_once'] += 1
        chosen = min(candidates, key=lambda g: key('cell-focal-guide', f'{channel}|{int(barcode)}|{guide_names[g]}'))
        focal[row] = chosen
        counts['evaluation_kept'] += 1
    return {'training': keep_training, 'focal_guide_index': focal, 'counts': dict(counts)}


class PredictionRisk:
    """Cell batches are reduced to independent-guide summaries before target means.

    Callers must only pass unique focal cells from assign_cells; this class never
    estimates normalization, nuisance, effects or parameters from held-out RNA.
    """
    def __init__(self):
        self.sums = defaultdict(lambda: np.zeros(4, np.float64))

    def add(self, condition, targets, guides, observed, prior_prediction, candidate_prediction, mask):
        arrays = [np.asarray(a) for a in (observed, prior_prediction, candidate_prediction, mask)]
        if len({a.shape for a in arrays}) != 1 or arrays[0].ndim != 2:
            raise ValueError('Prediction and mask axes differ')
        if any(len(x) != len(observed) for x in (condition, targets, guides)):
            raise ValueError('Observation metadata differs')
        mask = arrays[-1].astype(bool)
        if any(np.any(~np.isfinite(a[mask])) for a in arrays[:3]):
            raise ValueError('Nonfinite measured outcome/prediction')
        support = mask.sum(axis=1)
        if np.any(support == 0):
            raise ValueError('Cells without observed response support must be reported as missing')
        base_loss = np.where(mask, (arrays[0] - arrays[1])**2, 0).sum(axis=1) / support
        new_loss = np.where(mask, (arrays[0] - arrays[2])**2, 0).sum(axis=1) / support
        for cond, target, guide, baseline, candidate, n in zip(condition, targets, guides, base_loss, new_loss, support):
            self.sums[(str(cond), str(target), str(guide))] += [1, baseline, candidate, n]

    def finish(self, expected_conditions=('0', '1')):
        guide_rows = []
        grouped = defaultdict(list)
        for (condition, target, guide), (n, baseline, candidate, support) in sorted(self.sums.items()):
            row = {'condition': condition, 'target': target, 'guide': guide, 'cells': int(n),
                   'mean_response_support': support / n, 'prior_mse': baseline / n,
                   'candidate_mse': candidate / n, 'gain': (baseline - candidate) / n}
            guide_rows.append(row)
            grouped[(condition, target)].append(row)
        target_rows = []
        states = defaultdict(list)
        for (condition, target), rows in sorted(grouped.items()):
            row = {'condition': condition, 'target': target, 'guides': len(rows),
                   'cells': sum(r['cells'] for r in rows),
                   'prior_mse': float(np.mean([r['prior_mse'] for r in rows])),
                   'candidate_mse': float(np.mean([r['candidate_mse'] for r in rows])),
                   'gain': float(np.mean([r['gain'] for r in rows]))}
            target_rows.append(row)
            states[condition].append(row['gain'])
        state_gain = {c: float(np.mean(g)) for c, g in states.items()}
        complete = set(state_gain) == set(expected_conditions)
        return {'guide_rows': guide_rows, 'target_rows': target_rows, 'state_gain': state_gain,
                'primary_conditions_complete': complete,
                'macro_gain': float(np.mean(list(state_gain.values()))) if complete else None,
                'claim': 'Measured-support predictive MSE only; not a single-intervention effect or VCC score'}
