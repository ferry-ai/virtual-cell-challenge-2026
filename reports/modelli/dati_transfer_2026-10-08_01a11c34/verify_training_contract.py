"""Independently audit frozen training metadata; never claim response-array checks."""
import argparse
from collections import Counter, defaultdict
import hashlib
import math
from pathlib import Path
from percorso import now, pin, read, sha, write_new


def verify(release_path, out):
    release = read(release_path)
    for key in ('view', 'inputs', 'split'):
        record = release[key]
        path = Path(record['path'])
        if path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
            raise ValueError('changed release object: ' + key)
    view = read(release['view']['path'])
    genes = view['genes']
    if len(genes) != len(set(genes)) or len(genes) != view['response_shape'][1]:
        raise ValueError('invalid gene axis')
    if view['release_sha256'] != release['inputs']['sha256'] or view['split_manifest_sha256'] != release['split']['sha256']:
        raise ValueError('changed embedded release identity')
    if view['regime'] != release['regime'] or view['modality'] != 'CRISPRi':
        raise ValueError('unexpected regime or mechanism')
    contexts = {}; counts = Counter(); mass = defaultdict(list); pairs = set(); targets = set()
    hidden = set(view['effective_split']['hidden_targets'])
    for chunk in view['chunks']:
        identity = chunk['identity']; context = chunk['context_id']; study = identity['study']
        if identity['modality'] != 'CRISPRi' or context.startswith('h1_test:'):
            raise ValueError('protected or wrong-mechanism context')
        if context in contexts and contexts[context] != study:
            raise ValueError('context experiment changed')
        contexts[context] = study
        if len(chunk['targets']) != len(chunk['weights']):
            raise ValueError('weight axis mismatch')
        for target, weight in zip(chunk['targets'], chunk['weights']):
            if (context, target) in pairs:
                raise ValueError('duplicate target within biological context')
            pairs.add((context, target)); targets.add(target); counts[context] += 1
            if not math.isfinite(weight) or weight <= 0:
                raise ValueError('invalid training weight')
            mass[context].append(weight)
            if view['regime'] == 'T' and (target in hidden or int(hashlib.sha256(target.encode('utf-8')).hexdigest(), 16) % 5 == 0):
                raise ValueError('hidden target leaked into training contract: ' + target)
    if dict(counts) != view['expected_rows_by_context'] or len(pairs) != view['response_shape'][0]:
        raise ValueError('row coverage differs from declared coverage')
    contexts_per_study = Counter(contexts.values())
    study_mass = Counter()
    for context, study in contexts.items():
        observed = math.fsum(mass[context])
        expected = 1 / len(contexts_per_study) / contexts_per_study[study]
        if not math.isclose(observed, expected, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError('context mass differs from declared weight policy')
        study_mass[study] += observed
    write_new(out, dict(utc=now(), release=pin(release_path), regime=view['regime'],
        response_shape=view['response_shape'], contexts=len(contexts), experiments=len(study_mass),
        unique_targets=len(targets), chunks=len(view['chunks']), total_row_mass=math.fsum(study_mass.values()),
        hidden_targets_absent=view['regime'] == 'T', duplicate_context_targets=0,
        scope='actual local metadata hashes, axes, row identities, target exclusions and training weights',
        response_arrays_read=False, model_fit=False, claims_complete_corpus=False))
    print(view['regime'], len(pairs), len(contexts), len(targets), 'metadata verified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('release', type=Path); parser.add_argument('out', type=Path)
    args = parser.parse_args(); verify(args.release, args.out)
