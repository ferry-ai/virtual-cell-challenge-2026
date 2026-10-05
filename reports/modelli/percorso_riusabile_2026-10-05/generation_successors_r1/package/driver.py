"""Cloud generation driver. Mounts the retry mix and runs stages 100, 45 and 48.

Does not push, does not download a bank, and does not fall back to an older cache.
The product is one prediction .vcc. effects.npz is never a recipe source.
"""
from __future__ import annotations
import shutil

import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

import generate_contract as contract

WORKING = Path('/kaggle/working')
INPUTS = Path('/kaggle/input')
TEMP = Path('/kaggle/temp')
FINAL_NAME = 'prediction.vcc'


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path, payload):
    Path(path).write_text(contract.dumps(payload) + '\n', encoding='utf-8')


def _fail(status, **fields):
    _write(WORKING / 'status.json', {
        'status': status, 'usable_export': False, 'training_ready': False,
        'fit_ready': False, 'fit_admitted': False, 'loss': None, 'optimizer': None,
        'product': None, **fields,
    })
    raise SystemExit(2)


def _verify_embedded(params):
    root = WORKING
    for rel, digest in params['embedded_sha256'].items():
        path = root / rel
        if not path.is_file() or _sha256(path) != digest:
            _fail('blocked_embedded_sha256', path=rel)


def _find_mix():
    hits = [path for path in INPUTS.rglob('source_model.json') if contract.mix_dir_allowed(path)]
    refused = [path for path in INPUTS.rglob('source_model.json') if contract.REFUSE_DIR in path.parts]
    if refused:
        _fail('blocked_error_producer', paths=[str(path) for path in refused])
    if len(hits) != 1:
        _fail('blocked_mix_not_ready', found=len(hits), expected_directory=contract.MOUNT_DIR)
    model_dir = hits[0].parent
    cache = model_dir / 'cache'
    if not cache.is_dir():
        _fail('blocked_mix_cache_missing', model_dir=str(model_dir))
    return model_dir, cache


def _load_meta(handle):
    return json.loads(str(handle['meta']))


def _prepare_cache(cache, voted):
    import numpy as np
    dest = WORKING / 'cache_voted'
    dest.mkdir()
    origin = {}
    for name in voted:
        path = cache / (name + '.npz')
        override = json.loads((WORKING / 'params.json').read_text()).get('source_overrides', {}).get(name)
        if override:
            receipts = [p for p in INPUTS.rglob('cache_receipt.json') if _sha256(p) == override['receipt_sha256']]
            hits = [p for p in INPUTS.rglob(name + '.npz') if p.stat().st_size == override['bytes'] and _sha256(p) == override['sha256']]
            if len(receipts) != 1 or len(hits) != 1:
                _fail('blocked_corrected_source_identity', source=name, receipts=len(receipts), candidates=len(hits))
            path = hits[0]

        if name == 'k562':
            hits = list(INPUTS.rglob('k562.npz.bin'))
            if len(hits) != 1 or _sha256(hits[0]) != 'a37c78ce1f7c13a3fc145e75e64f2ccead555ec8e38a656d671903ed4fd7218f':
                _fail('blocked_k562_historical_identity')
            path = hits[0]
        if not path.is_file():
            _fail('blocked_voted_table_missing', source=name)
        with np.load(path, allow_pickle=False) as handle:
            keys = tuple(handle.files)
            meta = _load_meta(handle)
            contract.require_table_arrays(name, keys, handle['shrunk'], handle['raw'], handle['se'], meta)
            if name == 'cd4_mix':
                for part in meta['from']:
                    part_path = cache / (part + '.npz')
                    if not part_path.is_file():
                        _fail('blocked_cd4_part_missing', source=part)
                    origin[part] = {'role': 'cd4_condition_not_a_second_vote', 'sha256': _sha256(part_path),
                                    'bytes': part_path.stat().st_size}
        os.symlink(path, dest / (name + '.npz'))
        origin[name] = {'role': 'voted', 'sha256': _sha256(path), 'bytes': path.stat().st_size, 'successor': override}
    return dest, origin


def _one_named(root, filename):
    return [path for path in Path(root).rglob(filename) if path.is_file()]


def _link_controls(params):
    controls = WORKING / 'data' / 'raw' / 'controls'
    pins = params['controls']['sha256']
    linked = {}
    for filename, digest in pins.items():
        hits = _one_named(INPUTS, filename)
        matches = [path for path in hits if _sha256(path) == digest]
        if len(matches) != 1:
            _fail('blocked_controls_not_mounted', file=filename, candidates=len(hits),
                  matched=len(matches), note=params['controls']['note'])
        dest = controls / filename
        if dest.exists() or dest.is_symlink():
            _fail('blocked_controls_destination', file=filename)
        os.symlink(matches[0], dest)
        linked[filename] = str(matches[0])
    return linked


def _check_axis(params):
    embedded = WORKING / 'data' / 'raw' / 'controls' / 'gene_names.csv'
    if _sha256(embedded) != contract.AXIS_SHA256:
        _fail('blocked_axis_sha256')
    for path in _one_named(INPUTS, 'gene_names.csv'):
        if _sha256(path) != contract.AXIS_SHA256:
            _fail('blocked_mounted_axis_sha256', path=str(path))


def _resources(path):
    sys.path.insert(0, str(WORKING / 'repo' / 'src'))
    os.environ['VCC2026_DATA_ROOT'] = str(WORKING / 'data')
    os.environ['VCC2026_ARTIFACT_ROOT'] = str(TEMP / 'artifacts')
    from vcc2026.resources import snapshot
    return snapshot(path).as_dict()


def _guard_resources():
    TEMP.mkdir(parents=True, exist_ok=True)
    working = _resources(WORKING)
    scratch = _resources(TEMP)
    available = working.get('ram_available_bytes')
    if available is not None and available < contract.RAM_BUDGET_BYTES:
        _fail('blocked_ram', working=working, scratch=scratch, ram_budget_bytes=contract.RAM_BUDGET_BYTES)
    if working.get('disk_free_bytes', 0) < contract.OUTPUT_BUDGET_BYTES:
        _fail('blocked_output_disk', working=working, scratch=scratch,
              output_budget_bytes=contract.OUTPUT_BUDGET_BYTES)
    if scratch.get('disk_free_bytes', 0) < contract.OUTPUT_BUDGET_BYTES:
        _fail('blocked_scratch_disk', working=working, scratch=scratch,
              output_budget_bytes=contract.OUTPUT_BUDGET_BYTES)
    return {'working': working, 'scratch': scratch,
            'stage45_reserve_gib': contract.STAGE45_RESERVE_GIB,
            'stage48_reserve_gib': contract.STAGE48_RESERVE_GIB,
            'note': 'stages 45 and 48 still apply their own reserves; the full run wants about 17 GiB free'}


def _run_script(script, argv):
    old = sys.argv[:]
    sys.argv = [str(script), *list(argv)]
    try:
        runpy.run_path(str(script), run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    finally:
        sys.argv = old


def _compact(diagnostics):
    shape = diagnostics.get('shape') or {}
    provenance = diagnostics.get('context_provenance') or {}
    return {
        'run_id': diagnostics.get('run_id'),
        'trial': diagnostics.get('trial'),
        'seed': diagnostics.get('seed'),
        'is_pilot': diagnostics.get('is_pilot'),
        'shape': shape,
        'context_provenance_ok': provenance.get('all_labels_match_nearest_basal'),
        'storage': diagnostics.get('storage'),
        'runtime': diagnostics.get('runtime'),
        'memory': diagnostics.get('memory'),
        'not_a_score': diagnostics.get('not_a_score'),
        'per_block_omitted': True,
    }



def _verify_mix_checkpoint(model_dir):
    checkpoint = model_dir / 'checkpoint.json'
    if _sha256(checkpoint) != 'aa051ea44a299898ab908c99c2c6c23afb1f1cffb2e184a968944cc80cb321d0':
        _fail('blocked_producer_checkpoint_identity')
    receipt = json.loads(checkpoint.read_text())
    for item in receipt['files']:
        rel = Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts:
            _fail('blocked_producer_relative_path')
        path = model_dir / rel
        if not path.is_file() or path.stat().st_size != item['bytes'] or _sha256(path) != item['sha256']:
            _fail('blocked_producer_file_hash', file=item['path'])

def main():
    os.chdir(WORKING)
    sys.path.insert(0, str(WORKING))
    params = json.loads((WORKING / 'params.json').read_text(encoding='utf-8'))
    if params.get('mount_slug') != contract.MOUNT_SLUG:
        _fail('blocked_params_mount')
    coords_hits = list(INPUTS.rglob('gene_coordinates_gencode_v50.tsv'))
    if len(coords_hits) != 1 or _sha256(coords_hits[0]) != '065906f739094c6ae572d21c0b14e7b8f2d4daa0284cdb68864ed27b9caba34c':
        _fail('blocked_coordinates_identity')
    (WORKING / 'data/external/annotation').mkdir(parents=True, exist_ok=True)
    (WORKING / 'data/external/annotation/gene_coordinates_gencode_v50.tsv').write_bytes(coords_hits[0].read_bytes())
    _verify_embedded(params)
    _check_axis(params)
    try:
        import numpy  # noqa: F401
        import pandas  # noqa: F401
        import h5py  # noqa: F401
        import yaml  # noqa: F401
        import anndata  # noqa: F401
        import zstandard  # noqa: F401
    except ImportError as exc:
        _fail('blocked_image_import', missing=str(exc))
    resources = _guard_resources()
    linked = {} if params.get('effects_only') else _link_controls(params)
    model_dir, cache = _find_mix()
    _verify_mix_checkpoint(model_dir)
    document = json.loads((model_dir / 'source_model.json').read_text(encoding='utf-8'))
    try:
        recipe = contract.accept_source_model(document)
        for context in recipe['contexts'].values():
            context['weights']['k562'] = 1.0
            for name in params['source_overrides']:
                context['weights'][name] = 1.0
    except ValueError as exc:
        _fail('blocked_source_model', reason=str(exc))
    voted = sorted({name for ctx in recipe['contexts'].values() for name in ctx['weights']})
    voted_cache, origin = _prepare_cache(cache, voted)
    recipe_path = WORKING / 'recipe_extbank.json'
    recipe_path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
    recipe_sha = _sha256(recipe_path)
    record = {
        'registered_before_stage100': True,
        'recipe_sha256': recipe_sha,
        'voted_sources': voted,
        'origin': origin,
        'emission': contract.emission(),
        'reading_rule': contract.reading_rule(),
        'amplitude_applied_in_mix': False,
        'cis_applied_in_mix': False,
        'effects_scale_applied_in_mix': False,
        'k562_in_recipe': True,
        'k562_essential_is_not_k562': True,
        'training_ready': False,
        'fit_ready': False,
        'loss': None,
        'optimizer': None,
        'controls_linked': linked,
        'resources_before': resources,
        'product_will_be': FINAL_NAME,
    }
    _write(WORKING / 'prediction_record.json', record)
    sys.path.insert(0, str(WORKING / 'vendor'))
    data = WORKING / 'data'
    effects = TEMP / 'stage100'
    generated = TEMP / 'stage45'
    _run_script(WORKING / 'repo' / 'scripts' / '100_build_context_effects.py', [
        '--recipe', str(recipe_path),
        '--cache', str(voted_cache),
        '--targets-csv', str(data / 'raw' / 'controls' / 'pert_counts.csv'),
        '--coords', str(data / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv'),
        '--contexts', 'A,B,C',
        '--out', str(effects),
    ])
    if params.get('effects_only'):
        destination = WORKING / 'effects'
        shutil.copytree(effects, destination)
        _write(WORKING / 'status.json', {'status': 'effects_ready', 'usable_export': True,
          'registered_sources': voted, 'k562_historical_sha256': 'a37c78ce1f7c13a3fc145e75e64f2ccead555ec8e38a656d671903ed4fd7218f',
          'catalogue_complete': False, 'controls_h5ad_uploaded': False,
          'recipe_sha256': recipe_sha, 'scope': 'production; not held-out C/J'})
        return
    _run_script(WORKING / 'repo' / 'scripts' / '45_generate_prediction.py', [
        '--run-id', 'gen-extbank-r1',
        '--trial', contract.TRIAL,
        '--out', str(generated),
        '--controls-dir', str(data / 'raw' / 'controls'),
        '--cells-per-pert', str(contract.CELLS_PER_TARGET),
        '--seed', str(contract.GENERATOR_SEED),
        '--gene-dispersion',
        '--gene-dispersion-scale', str(contract.GENE_DISPERSION_SCALE),
        '--effects-scale', str(contract.EFFECTS_SCALE),
        '--reserve-gib', str(contract.STAGE45_RESERVE_GIB),
        '--effects', 'A=' + str(effects / 'effects_A.npz'),
        '--effects', 'B=' + str(effects / 'effects_B.npz'),
        '--effects', 'C=' + str(effects / 'effects_C.npz'),
    ])
    diagnostics = json.loads((generated / 'generation_diagnostics.json').read_text(encoding='utf-8'))
    compact = _compact(diagnostics)
    _write(WORKING / 'compact_diagnostics.json', compact)
    shape = compact.get('shape') or {}
    if compact.get('is_pilot') or shape.get('n_perturbations') != contract.PANEL_N:
        _fail('blocked_shape', compact=compact)
    if shape.get('cells_per_pert') != contract.CELLS_PER_TARGET or shape.get('n_cells') != 360000:
        _fail('blocked_shape', compact=compact)
    if list(shape.get('contexts') or []) != list(contract.CONTEXTS):
        _fail('blocked_shape', compact=compact)
    if compact.get('context_provenance_ok') is not True:
        _fail('blocked_context_provenance', compact=compact)
    if compact.get('seed') != contract.GENERATOR_SEED:
        _fail('blocked_seed', compact=compact)
    prediction = generated / 'prediction.h5ad'
    _run_script(WORKING / 'repo' / 'scripts' / '48_package_prediction.py', [
        '--run-id', 'gen-extbank-r1',
        '--prediction', str(prediction),
        '--out', str(WORKING),
        '--vcc-name', FINAL_NAME,
        '--workdir', str(TEMP / 'pack'),
        '--genes', str(data / 'raw' / 'controls' / 'gene_names.csv'),
        '--perts', str(data / 'raw' / 'controls' / 'pert_counts.csv'),
        '--contexts', 'A,B,C',
        '--reserve-gib', str(contract.STAGE48_RESERVE_GIB),
    ])
    product = WORKING / FINAL_NAME
    if not product.is_file():
        _fail('blocked_vcc_missing')
    digest = _sha256(product)
    _write(WORKING / 'generation_manifest.json', {
        'product': FINAL_NAME,
        'sha256': digest,
        'bytes': product.stat().st_size,
        'recipe_sha256': recipe_sha,
        'voted_sources': voted,
        'retrieval': 'parent uploads this one .vcc; nothing in this kernel uploads',
        'training_ready': False,
        'fit_ready': False,
        'loss': None,
        'optimizer': None,
        'local_score': None,
    })
    _write(WORKING / 'status.json', {
        'status': 'vcc_ready_for_parent_upload',
        'usable_export': True,
        'training_ready': False,
        'fit_ready': False,
        'fit_admitted': False,
        'loss': None,
        'optimizer': None,
        'product': FINAL_NAME,
        'sha256': digest,
    })


if __name__ == '__main__':
    main()
