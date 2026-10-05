"""Phase 2 of the extended t25 refit. Mix saved source fragments. This module does not push."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from source_policy import collapse_subcontexts

# Local import: phase 2 runs where the repository is present, after phase-1 outputs exist.
from vcc2026.multisource import AxisTable, mix  # noqa: E402


def _dump(payload):
    return json.dumps(payload, indent=1)


def save_extended_release(fragments, destination, *, missing, recipe, split_name, held_group):
    """Write effects, manifest and exposure for one split. Zeros stay the mix() contract."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    kept, held = [], []
    for item in fragments:
        if item.get('exclude_only_when_held', True) and item.get('line_group') == held_group:
            held.append(item['unit'])
            continue
        if not item.get('admitted_model', True):
            held.append(item['unit'])
            continue
        kept.append(item)
    if not kept:
        blocked = {
            'kind': 'extended_release_blocked', 'split': split_name, 'held_group': held_group,
            'reason': 'no admitted source remained after the split exclusion',
            'claims_complete_training': False, 'claims_complete_corpus': False, 'fit_admitted': False,
            'missing': list(missing),
        }
        (destination / 'BLOCKED.json').write_text(_dump(blocked), encoding='utf-8')
        return blocked
    grouped = {}
    pending = []
    for item in kept:
        grouped.setdefault(item['transfer_source_id'], []).append(item['table'])
        if item.get('distinct_study_pending_anchor'):
            pending.append(item['transfer_source_id'])
    collapsed = [collapse_subcontexts(parts, source_id) for source_id, parts in sorted(grouped.items())]
    targets = []
    seen = set()
    for table in collapsed:
        for target in table.targets:
            if target not in seen:
                seen.add(target)
                targets.append(target)
    weights = {table.name: float(recipe['source_weight']) for table in collapsed}
    if any(weight != 1.0 for weight in weights.values()):
        raise RuntimeError('source weight is not the frozen t25 weight')
    effects, denominator = mix(
        collapsed, targets, weights=weights, gamma=float(recipe['gamma']),
        reliability_scale=float(recipe['reliability_scale']))
    np.savez_compressed(
        destination / 'effects.npz',
        shrunk=np.asarray(effects, dtype=np.float32),
        denominator=np.asarray(denominator, dtype=np.float32),
        targets=np.asarray(targets))
    manifest = {
        'kind': 'extended_release_partial', 'split': split_name, 'held_group': held_group,
        'claims_complete_corpus': False, 'claims_complete_training': False, 'fit_admitted': False,
        'is_final_d053_catalogue': False, 'hybrid': False,
        'sources': [table.name for table in collapsed], 'weights': weights,
        'held_out_by_split': held, 'pending_anchor_sources': sorted(set(pending)),
        'missing': list(missing), 'recipe': recipe,
        'unmeasured_contract': 'mix() stores 0 where the denominator is 0; the denominator file separates that from a measured zero',
        'loss': None, 'optimizer': None, 'loss_applicable': False,
        'k562_essential_replaces_k562': False,
    }
    exposure = {
        'kind': 'exposure', 'n_sources': len(collapsed), 'n_targets': len(targets),
        'n_genes': int(collapsed[0].shrunk.shape[1]),
        'n_measured_pairs': int((np.asarray(denominator) > 0).sum()),
        'replaces_k562': False, 'pending_anchor_sources': sorted(set(pending)),
    }
    (destination / 'manifest.json').write_text(_dump(manifest), encoding='utf-8')
    (destination / 'exposure.json').write_text(_dump(exposure), encoding='utf-8')
    (destination / 'checkpoint.json').write_text(_dump({
        'split': split_name, 'sources': manifest['sources'], 'claims_complete_training': False,
    }), encoding='utf-8')
    return manifest


def load_split_fragments(root, split_name):
    """Read one phase-1 output directory. A missing unit is named, not skipped silently."""
    root = Path(root)
    slug = split_name.replace(':', '_').replace('/', '_')
    fragments, missing_units = [], []
    if not root.is_dir():
        return fragments, [str(root)]
    for unit_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        model_path = unit_dir / 'source_model.json'
        receipt_path = unit_dir / 'splits' / slug / 'receipt.json'
        if not model_path.is_file() or not receipt_path.is_file():
            missing_units.append(unit_dir.name)
            continue
        model = json.loads(model_path.read_text(encoding='utf-8'))
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('status') != 'derived' or not receipt.get('file'):
            missing_units.append(unit_dir.name + ':' + str(receipt.get('status')))
            continue
        loaded = np.load(unit_dir / receipt['file'])
        tables = (model.get('statistics') or [{}])[0].get('tables') or []
        if not tables:
            missing_units.append(unit_dir.name + ':no_table')
            continue
        table = tables[0]
        shrunk = np.asarray(loaded['0_shrunk'], dtype=np.float32)
        n_cells = np.asarray(loaded['0_n_cells'], dtype=np.float64)
        raw = np.asarray(loaded['0_raw'], dtype=np.float32) if '0_raw' in loaded.files else shrunk
        se = np.asarray(loaded['0_se'], dtype=np.float32) if '0_se' in loaded.files else np.full_like(shrunk, np.nan)
        fragments.append({
            'unit': model['unit'], 'transfer_source_id': model['transfer_source_id'],
            'line_group': model.get('line_group'), 'role': model.get('role', 'transfer'),
            'admitted_model': model.get('admitted_model', True),
            'exclude_only_when_held': model.get('exclude_only_when_held', True),
            'distinct_study_pending_anchor': model.get('distinct_study_pending_anchor', False),
            'replaces_k562': model.get('replaces_k562', False),
            'table': AxisTable(table.get('name') or model['transfer_source_id'], list(table['targets']),
                               shrunk, raw, se, n_cells, dict(table.get('meta') or {})),
        })
    return fragments, missing_units


def write_prerequisite(path):
    payload = {
        'phase': 2, 'push_now': False,
        'prerequisite_file': 'phase-1 outputs: source_model.json and statistics/*.npz from each package in ready_dispatch.json',
        'action': 'Parent pushes the phase-1 packages after a fresh preflight. When those kernels finish, run this script with the output directory as the first argument and a new directory as the second.',
        'does_not_block_phase_1': True, 'claims_complete_training': False,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(payload), encoding='utf-8')
    return payload


def main(argv):
    here = Path(__file__).resolve().parent
    if len(argv) < 3:
        write_prerequisite(here / 'release_phase2' / 'PREREQUISITE.json')
        print('phase2_waiting_for_phase1_outputs')
        return 0
    split_name = argv[3] if len(argv) > 3 else 'C:K562'
    held = split_name.split(':')[1] if ':' in split_name else split_name
    fragments, missing_units = load_split_fragments(Path(argv[1]), split_name)
    recipe_path = here / 'ready_dispatch.json'
    if not recipe_path.is_file():
        raise SystemExit('ready_dispatch.json is absent; phase 1 was not packaged')
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))['model']
    missing = list(missing_units)
    missing.append('k562 GWPS parent job is not an output of this wave')
    manifest = save_extended_release(
        fragments, Path(argv[2]), missing=missing, recipe=recipe, split_name=split_name, held_group=held)
    print(json.dumps({'status': manifest['kind'], 'sources': manifest.get('sources', [])}))
    return 0


if __name__ == '__main__':
    import sys
    main(sys.argv)
