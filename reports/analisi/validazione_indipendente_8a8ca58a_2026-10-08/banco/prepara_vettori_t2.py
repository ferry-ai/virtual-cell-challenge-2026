"""The frozen common vectors of T2 as DATI-TRANSFER delivered them: verify, describe, stage one private dataset.

    prepara_vettori_t2.py verifica <revision>               hashes against the delivery manifest, targets behind each vector
    prepara_vettori_t2.py dataset-create <revision>         upload common.npz and support.npz as one private dataset
    prepara_vettori_t2.py dataset-status <revision> <out.json>

The vectors belong to DATI-TRANSFER (session 01a11c34): they are read here and never changed. The bench needs them
on Kaggle because level A reruns stage 100 there, on a cache without the held lineage; the kernel finds the file
by size and sha256. `MINIMUM_TARGETS` is the early signal of STRADE S-011, written before these vectors were read.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prepara_banco as B  # noqa: E402

DELIVERY = B.REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34/common_release_production_r1.json'
MANIFEST = HERE.parent / 'manifest_fold_v2.json'
DATA = Path('C:/Users/ferra/vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08')
AXIS_FROM = DATA / 'effetti_k562_x1/T0.npz'           # an effect file of this bench: its genes are the official axis
MINIMUM_TARGETS = 20                                   # S-011: below twenty targets a mean removes over 5 % of an effect


def folder(revision):
    return HERE / ('t2_vettori_%s' % revision)


def verifica(revision):
    import numpy as np
    delivery = B.read(DELIVERY)
    here = folder(revision)
    here.mkdir(exist_ok=False)
    files = {}
    for key in ('common', 'support'):
        path = Path(delivery[key]['path'])
        got = B.pin(path)
        files[key] = dict(path=path.as_posix(), declared={k: delivery[key][k] for k in ('bytes', 'sha256')}, read=got,
                          equal=got == {k: delivery[key][k] for k in ('bytes', 'sha256')})
    sources = sorted(B.read(MANIFEST)['arms']['T1']['sources'])
    with np.load(AXIS_FROM, allow_pickle=False) as z:
        axis = [str(g) for g in z['genes']]
    described, problems = {}, []
    with np.load(files['common']['path'], allow_pickle=False) as c, np.load(files['support']['path'],
                                                                         allow_pickle=False) as s:
        for label, z in (('common', c), ('support', s)):
            if [str(g) for g in z['genes']] != axis:
                problems.append('%s: genes are not the official axis' % label)
            if sorted(set(z.files) - {'genes'}) != sources:
                problems.append('%s: sources differ from the T1 arm of the manifest' % label)
        for name in sources:
            value, behind = np.asarray(c[name], dtype=np.float64), np.asarray(s[name])
            supported = behind > 0
            if not np.isfinite(value).all() or (value[~supported] != 0).any():
                problems.append('%s: a value is not finite, or not zero where no target supports it' % name)
            described[name] = dict(
                targets_behind_max=int(behind.max()), targets_behind_median_on_supported=float(np.median(behind[supported])),
                targets_behind_min_on_supported=int(behind[supported].min()), genes_supported=int(supported.sum()),
                genes_without_support=int((~supported).sum()), norm=float(np.linalg.norm(value)),
                own_effect_removed_at_most=1.0 / int(behind.max()))
    below = sorted(n for n, d in described.items() if d['targets_behind_max'] < MINIMUM_TARGETS)
    B.write_new(here / 'verifica.json', dict(
        utc=B.now(), delivery=dict(B.pin(DELIVERY), path=DELIVERY.relative_to(B.REPO).as_posix()),
        owner_of_the_vectors='DATI-TRANSFER, session 01a11c34', regime=delivery['regime'], policy=delivery['policy'],
        files=files, sources=described, minimum_targets=MINIMUM_TARGETS, below_minimum=below, problems=problems,
        usable=all(f['equal'] for f in files.values()) and not problems and not below,
        note='support is per gene; the per-source check against the genes each table votes runs in the kernel, '
             'where the tables are'))
    print(json.dumps(dict(equal={k: f['equal'] for k, f in files.items()}, problems=problems, below_minimum=below,
                          targets_behind={n: d['targets_behind_max'] for n, d in described.items()})))


def dataset_create(revision):
    from pipeline_state import CONFIG
    here = folder(revision)
    check = B.read(here / 'verifica.json')
    if not check['usable']:
        raise ValueError('the delivered vectors did not pass the verification')
    stage = DATA / ('t2_vettori_%s' % revision)
    stage.mkdir(parents=True, exist_ok=False)
    files = {}
    for key in ('common', 'support'):
        dest = stage / (key + '.npz')
        shutil.copy2(check['files'][key]['path'], dest)
        files[key] = B.pin(dest)
        assert files[key] == check['files'][key]['declared'], 'copy of %s differs from the delivery' % key
    dataset = '%s/vcc-validazione-t2-vettori-%s-%s' % (B.OWNER, B.SESSION, revision)
    (stage / 'dataset-metadata.json').write_text(json.dumps(dict(
        title=dataset.split('/')[1], id=dataset, licenses=[dict(name='other')]), indent=1) + '\n')
    (stage / 'README.json').write_text(json.dumps(dict(
        what='frozen all-target common vectors of the T2 transfer, production regime, as delivered by DATI-TRANSFER '
             '(session 01a11c34); copied unchanged for the leave-one-lineage-out bench',
        delivery=check['delivery'], files=files, not_a_candidate=True), indent=1) + '\n')
    env = {k: v for k, v in os.environ.items()
           if k not in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[B.OWNER])
    run = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), 'datasets', 'create', '-p', str(stage)],
                         env=env, capture_output=True, encoding='utf-8', errors='replace', timeout=1800)
    B.write_new(here / 'dataset_create.json', dict(
        utc=B.now(), dataset=dataset, private=True, stage=stage.as_posix(), files=files, returncode=run.returncode,
        answer=(run.stdout + run.stderr)[-800:],
        authorization='standing owner authorization for Colab and Kaggle (27 September 2026); a private dataset of '
                      'two small arrays already derived by DATI-TRANSFER, no new data, nothing paid',
        note='confirm with dataset-status: the progress bar is not text'))
    print(json.dumps(dict(dataset=dataset, returncode=run.returncode, tail=(run.stdout + run.stderr)[-200:])))


def dataset_status(revision, out):
    record = B.read(folder(revision) / 'dataset_create.json')
    rc, status = B.call(B.OWNER, ['datasets', 'status', record['dataset']])
    rc2, listing = B.call(B.OWNER, ['datasets', 'files', record['dataset'], '--csv', '--page-size', '50'])
    listed = {l.split(',')[0]: l.split(',')[1] for l in listing.splitlines()[1:] if l.strip()}
    B.write_new(out, dict(utc=B.now(), dataset=record['dataset'], status=status, files=listed,
                          ready=rc == 0 and rc2 == 0 and status.strip() == 'ready'))
    print(json.dumps(dict(status=status, files=listed)))


if __name__ == '__main__':
    {'verifica': verifica, 'dataset-create': dataset_create, 'dataset-status': dataset_status}[sys.argv[1]](*sys.argv[2:])
