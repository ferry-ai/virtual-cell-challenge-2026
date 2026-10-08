"""Record current provider states and rehash delivered local artifacts only.

No cloud launch, output download, ingestion or response fitting.
"""
import argparse
import json
from pathlib import Path
from cloud_campaign import call
from percorso import HERE, ROOT, now, pin, read, sha, write_new


def main(out):
    status = {}
    for slug in ('dt-final-t2-01a11c34-r1', 'esm2-production-01a11c35-r4', 'esm2-t-01a11c35-r3'):
        rc, answer = call('davideferrante11', ['kernels', 'status', 'davideferrante11/' + slug])
        status[slug] = dict(utc=now(), returncode=rc, provider_status=answer.strip())
    candidate_path = HERE/'candidate_t2_r1.json'
    candidate = read(candidate_path)
    checked = {}
    for context, item in candidate['effects'].items():
        path = Path(item['path'])
        ok = path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
        if not ok: raise ValueError('T2 effect identity differs: ' + context)
        checked[context] = dict(**item, actual_bytes_rehashed=True)
    for key in ('receipt', 'cloud_verification', 'parent_release', 'common_release', 'fold_common_release'):
        item = candidate[key]
        if sha(item['path']) != item['sha256']: raise ValueError('T2 evidence changed: ' + key)
    views = {}
    for name in ('production', 'T', 'C-K562', 'C-iPSC', 'J-K562', 'J-iPSC'):
        path = HERE/f'training_release_{name}_r1.json'
        release = read(path)
        for key in ('view', 'inputs', 'split'):
            item = release[key]
            if Path(item['path']).stat().st_size != item['bytes'] or sha(item['path']) != item['sha256']:
                raise ValueError('training contract changed: ' + name + '/' + key)
        views[name] = dict(release=pin(path), view=release['view'], frozen_objects_unchanged=True)
    external = ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08'
    prepared = {name:pin(external/name) for name in ('prepared_production_r4.json', 'prepared_T_r3.json')}
    result = dict(utc=now(), scope='provider state, local delivered artifact hashes and frozen view identity',
        provider=status, T2=dict(candidate=pin(candidate_path), effects=checked, prior_verification_unchanged=True,
            consent_pending=False, cell_generation=False, scientific_promotion=False),
        views=views, external_prepared=prepared, model_fit_receipts_checked=False,
        response_chunks_read=False, jobs_launched=0, files_downloaded=0, complete_D053=False)
    write_new(out, result)
    print(json.dumps(dict(provider=status, T2_effects_rehashed=len(checked), frozen_views_unchanged=len(views),
                          model_fit_receipts_checked=False)))


if __name__ == '__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('out', type=Path);a=p.parse_args();main(a.out)
