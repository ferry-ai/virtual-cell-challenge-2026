"""Freeze a source release and build the cloud package of its fit.

    prepara_fit.py dataset <stage_dir>        stage the derived tables as one Kaggle dataset
    prepara_fit.py release <release.json>     freeze the release from the admission record
    prepara_fit.py package <release.json> <revision>   build fit/<revision>/package

The package is the verified t36 package (same repo snapshot, stage 100, contract and bootstrap)
with this folder's driver, a new params.json and the frozen release. Nothing else changes.
"""
import base64
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import percorso as P  # noqa: E402

T36 = P.REUSE / 'generation_successors_r1'
T36_RELEASE = P.REUSE / 'release_t36_reuse_r1.json'
MIX_CHECKPOINT = P.REUSE / 'extended_mix_completion_r1/model/checkpoint.json'
REV = P.os.environ.get('VCC_BANCA_REV', 'r1')  # revision of admission, dataset and release
ADMISSION = HERE.parent / ('ammissione_%s.json' % REV)
DATASET = 'davideferrante11/vcc-banca-canonica-derivati-' + REV
OWNER = 'davideferrante11'
CRLF, LF = '\r\n', '\n'


def admission():
    return json.loads(ADMISSION.read_text(encoding='utf-8'))


def dataset(stage):
    """Flat copy of every derived table (all arms) plus the admission record."""
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=False)
    listing = {}
    for name, record in admission()['sources'].items():
        source = Path(record['table']['path'])
        assert P.pin(source) == dict(bytes=record['table']['bytes'], sha256=record['table']['sha256'])
        shutil.copy2(source, stage / record['table']['name'])
        listing[record['table']['name']] = dict(bytes=record['table']['bytes'], sha256=record['table']['sha256'],
                                                 arm=record['arm'], vote=record['vote'])
    shutil.copy2(ADMISSION, stage / ADMISSION.name)
    (stage / 'dataset-metadata.json').write_text(json.dumps(dict(
        title=DATASET.split('/')[1], id=DATASET, licenses=[dict(name='other')]), indent=1) + '\n')
    P.write_new(HERE / ('dataset_%s.json' % REV), dict(utc=P.now(), dataset=DATASET, private=True, stage=stage.as_posix(),
                                               files=listing, admission=P.pin(ADMISSION)))
    print(json.dumps(dict(files=len(listing), bytes=sum(f['bytes'] for f in listing.values()))))


def release(out):
    record = json.loads((T36 / 'records_r1/prediction_record.json').read_text(encoding='utf-8'))
    t36 = json.loads(T36_RELEASE.read_text(encoding='utf-8'))
    checkpoint = {f['path']: f for f in json.loads(MIX_CHECKPOINT.read_text(encoding='utf-8'))['files']}
    voted, parts = {}, {}
    for name, origin in record['origin'].items():
        if origin['role'] != 'voted':
            parts[name] = dict(bytes=origin['bytes'], sha256=origin['sha256'])
            continue
        entry = dict(bytes=origin['bytes'], sha256=origin['sha256'], in_reference=True)
        if origin.get('successor'):
            s = origin['successor']
            entry.update(kind='successor', kernel=s['kernel'], version=s['version'], receipt_sha256=s['receipt_sha256'],
                         count_sum_sha256=s['count_sum_sha256'], targets=s['targets'])
        elif name == 'k562':
            entry.update(kind='historic', dataset='davideferrante11/vcc-k562-t25-cache-r1', file='k562.npz.bin',
                         note='historical K562 BULK table of the t25 recipe; not the single-cell GWPS bank')
        else:
            cached = checkpoint['cache/%s.npz' % name]
            assert cached['sha256'] == origin['sha256'] and cached['bytes'] == origin['bytes'], name
            entry.update(kind='mix_cache', kernel='davideferrante11/vcc-effects-mix-t25-bank-r1-retry1')
        voted[name] = entry
    assert sorted(voted) == sorted(record['voted_sources'])
    adm = admission()
    arms, refused = {}, {}
    for name, r in adm['sources'].items():
        pinned = dict(bytes=r['table']['bytes'], sha256=r['table']['sha256'], job=r['job'], version=r['version'],
                      receipt=r['receipt'], study=r['study'], modality=r['modality'], units=r['units'],
                      targets=r['targets'], target_cells=r['target_cells'], control_cells=r['control_cells'],
                      knockdown=r['knockdown'], decision=r['decision'])
        if r['vote']:
            assert name not in voted
            voted[name] = dict(pinned, kind='fragment', dataset=DATASET, file=r['table']['name'], in_reference=False)
        elif r['arm'] == 'crispri':
            refused[name] = pinned
        else:
            arms[name] = dict(pinned, arm=r['arm'], dataset=DATASET, file=r['table']['name'])
    document = dict(
        name='banca-canonica-' + REV, kind='frozen_source_release_of_the_t25_transfer',
        why=('t25 weight-1 policy on every source of the t36 release plus the CRISPRi sources admitted by the '
             'registered rule of banca_canonica_2026-10-07. Amplitude and the original cis pairs are applied once '
             'downstream, not in the mixer.'),
        frozen_utc=P.now(), claims_complete_corpus=False, not_heldout_validation=True,
        expected=dict(path=P.EXPECTED.relative_to(P.REPO).as_posix(), sha256=P.EXPECTED_SHA),
        admission=dict(P.pin(ADMISSION), path=ADMISSION.relative_to(P.REPO).as_posix()),
        protocol=dict(P.pin(HERE.parent / 'PROTOCOLLO.md'), path='reports/modelli/banca_canonica_2026-10-07/PROTOCOLLO.md'),
        axis_sha256=P.AXIS_SHA, panel_sha256=P.PANEL_SHA,
        reference=dict(entry='t36', recipe_sha256=record['recipe_sha256'],
                       fingerprint=dict(P.pin(T36_RELEASE), path=T36_RELEASE.relative_to(P.REPO).as_posix()),
                       cloud_job=t36['cloud_job'], sources=sorted(record['voted_sources'])),
        mix=dict(kernel='davideferrante11/vcc-effects-mix-t25-bank-r1-retry1',
                 checkpoint_sha256=P.sha(MIX_CHECKPOINT), cd4_parts=parts),
        voted=voted, derived_not_voted=arms, derived_not_admitted=refused, not_launched=adm['not_launched'])
    P.write_new(out, document)
    print(json.dumps(dict(voted=len(voted), new=[n for n, v in voted.items() if not v['in_reference']],
                          arms=sorted(arms), refused=sorted(refused), sha256=P.sha(out))))


def package(release_path, revision):
    release_path = Path(release_path).resolve()
    stage = HERE / revision / 'package'
    stage.mkdir(parents=True, exist_ok=False)
    old = (T36 / 'package/run.py').read_text(encoding='utf-8')
    match = re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)", old)
    head, tail = old[:match.start(1)], old[match.end(1):]
    members = {}
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as z:
        for info in z.infolist():
            if not info.is_dir():
                members[info.filename] = z.read(info)
    params_old = json.loads(members['params.json'])
    for rel, digest in params_old['embedded_sha256'].items():
        assert P.hashlib.sha256(members[rel]).hexdigest() == digest, 'reference package member changed: ' + rel
    assert P.sha(T36 / 'package/run.py') == json.loads(T36_RELEASE.read_text())['package_files'][0]['sha256']
    driver = (HERE / 'driver.py').read_bytes()
    release_bytes = release_path.read_bytes()
    embedded = dict(params_old['embedded_sha256'])
    embedded['driver.py'] = P.hashlib.sha256(driver).hexdigest()
    slug = '%s/vcc-fit-banca-canonica-%s' % (OWNER, revision)
    params = dict(kind='t25_transfer_fit_on_frozen_release_effects_only', slug=slug, effects_only=True,
                  release_sha256=P.hashlib.sha256(release_bytes).hexdigest(), coords=params_old['coords'],
                  axis=params_old['axis'], embedded_sha256=embedded, reference_package_run_sha256=P.sha(T36 / 'package/run.py'),
                  claims_complete_training=False, loss=None, optimizer=None)
    members.update({'driver.py': driver, 'release.json': release_bytes,
                    'params.json': (json.dumps(params, indent=1) + '\n').encode()})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 7, 0, 0, 0)), members[name], zipfile.ZIP_DEFLATED)
    code = head + base64.b64encode(buffer.getvalue()).decode() + tail
    compile(code, 'run.py', 'exec')
    (stage / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    (stage / 'params.json').write_bytes(members['params.json'])
    (stage / 'release.json').write_bytes(release_bytes)
    rel = json.loads(release_bytes)
    kernels = sorted({v['kernel'] for v in rel['voted'].values() if v.get('kernel')} | {rel['mix']['kernel']})
    datasets = sorted({v['dataset'] for v in rel['voted'].values() if v.get('dataset')}
                      | {'davideferrante11/vcc-ingest-code-cd4-r1'})
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=True,
                dataset_sources=datasets, kernel_sources=kernels, competition_sources=[])
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    P.write_new(HERE / revision / 'prepared.json', dict(
        utc=P.now(), slug=slug, stage=stage.relative_to(P.REPO).as_posix(), code=P.pin(stage / 'run.py'),
        params=P.pin(stage / 'params.json'), release=dict(P.pin(release_path), path=release_path.relative_to(P.REPO).as_posix()),
        driver_sha256=embedded['driver.py'], unchanged_members=len(params_old['embedded_sha256']) - 1,
        metadata=meta, compute_started=False))
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()), kernels=len(kernels), datasets=datasets)))


def dataset_create(stage, out):
    """Upload the staged tables as one private dataset. Native path: the CLI breaks on forward slashes."""
    import subprocess
    env = {k: v for k, v in P.os.environ.items()
           if k not in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / P.CONFIG[OWNER])
    run = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), 'datasets', 'create', '-p',
                          str(Path(stage).resolve())], env=env, capture_output=True, encoding='utf-8',
                         errors='replace', timeout=1800)
    P.write_new(out, dict(utc=P.now(), dataset=DATASET, returncode=run.returncode,
                          answer=(run.stdout + run.stderr)[-800:],
                          note='the progress bar is not reliable text: confirm with dataset-status'))
    print(json.dumps(dict(returncode=run.returncode)))


def dataset_status(out):
    rc, status = P.call(OWNER, ['datasets', 'status', DATASET])
    rc2, files = P.call(OWNER, ['datasets', 'files', DATASET, '--csv', '--page-size', '50'])
    listed = {line.split(',')[0]: int(line.split(',')[1]) for line in files.splitlines()[1:] if line.strip()}
    expected = json.loads((HERE / ('dataset_%s.json' % REV)).read_text(encoding='utf-8'))['files']
    ok = rc == 0 and rc2 == 0 and status == 'ready' and all(listed.get(n) == f['bytes'] for n, f in expected.items())
    P.write_new(out, dict(utc=P.now(), dataset=DATASET, status=status, files=listed, sizes_match_stage=ok,
                          note='sizes only; the fit verifies every sha256 it consumes'))
    print(json.dumps(dict(status=status, files=len(listed), sizes_match_stage=ok)))


def lancia(revision, preflight_path):
    here = HERE / revision
    proof = json.loads((here / 'prepared.json').read_text(encoding='utf-8'))
    pre = json.loads(Path(preflight_path).read_text(encoding='utf-8'))
    if (P.datetime.now(P.timezone.utc) - P.datetime.fromisoformat(pre['utc'])).total_seconds() > 900:
        raise ValueError('fresh preflight required')
    if pre['active'].get(OWNER, 0) >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full')
    stage = P.REPO / proof['stage']
    if P.sha(stage / 'run.py') != proof['code']['sha256'] or P.sha(stage / 'params.json') != proof['params']['sha256']:
        raise ValueError('prepared package changed')
    rc, body = P.call(OWNER, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'])
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=P.now(), slug=proof['slug'], owner=OWNER, stage=proof['stage'], code_sha256=proof['code']['sha256'],
                   params_sha256=proof['params']['sha256'], release_sha256=proof['release']['sha256'],
                   preflight_sha256=P.sha(preflight_path), state='intent', accepted=False)
    P.write_new(here / 'launch.json', receipt)
    rc, body = P.call(OWNER, ['kernels', 'push', '-p', str(stage)])
    receipt.update(returncode=rc, answer=body, state='push_returned', accepted=rc == 0 and 'successfully pushed' in body)
    if receipt['accepted']:
        rc, status = P.call(OWNER, ['kernels', 'status', proof['slug']])
        receipt.update(remote_status_returncode=rc, remote_status=status)
    (here / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status')}))


def raccogli(revision):
    here = HERE / revision
    launch = json.loads((here / 'launch.json').read_text(encoding='utf-8'))
    rc, status = P.call(OWNER, ['kernels', 'status', launch['slug']])
    print(status)
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    done = 'COMPLETE' in status
    out = here / ('completion' if done else 'failure')
    out.mkdir(exist_ok=False)
    P.write_new(out / 'provider_status.json', dict(utc=P.now(), returncode=rc, status=status))
    pattern = 'consumo.json|status.json|reference_manifest.json|recipe_.*json|runtime_versions.json|manifest.json'
    rc, answer = P.call(OWNER, ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern', pattern])
    P.write_new(out / 'retrieval.json', dict(returncode=rc, answer=answer))
    if not done:
        return
    saved = P.saved_kernel(OWNER, launch['slug'].split('/')[1])
    stage = P.REPO / launch['stage']
    assert P.sha(stage / 'run.py') == launch['code_sha256'], 'launched package changed'
    assert saved.blob.source.replace(CRLF, LF) == (stage / 'run.py').read_text(encoding='utf-8').replace(CRLF, LF), 'saved code differs'
    consumo = json.loads((out / 'consumo.json').read_text(encoding='utf-8'))
    assert consumo['release_sha256'] == launch['release_sha256']
    assert consumo['sources_expected'] == consumo['sources_verified'] == consumo['sources_read_by_stage100']
    P.write_new(out / 'verification.json', dict(
        utc=P.now(), job=launch['slug'], version=saved.metadata.current_version_number, saved_code_matches=True,
        code_sha256=launch['code_sha256'], release_sha256=launch['release_sha256'], consumo=P.pin(out / 'consumo.json'),
        sources=consumo['sources_verified'], recipe_sha256=consumo['recipe_sha256'],
        effects={c: v['release_sha256'] for c, v in consumo['contexts'].items()},
        reference_effects={c: v['reference_sha256'] for c, v in consumo['contexts'].items()},
        targets_changed_outside_added_votes=consumo['targets_changed_outside_added_votes'], verified=True))
    print(json.dumps(dict(sources=len(consumo['sources_verified']), added=consumo['sources_added_to_reference'],
                          touched=consumo['targets_with_added_votes'],
                          outside=consumo['targets_changed_outside_added_votes'])))


if __name__ == '__main__':
    {'dataset': dataset, 'release': release, 'package': package, 'dataset-status': dataset_status,
     'dataset-create': dataset_create,
     'lancia': lancia, 'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
