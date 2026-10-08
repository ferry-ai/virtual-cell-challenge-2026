"""Metadata-first fold selection and bounded-memory effect derivation.

No gene-name heuristics, global fitted statistics, or modality mixing. Raw arrays
are accessed only after the fold and biological identities have been resolved.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

BIO = ('study', 'line_group', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry')
SPECIAL = {'UNASSIGNED', 'NO_METADATA'}
HIDDEN_RULE = 'int(sha256(symbol utf-8).hexdigest(), 16) % 5 == 0, on every component of every label'


def validate_split(split):
    required = {'id', 'regime', 'held_groups', 'hidden_targets', 'protected_units', 'group_aliases'}
    if not required.issubset(split):
        raise ValueError('incomplete explicit split manifest')
    if split['regime'] not in {'production', 'C', 'T', 'J'}:
        raise ValueError('unknown regime')
    if split['regime'] in {'C', 'J'} and not split['held_groups']:
        raise ValueError('held context required')
    if split['regime'] in {'T', 'J'} and not split['hidden_targets']:
        raise ValueError('hidden targets required')
    if 'h1_test' not in split['protected_units']:
        raise ValueError('H1 test must remain protected')
    if split.get('hidden_rule') not in (None, HIDDEN_RULE):
        raise ValueError('unknown frozen hidden-target rule')


def select_rows(rows, resolutions, split, unit):
    """Return admitted metadata and a complete exclusion ledger, before arrays."""
    validate_split(split)
    if unit in split['protected_units']:
        raise ValueError('protected unit: ' + unit)
    if not set((*BIO, 'target', 'n')).issubset(rows.columns):
        raise ValueError('incomplete biological metadata')
    held, hidden = set(split['held_groups']), set(split['hidden_targets'])
    def hidden_component(name):
        return name in hidden or (split['regime'] in {'T','J'} and split.get('hidden_rule') == HIDDEN_RULE
            and int(hashlib.sha256(name.encode('utf-8')).hexdigest(),16) % 5 == 0)
    aliases = split['group_aliases']
    # Manifest keys and held values must use the same canonical group vocabulary.
    held = {aliases.get(g, g) for g in held}
    kept, records, counts = [], [], Counter()
    for pos, record in enumerate(rows.to_dict('records')):
        n = float(record['n'])
        if not np.isfinite(n) or n < 0 or n != int(n):
            raise ValueError('invalid cell population')
        target = str(record['target'])
        group = aliases.get(str(record['line_group']), str(record['line_group']))
        reason, label = None, None
        if unit in split.get('exclude_units', []):
            reason = 'excluded_unit'
        elif group in held:
            reason = 'held_group'
        elif n == 0:
            reason = 'empty_bank_row'
        elif target == 'NTC':
            label = 'non-targeting'
        elif target in SPECIAL:
            reason = 'unassigned_or_missing_metadata'
        elif target not in resolutions:
            reason = 'unresolved_target_mapping'
        else:
            entry = resolutions[target]
            components = entry.get('components')
            if not entry.get('evidence') or not components or any(not isinstance(c, str) or not c for c in components):
                raise ValueError('unproven target crosswalk: ' + target)
            label = entry['target']
            if hidden_component(label) or any(hidden_component(c) for c in components):
                reason = 'hidden_component'
            elif len(components) != 1 or components[0] != label:
                reason = 'compound_requires_separate_consumer'
        if reason:
            records.append(dict(row=pos, native_target=target, reason=reason, cells=int(n)))
            counts[reason] += int(n)
            continue
        record.update(bank_row=pos, native_target=target, target=label, line_group=group)
        # Missing biological identities stay missing, visibly scoped to study.
        for col in ('donor_or_clone', 'condition', 'chemistry'):
            if str(record[col]).upper() in {'', 'MISSING', 'UNASSIGNED'}:
                record[col] = 'UNREPORTED@' + str(record['study'])
        if any(str(record[col]).upper() in {'', 'MISSING', 'UNASSIGNED'} for col in ('study', 'line_group', 'context', 'modality')):
            records.append(dict(row=pos, native_target=target, reason='unresolved_context_identity', cells=int(n)))
            counts['unresolved_context_identity'] += int(n)
            continue
        kept.append(record)
        counts['control' if label == 'non-targeting' else 'effect_target'] += int(n)
    frame = pd.DataFrame(kept)
    if not frame.empty and frame.duplicated([*BIO, 'target']).any():
        raise ValueError('duplicate biological row; explicit block/guide pooling required')
    return frame, dict(cells_by_role=dict(counts), excluded_rows=records,
                       bank_cells=int(rows.n.sum()), admitted_rows=len(frame))


def derive(frame, counts, masks, genes, effects_fn, recipe, output, *, chunk_targets=128):
    """One table per biological context; donor controls pooled before shrink.

    Disk chunks retain raw, shrunk and SE; sufficient statistics for a masked
    equal-target mean are saved without loading all target x gene arrays in RAM.
    Contexts and modalities are never silently averaged into a source vote.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    genes = np.asarray(genes).astype(str)
    if genes.ndim != 1 or len(set(genes)) != len(genes):
        raise ValueError('duplicate or malformed gene axis')
    if counts.ndim != 2 or counts.shape != masks.shape or counts.shape[1] != len(genes) or masks.dtype != bool:
        raise ValueError('matrix/axis/mask contract mismatch')
    if chunk_targets < 1:
        raise ValueError('positive chunk size required')
    contexts = []
    if frame.empty:
        return dict(contexts=[], target_cells_contributing=0, physical_cells_read=0)
    context_cols = [k for k in BIO if k != 'donor_or_clone']
    for number, (key, group) in enumerate(frame.groupby(context_cols, sort=True, dropna=False)):
        identity = dict(zip(context_cols, key))
        ctrl = group[group.target == 'non-targeting']
        targets = sorted(set(group.target) - {'non-targeting'})
        ctrl_donors = set(ctrl.donor_or_clone)
        missing_donors = sorted(set(group[group.target != 'non-targeting'].donor_or_clone) - ctrl_donors)
        receipt = dict(identity=identity, targets_expected=targets, controls_cells=int(ctrl.n.sum()),
                       donors=sorted(set(group.donor_or_clone)), chunks=[], targets_derived=[],
                       target_cells_contributing=0, estimator_rows_accessed=0,
                       status='ready', physical_cells_read=0)
        if ctrl.empty or missing_donors:
            receipt.update(status='blocked_matched_controls', donors_without_controls=missing_donors)
            contexts.append(receipt)
            continue
        indices = group.bank_row.to_numpy(dtype=int)
        # Intersection is computed only after held groups/components were removed.
        measured = np.ones(len(genes), dtype=bool)
        for start in range(0, len(indices), 256):
            measured &= masks[indices[start:start + 256]].all(axis=0)
        if not measured.any():
            raise ValueError('empty measured axis after split')
        sums = np.zeros(len(genes), dtype=np.float64)
        denominator = np.zeros(len(genes), dtype=np.int64)
        for start in range(0, len(targets), chunk_targets):
            wanted = targets[start:start + chunk_targets]
            batch = group[group.target.isin(['non-targeting', *wanted])]
            ix = batch.bank_row.to_numpy(dtype=int)
            x = np.asarray(counts[ix], dtype=np.float64)
            m = np.asarray(masks[ix])
            if not np.isfinite(x).all() or (x < 0).any() or (x[~m] != 0).any():
                raise ValueError('invalid observed counts')
            x = x[:, measured]
            if (x.sum(axis=1) <= 0).any():
                raise ValueError('zero observed library')
            obs = pd.DataFrame(dict(target=batch.target.to_list(), donor=batch.donor_or_clone.to_list(),
                condition=['scope'] * len(batch), n_cells=batch.n.to_numpy(dtype=float)))
            result = effects_fn(x, obs, genes[measured], targets=wanted, condition=None, **recipe)
            out_targets = [str(t) for t in result['targets']]
            if not out_targets:
                continue
            arrays = {k: np.full((len(out_targets), len(genes)), np.nan, dtype=np.float32) for k in ('raw', 'shrunk', 'se')}
            columns = np.flatnonzero(measured)[result['control_mean'] >= recipe['min_control_frac']]
            usable = result['control_mean'] >= recipe['min_control_frac']
            for k in arrays:
                arrays[k][:, columns] = result[k][:, usable]
            valid = np.isfinite(arrays['shrunk'])
            sums += np.where(valid, arrays['shrunk'], 0).sum(axis=0, dtype=np.float64)
            denominator += valid.sum(axis=0)
            path = output / ('context%03d_chunk%05d.npz' % (number, start))
            np.savez_compressed(path, genes=genes, targets=np.asarray(out_targets), mask=valid,
                n_cells=result['n_cells'], meta=np.asarray(json.dumps(identity)), **arrays)
            receipt['chunks'].append(dict(file=path.name, targets=len(out_targets)))
            receipt['targets_derived'].extend(out_targets)
            receipt['target_cells_contributing'] += int(np.asarray(result['n_cells']).sum())
            receipt['estimator_rows_accessed'] += len(batch)
        common_mask = denominator > 0
        common = np.divide(sums, denominator, out=np.zeros(len(genes)), where=common_mask)
        common_path = output / ('context%03d_common.npz' % number)
        np.savez_compressed(common_path, genes=genes, common=common, mask=common_mask,
                            contributing_targets=denominator)
        receipt.update(common_file=common_path.name, common_support_genes=int(common_mask.sum()),
            targets_below_estimator_eligibility=sorted(set(targets) - set(receipt['targets_derived'])),
            bank_rows_in_fold=indices.tolist(),
            units='natural-log fold change; fractions on context measured axis; original pseudocount and shrink',
            status='derived' if receipt['targets_derived'] else 'no_eligible_targets')
        contexts.append(receipt)
        # Incremental receipt survives interruption; complete marker is a separate runtime output.
        (output / ('context%03d_receipt.json' % number)).write_text(json.dumps(receipt, indent=2) + '\n')
    return dict(contexts=contexts, target_cells_contributing=sum(c['target_cells_contributing'] for c in contexts),
                physical_cells_read=0, scope='aggregated effects; no cellular training')
