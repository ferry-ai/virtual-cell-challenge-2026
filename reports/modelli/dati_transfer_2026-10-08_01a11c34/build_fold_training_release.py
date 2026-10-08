"""Freeze C/J metadata and subset existing private runtime access; never read RNA.

C starts from production effects, J from effects derived with T exclusions.
All effects are context-local with fixed shrinkage parameters. Dropping an entire
lineage precedes every cross-context fit, imputation and weight calculation.
"""
import argparse
from collections import Counter
import copy
import hashlib
import math
from pathlib import Path
from percorso import DATA, HERE, ROOT, now, pin, read, sha, write_new
from fold_bank import validate_split

VALID = ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08'


def transform(parent, split):
    validate_split(split)
    regime = split['regime']
    if regime not in {'C', 'J'} or parent['regime'] != ('production' if regime == 'C' else 'T'):
        raise ValueError('C requires production, J requires upstream target-excluded effects')
    aliases = split['group_aliases']
    canonical = lambda g: aliases.get(g, g)
    held = {canonical(g) for g in split['held_groups']}
    chunks = []
    removed = {}
    for original in parent['chunks']:
        group = canonical(original['context_group'])
        if group in held:
            removed.setdefault(original['context_id'], dict(identity=original['identity'],
                rows=0, reason='held_lineage_before_any_cross_context_learning'))['rows'] += len(original['targets'])
        else:
            if original.get('protected') or original['context_id'].startswith('h1_test:'):
                raise ValueError('protected context')
            chunks.append(copy.deepcopy(original))
    if not removed or not chunks:
        raise ValueError('empty held or retained context set')
    contexts = {}; counts = Counter(); targets = set()
    hidden = set(split['hidden_targets']) | set(parent['excluded_targets'])
    for chunk in chunks:
        cid = chunk['context_id']; study = chunk['identity']['study']
        if contexts.setdefault(cid, study) != study:
            raise ValueError('context spans experiments')
        counts[cid] += len(chunk['targets']); targets.update(chunk['targets'])
        if regime == 'J' and any(t in hidden or int(hashlib.sha256(t.encode()).hexdigest(), 16) % 5 == 0
                                 for t in chunk['targets']):
            raise ValueError('upstream hidden response reached J')
    per_study = Counter(contexts.values())
    for chunk in chunks:
        cid = chunk['context_id']
        weight = 1.0 / (len(per_study) * per_study[contexts[cid]] * counts[cid])
        chunk['weights'] = [weight] * len(chunk['targets'])
    total = math.fsum(w for c in chunks for w in c['weights'])
    if not math.isclose(total, 1.0, rel_tol=1e-12):
        raise ValueError('fold weights do not sum to one')
    view = copy.deepcopy(parent)
    view.update(utc=now(), regime=regime, chunks=chunks, expected_rows_by_context=dict(counts),
        effective_split=split, excluded_targets=sorted(hidden),
        excluded_contexts=sorted(held | {g for g in aliases if canonical(g) in held}),
        response_shape=[sum(counts.values()), len(parent['genes'])],
        mmap_bytes=sum(counts.values()) * len(parent['genes']) * 5,
        excluded=parent['excluded'] + [dict(context_id=k, **v) for k,v in sorted(removed.items())])
    producers = {c['producer'] for c in chunks}
    view['provenance'] = [p for p in parent['provenance'] if p['producer'] in producers]
    audit = dict(retained_contexts=len(counts), removed_contexts=removed,
        retained_rows=sum(counts.values()), removed_rows=sum(x['rows'] for x in removed.values()),
        experiments=len(per_study), unique_targets=len(targets), chunks=len(chunks), total_row_mass=total,
        response_arrays_read=False, recomputed_effects=False, changes_to_retained_chunks=['weights'],
        target_exclusions_before_derivation=(regime == 'J'), model_fit=False, complete_D053=False)
    return view, audit


def frozen_split(regime, lineage):
    v1, v2 = read(VALID/'manifest_fold_v1.json'), read(VALID/'manifest_fold_v2.json')
    if v2['supersedes']['sha256'] != sha(VALID/'manifest_fold_v1.json'):
        raise ValueError('v2 parent manifest differs')
    before = next(f for f in v1['folds_C'] if f['lineage'] == lineage)
    after = next(f for f in v2['folds_C'] if f['lineage'] == lineage)
    for key in ('id', 'lineage', 'exclude_tables', 'exclude_units', 'arm_sources', 'truth'):
        if before[key] != after[key]: raise ValueError('registered fold moved: ' + key)
    split = read(VALID/'splits_v1'/f'{regime}-{lineage}.json')
    if split['exclude_units'] != sorted(after['exclude_units']):
        raise ValueError('split unit exclusions differ')
    split.update(manifest_sha256=sha(VALID/'manifest_fold_v2.json'), manifest_version='v2')
    return split


def runtime_subset(parent_regime, revision, release_path, view):
    parent_dir = DATA/'processed/dati_transfer_2026-10-08_01a11c34/runtime_access'/f'{parent_regime}_df11_r1'
    parent_inputs = read(parent_dir/'runtime_inputs.json')
    locator_pin = parent_inputs['private_locators']
    if sha(locator_pin['path']) != locator_pin['sha256']:
        raise ValueError('parent private locator identity differs')
    parent_locators = read(locator_pin['path'])['files']
    grouped = {}
    for c in view['chunks']:
        grouped.setdefault(c['producer'], {})[c['producer_file']] = c
    sources = {}; mounts = []; locators = {}
    for producer, chunks in sorted(grouped.items()):
        source = copy.deepcopy(parent_inputs['sources'][producer])
        source.update(chunks=len(chunks), bytes=sum(c['bytes'] for c in chunks.values()))
        sources[producer] = source
        if source['route'] == 'native_mount':
            mounts.append(producer)
        else:
            for filename, chunk in chunks.items():
                key = producer + '/' + filename
                entry = parent_locators[key]
                if any(entry[k] != chunk[k] for k in ('bytes', 'sha256')):
                    raise ValueError('private chunk identity differs')
                locators[key] = entry
    stage = parent_dir.parent/revision
    stage.mkdir(parents=True, exist_ok=False)
    release = read(release_path)
    write_new(stage/'private_locators.json', dict(utc=now(), runtime_owner='davideferrante11',
        release=pin(release_path), view=release['view'], files=locators, private=True, never_log_or_commit=True))
    write_new(stage/'runtime_inputs.json', dict(utc=now(), release=pin(release_path), view=release['view'],
        kernel_sources=mounts, private_locators=pin(stage/'private_locators.json'), sources=sources))
    public = dict(runtime_inputs=pin(stage/'runtime_inputs.json'), native_mounts=len(mounts),
        private_chunks=len(locators), private_bytes=sum(x['bytes'] for x in locators.values()),
        subset_of_existing_authorized_access=True, new_locators_issued=False, downloaded_bytes=0,
        runtime_owner='davideferrante11', private_only=True, source_visibility_changed=False)
    return public


def main(regime, lineage, revision):
    parent_regime = 'production' if regime == 'C' else 'T'
    parent_release_path = HERE/f'training_release_{parent_regime}_r1.json'
    parent_release = read(parent_release_path)
    for key in ('view', 'inputs', 'split'):
        item = parent_release[key]
        if sha(item['path']) != item['sha256']:
            raise ValueError('parent release identity differs')
    parent = read(parent_release['view']['path'])
    split = frozen_split(regime, lineage)
    view, audit = transform(parent, split)
    name = f'{regime}-{lineage}_{revision}'
    out = DATA/'processed/dati_transfer_2026-10-08_01a11c34/training_views'/name
    out.mkdir(parents=True, exist_ok=False)
    write_new(out/'view_split.json', split)
    write_new(out/'view_inputs.json', dict(schema='fold-training-input-release/1', utc=now(),
        parent_release=pin(parent_release_path), parent_inputs=parent_release['inputs'],
        provenance=view['provenance'], selection=audit,
        transformations='Remove entire held lineage; retain context-local derived arrays; recalculate training row weights'))
    view.update(parent_view=parent_release['view'], split_manifest=pin(out/'view_split.json'),
        split_manifest_sha256=sha(out/'view_split.json'), release=pin(out/'view_inputs.json'),
        release_sha256=sha(out/'view_inputs.json'),
        validation_review=dict(status='pending independent comparative validation', manifest=pin(VALID/'manifest_fold_v2.json')))
    write_new(out/'view.json', view)
    release_path = HERE/f'training_release_{name}.json'
    write_new(release_path, dict(utc=now(), regime=regime, lineage=lineage, view=pin(out/'view.json'),
        inputs=pin(out/'view_inputs.json'), split=pin(out/'view_split.json'), parent_release=pin(parent_release_path),
        response_shape=view['response_shape'], contexts=len(view['expected_rows_by_context']), chunks=len(view['chunks']),
        selection=audit, code=pin(Path(__file__)), arrays_independently_rehashed=False,
        model_fit=False, claims_complete_corpus=False))
    access = runtime_subset(parent_regime, f'{regime}-{lineage}_df11_{revision}', release_path, view)
    write_new(HERE/f'fold_runtime_access_{name}.json', dict(utc=now(), release=pin(release_path), **access))
    print({k:v for k,v in dict(fold=name, **audit, **access).items() if k not in {'removed_contexts', 'runtime_inputs'}})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('regime', choices=['C', 'J']); p.add_argument('lineage', choices=['K562', 'iPSC'])
    p.add_argument('revision'); a = p.parse_args(); main(a.regime, a.lineage, a.revision)
