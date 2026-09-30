"""Extend frozen transfer row coverage, with exact parity on all existing rows.

No destination perturbed counts, scoring, model, source-effect refit or changed
centring. Only evidence masks are reconstructed by the original generator code.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import stack_pilot as pilot
from stack_confirmation_pack import EXPECTED

HERE = Path(__file__).resolve().parent
GENERATOR_SHA = 'e959e6874a4a35e9d3dd6ebb64aec4230f2918d1de1eb3d11a031a9ff0f6bae6'
EFFECTS_SHA = 'a8d7e65c7b9ea6f9933b474628160b1167c5a229eb744dabd42912b097206169'
BULK_SHA = '7cec96b3b76169abbf6b6ab9d10bf00d71d942d89e63292351f745e130b154db'
MANIFEST_SHA = '7b7459ca86d0bef53d4a53f3b7bcae983189a44f623deb2510d7ed33da07d79f'


def checked_rows(targets, wanted):
    index = pd.Index(np.asarray(targets).astype(str))
    if not index.is_unique or len(set(wanted)) != len(wanted):
        raise ValueError('Duplicate transfer target axis')
    pos = index.get_indexer(wanted)
    if np.any(pos < 0):
        raise ValueError('Frozen full transfer lacks target: ' + ','.join(np.asarray(wanted)[pos < 0]))
    return pos


def derive(generator, full_targets, full_genes, full_lfc, mask, selected, genes):
    pos = checked_rows(full_targets, selected)
    if mask.shape != (len(selected), len(full_genes)) or mask.dtype.kind != 'b':
        raise ValueError('Evidence mask shape/dtype differs')
    return generator.map_effects(full_genes, full_lfc[pos], mask, genes)


def exact_existing(genes, values, mask, selected, path):
    with np.load(path, allow_pickle=False) as old:
        if list(old['genes'].astype(str)) != list(genes):
            raise ValueError('Existing transfer response axis differs')
        pos = checked_rows(selected, old['targets'].astype(str).tolist())
        if not np.array_equal(values[pos], old['lfc']) or not np.array_equal(mask[pos], old['observed']):
            raise ValueError('Existing frozen transfer values or observed mask changed')
        return len(pos)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('effects', 'bulk', 'generator-manifest', 'prepared-effects', 'pilot-bundle', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    generator_path = HERE.parent / 'generator_bench.py'
    for path, wanted in ((generator_path, GENERATOR_SHA), (a.effects, EFFECTS_SHA),
                         (a.bulk, BULK_SHA), (a.generator_manifest, MANIFEST_SHA)):
        if pilot.sha(path) != wanted:
            raise ValueError('Frozen input changed: ' + str(path))
    manifest = json.loads(a.generator_manifest.read_text(encoding='utf-8'))
    if pilot.sha(a.prepared_effects) != manifest['prepared_effects_sha256']:
        raise ValueError('Existing prepared effects changed')
    spec = importlib.util.spec_from_file_location('frozen_generator_for_stack_masks', generator_path)
    generator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = generator
    spec.loader.exec_module(generator)
    if pilot.sha(generator.REPO / 'scripts/98_multisource_effects.py') != manifest['source_mask']['source_stage_sha256']:
        raise ValueError('Original mask stage changed')
    # Mask dependencies must be the exact ones used for the generator preparation.
    fingerprints = manifest['fingerprints']
    dependency_hashes = {}
    for relative in ('src/vcc2026/multisource.py', 'src/vcc2026/predictor_sc.py'):
        old = [v['sha256'] for k, v in fingerprints.items() if k.endswith('/' + relative)]
        if len(old) != 1 or pilot.sha(generator.REPO / relative) != old[0]:
            raise ValueError('Frozen mask dependency changed: ' + relative)
        dependency_hashes[relative] = old[0]
    old_bundle = json.loads((a.pilot_bundle / 'bundle.json').read_text(encoding='utf-8'))
    for name in ('transfer.npz', 'destination_controls.h5ad'):
        if pilot.sha(a.pilot_bundle / name) != old_bundle['files'][name]:
            raise ValueError('Pilot input changed: ' + name)
    with np.load(a.prepared_effects, allow_pickle=False) as old:
        previous = old['targets'].astype(str).tolist()
        genes = old['genes'].astype(str)
    if previous != manifest['development'] + manifest['confirmation']:
        raise ValueError('Existing prepared rows do not match the registered splits')
    if set(previous) & set(EXPECTED):
        raise ValueError('Confirmation reserve overlaps generator splits')
    if list(genes) != list(pilot.genes_of(a.pilot_bundle / 'destination_controls.h5ad')):
        raise ValueError('Destination response axis differs from original pilot')
    selected = previous + EXPECTED
    with np.load(a.effects, allow_pickle=False) as full:
        full_targets, full_genes = full['targets'].astype(str), full['genes'].astype(str)
        full_lfc = full['lfc'].copy()
        if 'observed' in full:
            raise ValueError('Original t19like unexpectedly has an observed mask')
    checked_rows(full_targets, selected)
    mask, mask_metadata = generator.source_mask(a.bulk, selected, full_genes)
    values, mask = derive(generator, full_targets, full_genes, full_lfc, mask, selected, genes)
    checked_previous = exact_existing(genes, values, mask, selected, a.prepared_effects)
    checked_pilot = exact_existing(genes, values, mask, selected, a.pilot_bundle / 'transfer.npz')
    reserve = checked_rows(selected, EXPECTED)
    a.out.mkdir(parents=True)
    output = a.out / 'confirmation_effects.npz'
    np.savez_compressed(output, targets=np.asarray(EXPECTED, dtype=str), genes=np.asarray(genes, dtype=str),
                        lfc=values[reserve], observed=mask[reserve])
    # This opens every array without pickle, including the response axis.
    exact_existing(genes, values, mask, selected, output)
    sources = (a.effects, a.bulk, a.generator_manifest, a.prepared_effects,
               a.pilot_bundle / 'transfer.npz', a.pilot_bundle / 'bundle.json', generator_path, Path(__file__))
    pilot.write_json(a.out / 'manifest.json', {
        'status': 'extended_row_coverage_exact_existing_parity_no_scores',
        'utc': datetime.now(timezone.utc).isoformat(), 'targets': EXPECTED,
        'existing_generator_rows_bit_exact': checked_previous, 'existing_pilot_rows_bit_exact': checked_pilot,
        'values': 'Original t19like natural-log effects selected only; no refit or recentering',
        'mask': mask_metadata, 'mask_dependency_hashes': dependency_hashes,
        'destination_perturbed_rows_read': 0,
        'output_sha256': pilot.sha(output),
        'inputs': {str(x): {'bytes': x.stat().st_size, 'sha256': pilot.sha(x)} for x in sources}})
    print(json.dumps({'out': str(a.out), 'reserve_targets': len(EXPECTED),
                      'parity_generator': checked_previous, 'parity_pilot': checked_pilot}))


if __name__ == '__main__':
    main()
