"""Original t25 arm, expanded arm, and the cloud path. A full fit still fails closed."""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np

from pins import (AMPLITUDE, FORBIDDEN_DATASET, GAMMA, ORIGINAL_SOURCES, RELIABILITY_SCALE,
                  REPO, SOURCE_WEIGHT, STORAGE_SHA256)
from split_rule import LINE_GROUPS, PROVENANCE

sys.path.insert(0, str(REPO / 'src'))
from source_policy import collapse_subcontexts  # noqa: E402
from vcc2026.multisource import AxisTable, mix  # noqa: E402


class FitBlocked(RuntimeError):
    def __init__(self, blockers):
        self.blockers = list(blockers)
        super().__init__(self.blockers[0] if self.blockers else 'fit blocked')


def drop_hidden(table, hidden, component_map):
    hidden = set(map(str, hidden))
    keep = []
    for target in table.targets:
        if target not in component_map:
            raise FitBlocked(['target without an explicit component map: ' + target])
        if set(map(str, component_map[target])) & hidden:
            continue
        keep.append(target)
    if len(keep) == len(table.targets):
        return table
    index = [table.targets.index(target) for target in keep]
    return AxisTable(table.name, keep, table.shrunk[index], table.raw[index], table.se[index],
                     table.n_cells[index], dict(table.meta))


def _collapse_arm(tables):
    grouped = defaultdict(list)
    for table in tables:
        grouped[table.meta.get('transfer_source_id', table.name)].append(table)
    return [collapse_subcontexts(parts, source_id) for source_id, parts in sorted(grouped.items())]


def mix_arm(tables, targets, source_names, component_map, hidden_targets=()):
    collapsed = _collapse_arm(tables)
    names = [table.name for table in collapsed]
    if len(names) != len(set(names)) or set(names) != set(source_names):
        raise FitBlocked(['source set does not match the requested arm: ' + ','.join(names)])
    cleaned = [drop_hidden(table, hidden_targets, component_map) for table in collapsed]
    weights = {name: SOURCE_WEIGHT for name in source_names}
    if any(weight != 1.0 for weight in weights.values()):
        raise FitBlocked(['source weight is not the frozen t25 weight'])
    effects, denominator = mix(cleaned, list(targets), weights=weights, gamma=GAMMA,
                               reliability_scale=RELIABILITY_SCALE)
    return effects * AMPLITUDE, denominator


def assert_fit_allowed(admission):
    blockers = []
    if admission.get('storage_sha256') != STORAGE_SHA256:
        blockers.append('storage hash mismatch')
    if admission.get('fit_admitted') is not True:
        blockers.extend(admission.get('blockers') or ['fit_admitted is not true'])
    open_records = [row['record_id'] for row in admission.get('records', []) if row.get('role') == 'open']
    if open_records:
        blockers.append('open catalogue records: ' + str(len(open_records)))
    for item in admission.get('fit_inputs', []):
        blob = item.get('dataset', '') + item.get('kernel', '')
        if FORBIDDEN_DATASET in blob:
            blockers.append('forbidden dataset ' + FORBIDDEN_DATASET)
        for field in ('dataset', 'version', 'receipt_sha256', 'producer', 'matrix'):
            if not item.get(field):
                blockers.append('fit input missing ' + field)
        if item.get('matrix') != 'count_sum':
            blockers.append('fit input is not count_sum')
        if not item.get('transfer_source_id'):
            blockers.append('fit input has no explicit transfer_source_id')
    if blockers:
        raise FitBlocked(blockers)
    return True


def run_refit(admission, tables_by_arm, targets, component_map, *, allow_local_fit=False, launcher=None):
    """An admitted corpus is fitted in the cloud unless the caller names a tiny local fixture."""
    assert_fit_allowed(admission)
    expected = set(admission['required_context_ids'])
    present = set(admission.get('loaded_context_ids', []))
    if expected != present:
        raise FitBlocked(['context coverage mismatch'])
    if not allow_local_fit:
        if launcher is None:
            raise FitBlocked(['admitted corpus requires the cloud launcher'])
        return launcher.launch_full_fit(admission)
    original = mix_arm(tables_by_arm['original'], targets, list(ORIGINAL_SOURCES), component_map,
                       admission.get('hidden_targets', ()))
    expanded_names = list(admission['expanded_source_names'])
    if not set(ORIGINAL_SOURCES).issubset(expanded_names):
        raise FitBlocked(['expanded arm dropped an original t25 source'])
    expanded = mix_arm(tables_by_arm['expanded'], targets, expanded_names, component_map,
                       admission.get('hidden_targets', ()))
    return {'original': original, 'expanded': expanded, 'emission': admission['emission']}


def cloud_params_refused(params):
    blockers = []
    if params.get('storage_sha256') != STORAGE_SHA256:
        blockers.append('cloud fit refused: storage hash')
    if params.get('fit_admitted') is not True:
        blockers.append('cloud fit refused: fit_admitted is not true')
    if params.get('matrix') != 'count_sum':
        blockers.append('cloud fit refused: matrix is not count_sum')
    if FORBIDDEN_DATASET in json.dumps(params.get('inputs', [])):
        blockers.append('cloud fit refused: forbidden dataset')
    if blockers:
        raise FitBlocked(blockers)
    return True


def preparation_allowed(plan):
    """A derivation plan is not a full fit. Splits and the axis are part of the plan."""
    if plan.get('kind') != 'technical_preparation':
        raise FitBlocked(['derivation must be named technical_preparation'])
    if plan.get('claims_complete_training'):
        raise FitBlocked(['a preparation job is not the extended training'])
    if plan.get('matrix') != 'count_sum':
        raise FitBlocked(['preparation matrix is not count_sum'])
    if plan.get('storage_sha256') != STORAGE_SHA256:
        raise FitBlocked(['preparation storage hash is not r10'])
    if FORBIDDEN_DATASET in json.dumps(plan):
        raise FitBlocked(['forbidden dataset'])
    splits = plan.get('splits') or {}
    if list(splits.get('line_groups') or []) != list(LINE_GROUPS) or splits.get('provenance') != PROVENANCE:
        raise FitBlocked(['preparation splits are not the frozen registry groups'])
    if not plan.get('global_hidden_targets') and plan.get('global_hidden_targets') != []:
        raise FitBlocked(['preparation has no global hidden-target list'])
    axis = plan.get('axis') or {}
    for field in ('sha256', 'genes', 'relative_path', 'bytes', 'dataset'):
        if not axis.get(field):
            raise FitBlocked(['preparation axis missing ' + field])
    if not plan.get('code_sha256') or not plan.get('units'):
        raise FitBlocked(['preparation has no code hash or unit'])
    for unit in plan['units']:
        for field in ('unit', 'kernel', 'owner', 'count_sum_sha256', 'rows_sha256', 'mask_sha256',
                      'transfer_source_id', 'relative_path', 'line_group', 'version'):
            if not unit.get(field):
                raise FitBlocked(['preparation unit missing ' + field])
        if (unit.get('component_policy') or {}).get('name') != 'bound_axis_membership':
            raise FitBlocked(['component policy is not bound to the axis'])
        if 'gwps' in unit['kernel']:
            raise FitBlocked(['K562 GWPS must not be duplicated'])
    return True
