"""Pin the missing cross-account access from destination-side metadata checks."""
from collections import defaultdict
import json
from pathlib import Path
from percorso import HERE, ROOT, now, pin, read, sha, write_new


def build():
    external = ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08'
    folds = {}
    for fold, owner in [('C-iPSC', 'davidmaisterx'), ('J-iPSC', 'davideferante')]:
        release_path = HERE/f'training_release_{fold}_r1.json'
        release = read(release_path)
        view_path = Path(release['view']['path'])
        if sha(view_path) != release['view']['sha256']:
            raise ValueError('frozen view changed')
        view = read(view_path)
        prepared_path = external/f'prepared_{fold}_r2.json'
        prepared = read(prepared_path)
        access_path = HERE/f'source_access_{fold}_r1.json'
        access = read(access_path)
        if access['destination'] != owner or access['prepared_sha256'] != sha(prepared_path):
            raise ValueError('destination access evidence differs')
        if prepared['view_sha256'] != sha(view_path):
            raise ValueError('prepared view changed')
        rejected = {x['source'] for x in access['sources'] if not x['native_admissible']}
        if any(not p.startswith('davideferrante11/') for p in rejected):
            raise ValueError('unexpected source owner')
        grouped = defaultdict(dict)
        for c in view['chunks']:
            if c['producer'] in rejected:
                value = {k:c[k] for k in ('sha256', 'bytes')}
                old = grouped[c['producer']].setdefault(c['producer_file'], value)
                if old != value:
                    raise ValueError('conflicting file identity')
        if set(grouped) != rejected:
            raise ValueError('access rejection does not belong to view')
        sources = {p:dict(chunks=len(files), bytes=sum(x['bytes'] for x in files.values()))
                   for p, files in sorted(grouped.items())}
        folds[fold] = dict(destination=owner, destination_visibility='private jobs only',
            release=pin(release_path), view=release['view'], prepared=pin(prepared_path),
            access_evidence=pin(access_path), sources=sources,
            additional_chunks=sum(x['chunks'] for x in sources.values()),
            additional_bytes=sum(x['bytes'] for x in sources.values()),
            already_authorized_private_bytes=prepared['private_bytes'])
    result = dict(utc=now(), status='PREPARED_NOT_TRANSFERRED', folds=folds,
        method='Owner-authenticated output listing; temporary file locators in new private packages outside Git and logs; only pinned NPZ chunks downloaded within destination Kaggle runtimes.',
        authorization='The exact existing 53.5 MB / 43.8 MB consent excludes these additional df11-owned files. Record specific extension before issuing locators.',
        publication_alternative='User authorized publishing campaign derivatives; installed Kaggle SDK exposes SaveKernel, not a dedicated visibility-only update. No speculative save/version/re-execution is used.',
        no_local_rna_download=True, no_acl_changes=True, no_source_publication=True,
        no_esm2_publication=True, no_new_compute=True,
        science_unchanged=['view bytes', 'split', 'chunk hashes', 'axes', 'weights', 'query support'],
        execution_owner='DATI-TRANSFER prepares access after authorization; MODELLI-ESTERNI owns fit packaging and dispatch')
    out = HERE/'cross_account_access_plan_r1.json'
    write_new(out, result)
    print(json.dumps({f:{k:x[k] for k in ('destination','additional_chunks','additional_bytes','already_authorized_private_bytes')}
                      for f,x in folds.items()}))


if __name__ == '__main__':
    build()
