"""Fit of the unchanged t25 transfer (stage 100) on a frozen source release. Effects only.

The model is the one of t36: equal weight 1 per voted source, shrunk effects, gamma 1,
amplitude 1.576, original cis head. Only the bank changes. The run:

1. verifies every embedded file, the axis, the panel and the mounted mix checkpoint;
2. resolves every voted source of ``release.json`` by its pinned bytes and sha256 - a source
   that is missing or different stops the run, there is no fallback to another table;
3. rebuilds the t36 recipe from the same mounts and requires its recorded sha256, then runs
   stage 100 on it (reference) and on the release recipe;
4. writes ``consumo.json``: sources expected, verified and actually read by stage 100, votes
   per panel target, and where the release effects differ from the reference.

No generation, no packaging, no submission. Not a held-out validation.
"""
from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import sys
from pathlib import Path

import generate_contract as contract

WORKING = Path('/kaggle/working')
INPUTS = Path('/kaggle/input')
TEMP = Path('/kaggle/temp')


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _fail(status, **fields):
    _write(WORKING / 'status.json', {'status': status, 'usable_export': False, 'loss': None,
                                     'optimizer': None, **fields})
    raise SystemExit(2)


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
    """Exactly one content: every mounted file with the pinned size and sha256 is that table."""
    hits = [path for path in INPUTS.rglob('*')
            if path.is_file() and path.stat().st_size == pin['bytes'] and _sha256(path) == pin['sha256']]
    if not hits:
        _fail('blocked_source_identity', source=label, expected=pin)
    return hits[0]


def _resolve(release, model_dir):
    """Every voted source, by pinned identity. Returns {name: (path, record)}."""
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
            if 'genes' in handle.files:
                axis = [line.split(',')[0] for line in (WORKING / 'data/raw/controls/gene_names.csv')
                        .read_text().splitlines()[1:]]
                if [str(g) for g in handle['genes']] != axis:
                    _fail('blocked_source_gene_order', source=name)
            targets = [str(t) for t in handle['targets']]
            measured = {t: int(np.isfinite(shrunk[i]).sum()) for i, t in enumerate(targets)}
            if name == 'cd4_mix':
                for part in meta['from']:
                    part_pin = release['mix']['cd4_parts'][part]
                    part_path = model_dir / 'cache' / (part + '.npz')
                    if not part_path.is_file() or _sha256(part_path) != part_pin['sha256']:
                        _fail('blocked_cd4_part', source=part)
        resolved[name] = (path, {'kind': entry['kind'], 'path': str(path), 'bytes': pin['bytes'],
                                 'sha256': pin['sha256'], 'targets': targets, 'genes_measured': measured,
                                 'in_reference': bool(entry['in_reference'])})
    return resolved


def _cache_dir(name, resolved, sources):
    dest = WORKING / name
    dest.mkdir()
    for source in sources:
        os.symlink(resolved[source][0], dest / (source + '.npz'))
    return dest


def _recipe(document, sources, name, why=None):
    recipe = contract.accept_source_model(document)
    for context in recipe['contexts'].values():
        for source in sources:
            context['weights'][source] = contract.WEIGHT
        if sorted(context['weights']) != sorted(sources):
            _fail('blocked_recipe_sources', expected=sorted(sources), got=sorted(context['weights']))
    if name:
        recipe['name'] = name
        recipe['why'] = why
    return recipe


def _run_stage100(recipe_path, cache, out):
    script = WORKING / 'repo' / 'scripts' / '100_build_context_effects.py'
    data = WORKING / 'data'
    old = sys.argv[:]
    sys.argv = [str(script), '--recipe', str(recipe_path), '--cache', str(cache),
                '--targets-csv', str(data / 'raw' / 'controls' / 'pert_counts.csv'),
                '--coords', str(data / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv'),
                '--contexts', 'A,B,C', '--out', str(out)]
    try:
        runpy.run_path(str(script), run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    finally:
        sys.argv = old
    return json.loads((out / 'manifest.json').read_text(encoding='utf-8'))


def _read_check(manifest, resolved, sources):
    """Stage 100 hashes every table it opens: a voted source it did not open is a failure."""
    read = manifest['cache_npz_sha256']
    missing = [s for s in sources if read.get(s + '.npz') != resolved[s][1]['sha256']]
    extra = sorted(set(read) - {s + '.npz' for s in sources} - {'cd4_Rest.npz', 'cd4_Stim8hr.npz', 'cd4_Stim48hr.npz'})
    if missing or extra:
        _fail('blocked_consumption_mismatch', not_read=missing, unexpected=extra)
    return read


def main():
    os.chdir(WORKING)
    sys.path.insert(0, str(WORKING))
    params = json.loads((WORKING / 'params.json').read_text(encoding='utf-8'))
    release_path = WORKING / 'release.json'
    if _sha256(release_path) != params['release_sha256']:
        _fail('blocked_release_identity')
    release = json.loads(release_path.read_text(encoding='utf-8'))
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

    model_dir = _find_mix(release)
    document = json.loads((model_dir / 'source_model.json').read_text(encoding='utf-8'))
    resolved = _resolve(release, model_dir)
    voted = sorted(resolved)
    reference = sorted(s for s in voted if resolved[s][1]['in_reference'])

    # Reference: the t36 recipe, rebuilt from these mounts. Its recorded hash must come back.
    ref_recipe = WORKING / 'recipe_reference_t36.json'
    ref_recipe.write_text(json.dumps(_recipe(document, reference, None), indent=2) + '\n', encoding='utf-8')
    if _sha256(ref_recipe) != release['reference']['recipe_sha256']:
        _fail('blocked_reference_recipe', got=_sha256(ref_recipe), expected=release['reference']['recipe_sha256'])
    ref_manifest = _run_stage100(ref_recipe, _cache_dir('cache_reference', resolved, reference), TEMP / 'reference')
    _read_check(ref_manifest, resolved, reference)

    rel_recipe = WORKING / 'recipe_release.json'
    rel_recipe.write_text(json.dumps(_recipe(document, voted, release['name'], release['why']), indent=2) + '\n',
                          encoding='utf-8')
    rel_manifest = _run_stage100(rel_recipe, _cache_dir('cache_release', resolved, voted), TEMP / 'release')
    read = _read_check(rel_manifest, resolved, voted)

    panel = [line.split(',')[0] for line in (WORKING / 'data/raw/controls/pert_counts.csv').read_text().splitlines()[1:]]
    votes = {t: [s for s in voted if resolved[s][1]['genes_measured'].get(t, 0) > 0] for t in panel}
    added = [s for s in voted if not resolved[s][1]['in_reference']]
    touched = sorted(t for t in panel if any(s in added for s in votes[t]))
    contexts, changed_all = {}, set()
    out = WORKING / 'effects'
    out.mkdir()
    for ctx in ('A', 'B', 'C'):
        with np.load(TEMP / 'release' / ('effects_%s.npz' % ctx), allow_pickle=False) as new, \
                np.load(TEMP / 'reference' / ('effects_%s.npz' % ctx), allow_pickle=False) as old:
            if [str(t) for t in new['targets']] != panel or [str(t) for t in old['targets']] != panel:
                _fail('blocked_effect_targets', context=ctx)
            delta = np.abs(new['lfc'].astype(np.float64) - old['lfc'].astype(np.float64))
            changed = [panel[i] for i in np.flatnonzero(delta.max(axis=1) > 0)]
            changed_all.update(changed)
            norms = {panel[i]: float(np.linalg.norm(new['lfc'][i] - old['lfc'][i])) for i in np.flatnonzero(delta.max(axis=1) > 0)}
        shutil.copy2(TEMP / 'release' / ('effects_%s.npz' % ctx), out / ('effects_%s.npz' % ctx))
        contexts[ctx] = {'release_sha256': rel_manifest['contexts'][ctx]['sha256'],
                         'reference_sha256': ref_manifest['contexts'][ctx]['sha256'],
                         'targets_covered': rel_manifest['contexts'][ctx]['targets_covered'],
                         'targets_missing': rel_manifest['contexts'][ctx]['targets_missing'],
                         'reference_targets_covered': ref_manifest['contexts'][ctx]['targets_covered'],
                         'targets_changed_vs_reference': changed, 'delta_l2_by_target': norms}
    shutil.copy2(TEMP / 'release' / 'manifest.json', out / 'manifest.json')
    shutil.copy2(TEMP / 'reference' / 'manifest.json', WORKING / 'reference_manifest.json')
    outside = sorted(changed_all - set(touched))
    consumo = {
        'state': 'fit_complete_effects_only', 'release': release['name'], 'release_sha256': params['release_sha256'],
        'model': 'stage 100, t25 transfer: weight 1 per voted source, shrunk, gamma 1, amplitude 1.576, cis head',
        'loss': None, 'optimizer': None, 'not_heldout_validation': True, 'not_a_score': True,
        'sources_expected': sorted(release['voted']), 'sources_verified': voted,
        'sources_read_by_stage100': sorted(k[:-4] for k in read if k[:-4] in voted),
        'sources': {s: {k: v for k, v in resolved[s][1].items() if k != 'genes_measured'} | {
            'panel_targets_voted': sum(1 for t in panel if s in votes[t])} for s in voted},
        'sources_added_to_reference': added,
        'votes_per_target': {t: votes[t] for t in panel},
        'vote_count_histogram': {str(n): sum(1 for t in panel if len(votes[t]) == n)
                                 for n in sorted({len(v) for v in votes.values()})},
        'targets_with_added_votes': touched,
        'targets_changed_outside_added_votes': outside,
        'reference': {'recipe_sha256': _sha256(ref_recipe), 'equals_recorded_t36_recipe': True,
                      'sources': reference},
        'recipe_sha256': _sha256(rel_recipe), 'contexts': contexts,
        'resources': resources,
        'claims_complete_corpus': False,
        'scope': 'production fit on the admitted vote arm; other arms and blocked sources are in release.json',
    }
    _write(WORKING / 'consumo.json', consumo)
    _write(WORKING / 'status.json', {'status': 'effects_ready', 'usable_export': True, 'loss': None,
                                     'optimizer': None, 'sources': voted, 'recipe_sha256': consumo['recipe_sha256'],
                                     'targets_changed_outside_added_votes': len(outside)})
    for name in ('cache_reference', 'cache_release'):
        shutil.rmtree(WORKING / name)


if __name__ == '__main__':
    main()
