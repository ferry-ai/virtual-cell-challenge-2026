"""Original t25 transfer versus an expanded source set. Fails closed before any fit."""
from __future__ import annotations

import json
import sys

import numpy as np

from pins import (AMPLITUDE, FORBIDDEN_DATASET, GAMMA, MANIFEST_SHA256, ORIGINAL_SOURCES,
                  RELIABILITY_SCALE, REPO, SOURCE_WEIGHT)

sys.path.insert(0, str(REPO / 'src'))
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


def mix_arm(tables, targets, source_names, component_map, hidden_targets=()):
    names = [table.name for table in tables]
    if len(names) != len(set(names)) or set(names) != set(source_names):
        raise FitBlocked(['source set does not match the requested arm'])
    cleaned = [drop_hidden(table, hidden_targets, component_map) for table in tables]
    weights = {name: SOURCE_WEIGHT for name in source_names}
    if any(weight != 1.0 for weight in weights.values()):
        raise FitBlocked(['source weight is not the frozen t25 weight'])
    effects, denominator = mix(cleaned, list(targets), weights=weights, gamma=GAMMA,
                               reliability_scale=RELIABILITY_SCALE)
    return effects * AMPLITUDE, denominator


def assert_fit_allowed(admission):
    blockers = []
    if admission.get('manifest_sha256') != MANIFEST_SHA256:
        blockers.append('manifest hash mismatch')
    if admission.get('fit_admitted') is not True:
        blockers.extend(admission.get('blockers') or ['fit_admitted is not true'])
    unresolved = [row['record_id'] for row in admission.get('records', []) if row.get('role') == 'unresolved']
    if unresolved:
        blockers.append('unresolved catalogue roles: ' + str(len(unresolved)))
    for item in admission.get('fit_inputs', []):
        if FORBIDDEN_DATASET in item.get('dataset', '') or FORBIDDEN_DATASET in item.get('kernel', ''):
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


def run_refit(admission, tables_by_arm, targets, component_map, *, allow_local_fit=False):
    """Gate first. A laptop fit is allowed only for an explicit tiny fixture."""
    assert_fit_allowed(admission)
    expected = set(admission['required_context_ids'])
    present = set(admission.get('loaded_context_ids', []))
    if expected != present:
        raise FitBlocked(['context coverage mismatch'])
    if not allow_local_fit:
        raise FitBlocked(['admitted corpus is a CPU-cloud fit, not a laptop fit'])
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
    if params.get('manifest_sha256') != MANIFEST_SHA256:
        blockers.append('cloud fit refused: manifest hash')
    if params.get('fit_admitted') is not True:
        blockers.append('cloud fit refused: fit_admitted is not true')
    if params.get('matrix') != 'count_sum':
        blockers.append('cloud fit refused: matrix is not count_sum')
    blob = json.dumps(params.get('inputs', []))
    if FORBIDDEN_DATASET in blob:
        blockers.append('cloud fit refused: forbidden dataset')
    if blockers:
        raise FitBlocked(blockers)
    return True


def refuse(admission, destination):
    try:
        assert_fit_allowed(admission)
    except FitBlocked as error:
        payload = {'fit_launched': False, 'blockers': error.blockers}
        destination.write_text(json.dumps(payload, indent=1), encoding='utf-8')
        return payload
    raise RuntimeError('refusing to launch from an admission that passed the gate without a cloud plan')
