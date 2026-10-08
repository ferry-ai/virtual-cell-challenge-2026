"""Leave-one-lineage-out bench of the unchanged stage-100 transfer on a frozen source release.

Level A of the independent validation (contract v1). For every arm of the frozen fold manifest and every
C fold, the production stage 100 is run on a cache that physically lacks the tables of the held lineage,
and its prediction is compared, target by target, with the held lineage's own table. Nothing is trained,
generated, packaged or submitted. The numbers are effect-space proxies on development lineages: not VCC
scores and not an independent confirmation.

The run:
1. verifies every embedded file, the axis, the panel, the frozen manifest and the mounted mix checkpoint,
   and resolves every source of the release by its pinned bytes and sha256 (as the fit of release r1 does);
2. PARITY: with no exclusion, the effects of T0, R1 and T1 must reproduce the sha256 recorded by the
   production fits; otherwise the bench stops before any comparison;
3. FOLDS: one stage-100 run per (arm, fold) on a reduced cache; the list of files stage 100 hashed must be
   exactly the allowed sources, and none may belong to the held lineage;
4. MEASURES: `metrics.py` per target, the declared contrasts with a paired bootstrap over targets, the
   controls (shuffled targets, null, mean only, gamma 0, no cis) and the audits of duplicated experiments
   and of votes per lineage.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import generate_contract as contract

WORKING = Path('/kaggle/working')
INPUTS = Path('/kaggle/input')
TEMP = Path('/kaggle/temp')
VARIANTS = {'': {}, 'gamma0': {'gamma': 0.0}, 'nocis': {'cis': None}}
T0 = time.monotonic()


def _log(message):
    print('[%7.1fs] %s' % (time.monotonic() - T0, message), flush=True)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, default=float) + '\n', encoding='utf-8')


def _fail(status, **fields):
    _write(WORKING / 'status.json', {'status': status, 'usable': False, **fields})
    _log('FAILED: %s %s' % (status, json.dumps(fields, default=str)[:600]))
    raise SystemExit(2)


# --- the next five functions are the fit driver of release r1, unchanged in what they verify ---------------

def _verify_embedded(params):
    for rel, digest in params['embedded_sha256'].items():
        path = WORKING / rel
        if not path.is_file() or _sha256(path) != digest:
            _fail('blocked_embedded_sha256', path=rel)


def _check_axis():
    embedded = WORKING / 'data' / 'raw' / 'controls' / 'gene_names.csv'
    if _sha256(embedded) != contract.AXIS_SHA256:
        _fail('blocked_axis_sha256')
    panel = WORKING / 'data' / 'raw' / 'controls' / 'pert_counts.csv'
    if _sha256(panel) != contract.PANEL_FILE_SHA256:
        _fail('blocked_panel_sha256')
    for path in INPUTS.rglob('gene_names.csv'):
        if _sha256(path) != contract.AXIS_SHA256:
            _fail('blocked_mounted_axis_sha256', path=str(path))


def _find_mix(release):
    hits = [path for path in INPUTS.rglob('source_model.json') if contract.mix_dir_allowed(path)]
    if any(contract.REFUSE_DIR in path.parts for path in INPUTS.rglob('source_model.json')):
        _fail('blocked_error_producer')
    if len(hits) != 1:
        _fail('blocked_mix_not_ready', found=len(hits))
    model_dir = hits[0].parent
    checkpoint = model_dir / 'checkpoint.json'
    if _sha256(checkpoint) != release['mix']['checkpoint_sha256']:
        _fail('blocked_producer_checkpoint_identity')
    for item in json.loads(checkpoint.read_text())['files']:
        rel = Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts:
            _fail('blocked_producer_relative_path')
        path = model_dir / rel
        if not path.is_file() or path.stat().st_size != item['bytes'] or _sha256(path) != item['sha256']:
            _fail('blocked_producer_file_hash', file=item['path'])
    return model_dir


def _by_content(pin, label):
    hits = [path for path in INPUTS.rglob('*')
            if path.is_file() and path.stat().st_size == pin['bytes'] and _sha256(path) == pin['sha256']]
    if not hits:
        _fail('blocked_source_identity', source=label, expected=pin)
    return hits[0]


def _resolve(release, model_dir):
    """Every voted source of the release, by pinned identity. Returns {name: (path, record)}."""
    import numpy as np
    resolved = {}
    for name, entry in sorted(release['voted'].items()):
        pin = {'bytes': entry['bytes'], 'sha256': entry['sha256']}
        if entry['kind'] == 'mix_cache':
            path = model_dir / 'cache' / (name + '.npz')
            if not path.is_file() or path.stat().st_size != pin['bytes'] or _sha256(path) != pin['sha256']:
                _fail('blocked_source_identity', source=name, expected=pin)
        else:
            path = _by_content(pin, name)
            if entry.get('receipt_sha256') and entry['kind'] == 'successor':
                receipts = [p for p in INPUTS.rglob('cache_receipt.json') if _sha256(p) == entry['receipt_sha256']]
                if len(receipts) != 1:
                    _fail('blocked_source_receipt', source=name, found=len(receipts))
        with np.load(path, allow_pickle=False) as handle:
            meta = json.loads(str(handle['meta']))
            shrunk, raw, se = handle['shrunk'], handle['raw'], handle['se']
            try:
                contract.require_table_arrays(name, tuple(handle.files), shrunk, raw, se, meta)
            except ValueError as exc:
                _fail('blocked_source_table', source=name, reason=str(exc))
            if shrunk.shape[1] != contract.AXIS_GENES:
                _fail('blocked_source_axis', source=name, width=int(shrunk.shape[1]))
            targets = [str(t) for t in handle['targets']]
            if name == 'cd4_mix':
                for part in meta['from']:
                    part_pin = release['mix']['cd4_parts'][part]
                    part_path = model_dir / 'cache' / (part + '.npz')
                    if not part_path.is_file() or _sha256(part_path) != part_pin['sha256']:
                        _fail('blocked_cd4_part', source=part)
        resolved[name] = (path, {'kind': entry['kind'], 'path': str(path), 'bytes': pin['bytes'],
                                 'sha256': pin['sha256'], 'targets': targets,
                                 'in_reference': bool(entry['in_reference'])})
    return resolved


def _reference_recipe(document, sources):
    """The fit driver's recipe of the reference, byte for byte: its sha256 is the recorded t36 recipe."""
    recipe = contract.accept_source_model(document)
    for context in recipe['contexts'].values():
        for source in sources:
            context['weights'][source] = contract.WEIGHT
        if sorted(context['weights']) != sorted(sources):
            _fail('blocked_recipe_sources', expected=sorted(sources), got=sorted(context['weights']))
    return recipe


# --- the bench ---------------------------------------------------------------------------------------------

def _recipe(document, sources, ctx, name, variant):
    base = contract.accept_source_model(document)          # the t36 constants, checked against the mix receipt
    one = next(iter(base['contexts'].values()))
    recipe = {k: v for k, v in base.items() if k != 'contexts'}
    recipe['contexts'] = {ctx: {'amplitude': one['amplitude'],
                                'weights': {s: contract.WEIGHT for s in sorted(sources)}}}
    recipe['name'] = name
    recipe['why'] = 'independent validation, contract v1: fold view of the unchanged t25 transfer'
    for key, value in VARIANTS[variant].items():
        if value is None:
            recipe.pop(key)
        else:
            recipe[key] = value
    return recipe


def _run_stage100(job):
    """One (arm, variant, context) on a cache holding only the allowed sources. Returns the job with its
    manifest; raises on any stage-100 failure."""
    label, ctx, sources, recipe, resolved = job['label'], job['ctx'], job['sources'], job['recipe'], job['resolved']
    root = TEMP / 'runs' / (label + '__' + ctx)
    cache = root / 'cache'
    cache.mkdir(parents=True)
    for source in sources:
        os.symlink(resolved[source][0], cache / (source + '.npz'))
    recipe_path = root / 'recipe.json'
    recipe_path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
    data = WORKING / 'data'
    env = dict(os.environ, VCC2026_DATA_ROOT=str(data), VCC2026_ARTIFACT_ROOT=str(TEMP / 'artifacts'),
               PYTHONPATH=os.pathsep.join([str(WORKING / 'repo' / 'src'), str(WORKING / 'vendor'), str(WORKING)]),
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    cmd = [sys.executable, str(WORKING / 'repo' / 'scripts' / '100_build_context_effects.py'),
           '--recipe', str(recipe_path), '--cache', str(cache),
           '--targets-csv', str(data / 'raw' / 'controls' / 'pert_counts.csv'),
           '--coords', str(data / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv'),
           '--contexts', ctx, '--out', str(root / 'out')]
    started = time.monotonic()
    run = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError('stage 100 failed for %s %s: %s' % (label, ctx, (run.stdout + run.stderr)[-1500:]))
    manifest = json.loads((root / 'out' / 'manifest.json').read_text(encoding='utf-8'))
    job.update(manifest=manifest, effects=root / 'out' / ('effects_%s.npz' % ctx),
               recipe_sha256=_sha256(recipe_path), seconds=time.monotonic() - started)
    return job


def _check_consumption(job, fold):
    """What stage 100 hashed must be exactly the allowed sources, with the pinned bytes, and nothing of the
    held lineage. Returns the receipt of the run."""
    read = job['manifest']['cache_npz_sha256']
    allowed = {s + '.npz': job['resolved'][s][1]['sha256'] for s in job['sources']}
    receipt = {'label': job['label'], 'context': job['ctx'], 'sources_linked': sorted(job['sources']),
               'files_read_by_stage100': read, 'recipe_sha256': job['recipe_sha256'],
               'effects_sha256': job['manifest']['contexts'][job['ctx']]['sha256'],
               'targets_covered': job['manifest']['contexts'][job['ctx']]['targets_covered'],
               'targets_missing': job['manifest']['contexts'][job['ctx']]['targets_missing'],
               'seconds': round(job['seconds'], 1)}
    if read != allowed:
        _fail('blocked_consumption_mismatch', label=job['label'], context=job['ctx'],
              not_read=sorted(set(allowed) - set(read)), unexpected=sorted(set(read) - set(allowed)))
    if fold is not None:
        held = set(fold['exclude_tables'])
        leaked = sorted(s for s in job['sources'] if s in held)
        named = sorted(s for s in job['sources'] for p in fold['exclude_name_patterns'] if p.lower() in s.lower())
        receipt.update(held_lineage=fold['lineage'], excluded_tables=sorted(held), held_tables_read=leaked,
                       sources_matching_held_patterns=named)
        if leaked or named:
            _fail('blocked_held_lineage_read', label=job['label'], context=job['ctx'], leaked=leaked, named=named)
    return receipt


def _load_table(path):
    import numpy as np
    with np.load(path, allow_pickle=False) as z:
        return {'targets': [str(t) for t in z['targets']], 'shrunk': z['shrunk'], 'raw': z['raw'], 'se': z['se'],
                'n_cells': z['n_cells']}


def _load_effects(path, panel, axis):
    import numpy as np
    with np.load(path, allow_pickle=False) as z:
        if [str(t) for t in z['targets']] != panel or [str(g) for g in z['genes']] != axis:
            _fail('blocked_effect_axes', path=str(path))
        return z['lfc'].astype(np.float32), z['observed'].astype(bool)


def main():
    os.chdir(WORKING)
    sys.path.insert(0, str(WORKING))
    params = json.loads((WORKING / 'params.json').read_text(encoding='utf-8'))
    release_path = WORKING / 'release.json'
    if _sha256(release_path) != params['release_sha256']:
        _fail('blocked_release_identity')
    if _sha256(WORKING / 'manifest_fold.json') != params['manifest_sha256']:
        _fail('blocked_manifest_identity')
    release = json.loads(release_path.read_text(encoding='utf-8'))
    manifest = json.loads((WORKING / 'manifest_fold.json').read_text(encoding='utf-8'))
    _verify_embedded(params)
    _check_axis()
    coords = [p for p in INPUTS.rglob('gene_coordinates_gencode_v50.tsv') if _sha256(p) == params['coords']['sha256']]
    if not coords:
        _fail('blocked_coordinates_identity')
    (WORKING / 'data/external/annotation').mkdir(parents=True, exist_ok=True)
    (WORKING / 'data/external/annotation/gene_coordinates_gencode_v50.tsv').write_bytes(coords[0].read_bytes())
    sys.path.insert(0, str(WORKING / 'repo' / 'src'))
    sys.path.insert(0, str(WORKING / 'vendor'))
    os.environ['VCC2026_DATA_ROOT'] = str(WORKING / 'data')
    os.environ['VCC2026_ARTIFACT_ROOT'] = str(TEMP / 'artifacts')
    TEMP.mkdir(parents=True, exist_ok=True)
    from vcc2026.resources import snapshot
    resources = snapshot(WORKING).as_dict()
    if (resources.get('ram_available_bytes') or 0) < contract.RAM_BUDGET_BYTES:
        _fail('blocked_ram', resources=resources)
    import numpy as np
    import bench_core as core
    import metrics as M

    model_dir = _find_mix(release)
    document = json.loads((model_dir / 'source_model.json').read_text(encoding='utf-8'))
    resolved = _resolve(release, model_dir)
    _log('resolved %d sources by content' % len(resolved))
    parts = {}
    for part, pin in release['mix']['cd4_parts'].items():
        path = model_dir / 'cache' / (part + '.npz')
        if _sha256(path) != pin['sha256']:
            _fail('blocked_cd4_part', source=part)
        parts[part] = path
    arms = manifest['arms']
    analysis = params.get('analysis_arms') or {}          # arms of a declared analysis, not of the manifest
    if set(analysis) & set(arms) or any('~' in a or '__' in a for a in analysis):
        _fail('blocked_analysis_arm_names', names=sorted(analysis))
    for arm, spec in {**arms, **analysis}.items():
        missing = sorted(set(spec['sources']) - set(resolved))
        if missing:
            _fail('blocked_arm_sources', arm=arm, missing=missing)
    reference = sorted(s for s in resolved if resolved[s][1]['in_reference'])
    if reference != arms['T0']['sources'] or sorted(resolved) != arms['R1']['sources']:
        _fail('blocked_arm_definition', reference=reference)
    ref_recipe = WORKING / 'recipe_reference_t36.json'
    ref_recipe.write_text(json.dumps(_reference_recipe(document, reference), indent=2) + '\n', encoding='utf-8')
    if _sha256(ref_recipe) != release['reference']['recipe_sha256']:
        _fail('blocked_reference_recipe', got=_sha256(ref_recipe))

    panel = [line.split(',')[0] for line in (WORKING / 'data/raw/controls/pert_counts.csv').read_text().splitlines()[1:]]
    axis = [line.split(',')[0] for line in (WORKING / 'data/raw/controls/gene_names.csv').read_text().splitlines()[1:]]
    if len(panel) != contract.PANEL_N or len(axis) != contract.AXIS_GENES:
        _fail('blocked_axes', panel=len(panel), axis=len(axis))
    folds = {f['id']: f for f in manifest['folds_C']}

    jobs = []
    for arm, spec in {**arms, **analysis}.items():
        variants = ['', 'gamma0', 'nocis'] if arm == 'T0' else ['']
        for variant in variants:
            label = arm if not variant else arm + '~' + variant
            for ctx in ['PROD', *folds]:
                if ctx == 'PROD':
                    sources = spec['sources']
                else:
                    sources = sorted(set(spec['sources']) - set(folds[ctx]['exclude_tables']))
                    if arm in arms and sources != sorted(folds[ctx]['arm_sources'][arm]):
                        _fail('blocked_fold_sources', arm=arm, context=ctx)
                if not sources:
                    continue
                jobs.append({'label': label, 'arm': arm, 'variant': variant, 'ctx': ctx, 'sources': list(sources),
                             'recipe': _recipe(document, sources, ctx, 'validazione-%s-%s' % (label, ctx), variant),
                             'resolved': resolved})
    _log('running %d stage-100 jobs' % len(jobs))
    with ThreadPoolExecutor(4) as pool:
        done = list(pool.map(_run_stage100, jobs))
    _log('stage 100 finished')
    consumption = [_check_consumption(job, folds.get(job['ctx'])) for job in done]
    by = {(job['label'], job['ctx']): job for job in done}

    # PARITY before any comparison: production effects must reproduce the recorded sha256
    recorded = params['recorded_production_effects_sha256']
    parity = {arm: {'recorded': recorded[arm], 'got': by[(arm, 'PROD')]['manifest']['contexts']['PROD']['sha256']}
              for arm in recorded}
    for arm, p in parity.items():
        p['equal'] = p['recorded'] == p['got']
    _write(WORKING / 'parity.json', {'reference_recipe_sha256': _sha256(ref_recipe), 'effects': parity})
    _write(WORKING / 'consumption.json', consumption)
    if not all(p['equal'] for p in parity.values()):
        _fail('blocked_parity', parity=parity)
    _log('parity passed for %s' % sorted(parity))

    out_effects = WORKING / 'effects'
    out_effects.mkdir()
    effects = {}
    for (label, ctx), job in by.items():
        effects[(label, ctx)] = _load_effects(job['effects'], panel, axis)
        if ctx != 'PROD' and '~' not in label:
            shutil.copy2(job['effects'], out_effects / ('%s__%s.npz' % (label, ctx)))
    manifests = WORKING / 'stage100_manifests'
    manifests.mkdir()
    for (label, ctx), job in by.items():
        _write(manifests / ('%s__%s.json' % (label, ctx)), job['manifest'])

    tables = {name: _load_table(path) for name, (path, _) in resolved.items()}
    tables.update({name: _load_table(path) for name, path in parts.items()})
    # external arms: effects another assignment delivered per fold, found by pinned size and sha256
    external = params.get('external_arms') or {}
    external_read = {}
    for label, by_fold in external.items():
        if label in arms or label in analysis or '~' in label:
            _fail('blocked_external_arm_name', label=label)
        for fid, pin in by_fold.items():
            if fid not in folds:
                _fail('blocked_external_fold', label=label, fold=fid)
            path = _by_content(pin, '%s/%s' % (label, fid))
            effects[(label, fid)] = _load_effects(path, panel, axis)
            external_read['%s/%s' % (label, fid)] = {'path': str(path), **pin}
    _write(WORKING / 'external_arms.json', external_read)
    results, macro, shuffle, rows_csv = core.measure(
        folds, list(arms), effects, tables.__getitem__, panel, axis, _log,
        extra_arms=[*analysis, *external], extra_contrasts=params.get('contrasts') or [])

    with (WORKING / 'per_target.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(core.CSV_HEADER)
        writer.writerows(rows_csv)
    exclude = np.isin(np.asarray(axis), np.asarray(panel))
    _write(WORKING / 'table_audit.json', {
        'pairs': core.table_audit(tables, exclude),
        'votes': core.vote_audit(manifest, {s: r[1]['targets'] for s, r in resolved.items()}, panel)})
    _write(WORKING / 'results.json', {
        'state': 'level_A_complete', 'not_vcc_scores': True, 'development_lineages_not_confirmation': True,
        'contract': 'PROTOCOLLO_v1', 'manifest_sha256': params['manifest_sha256'],
        'release_sha256': params['release_sha256'], 'parity': parity, 'folds': results, 'macro': macro,
        'shuffle_control': shuffle, 'bootstrap': {'resamples': M.BOOT, 'seed': M.BOOT_SEED, 'unit': 'target'},
        'resources': resources, 'seconds': time.monotonic() - T0})
    _write(WORKING / 'status.json', {'status': 'level_A_complete', 'usable': True, 'jobs': len(done),
                                     'parity': {a: p['equal'] for a, p in parity.items()}})
    shutil.rmtree(TEMP / 'runs', ignore_errors=True)
    _log('done')


if __name__ == '__main__':
    main()
