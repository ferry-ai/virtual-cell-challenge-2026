"""Build, launch and collect the cloud package of the leave-one-lineage-out bench (level A).

    prepara_banco.py package <revision>              build banco/<revision>/package from the verified fit r1 package
    prepara_banco.py preflight <out.json>            read-only state of the three Kaggle accounts
    prepara_banco.py lancia <revision> <preflight>   one push, with ledger, dedup and slot check
    prepara_banco.py stato <revision> <out.json>     remote status, saved as observed
    prepara_banco.py raccogli <revision>             small outputs, saved-code check

The package is the verified package of the fit of release r1 (same repository snapshot, stage 100, contract
and bootstrap) with this folder's driver and measures, the frozen fold manifest and new params. The sources
mounted are the ones that fit mounted; nothing is uploaded besides the code. One CPU session, no GPU.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BANK = REPO / 'reports/modelli/banca_canonica_2026-10-07'
FIT_R1 = BANK / 'fit/r1'
RELEASE = BANK / 'fit/release_r1.json'
MANIFEST = HERE.parent / 'manifest_fold_v1.json'
T1_VERIFICATION = REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34/fit/dt1-01a11c34-r1/verification.json'
OWNER = 'davideferrante11'
SLOT_LIMIT = 5
SESSION = '8a8ca58a'
CRLF, LF = '\r\n', '\n'
sys.path.insert(0, str(REPO / 'reports/modelli/percorso_riusabile_2026-10-05'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pin(path):
    return dict(bytes=Path(path).stat().st_size, sha256=sha(path))


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, payload):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(payload, f, indent=1)
        f.write('\n')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def call(owner, args):
    from preflight_slots_fast_v1 import call as kaggle
    return kaggle(owner, args)


def saved_kernel(owner, slug):
    """The code Kaggle saved for a kernel, read with the owner's token (as banca_canonica's percorso.py)."""
    import os
    from pipeline_state import CONFIG
    for key in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN'):
        os.environ.pop(key, None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiGetKernelRequest
    api = KaggleApi()
    api.authenticate()
    request = ApiGetKernelRequest()
    request.user_name = owner
    request.kernel_slug = slug
    with api.build_kaggle_client() as client:
        return client.kernels.kernels_api_client.get_kernel(request)


def package(revision):
    stage = HERE / revision / 'package'
    stage.mkdir(parents=True, exist_ok=False)
    prepared_r1 = read(FIT_R1 / 'prepared.json')
    source = FIT_R1 / 'package/run.py'
    assert sha(source) == prepared_r1['code']['sha256'], 'the verified fit package changed'
    old = source.read_text(encoding='utf-8')
    match = re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)", old)
    head, tail = old[:match.start(1)], old[match.end(1):]
    members = {}
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as z:
        for info in z.infolist():
            if not info.is_dir():
                members[info.filename] = z.read(info)
    params_old = json.loads(members['params.json'])
    for rel, digest in params_old['embedded_sha256'].items():
        assert hashlib.sha256(members[rel]).hexdigest() == digest, 'fit package member changed: ' + rel
    assert hashlib.sha256(members['release.json']).hexdigest() == sha(RELEASE) == params_old['release_sha256']
    consumo = read(FIT_R1 / 'completion/consumo.json')
    recorded = {'T0': consumo['contexts']['A']['reference_sha256'], 'R1': consumo['contexts']['A']['release_sha256'],
                'T1': read(T1_VERIFICATION)['effects']['A']['sha256']}
    for ctx in ('B', 'C'):      # the transfer does not read the destination context
        assert consumo['contexts'][ctx]['reference_sha256'] == recorded['T0']
        assert consumo['contexts'][ctx]['release_sha256'] == recorded['R1']
    driver = (HERE / 'logo_driver.py').read_bytes().replace(b'\r\n', b'\n')
    measures = (HERE / 'metrics.py').read_bytes().replace(b'\r\n', b'\n')
    core = (HERE / 'bench_core.py').read_bytes().replace(b'\r\n', b'\n')
    manifest = MANIFEST.read_bytes()
    embedded = dict(params_old['embedded_sha256'])
    embedded['driver.py'] = hashlib.sha256(driver).hexdigest()
    embedded['metrics.py'] = hashlib.sha256(measures).hexdigest()
    embedded['bench_core.py'] = hashlib.sha256(core).hexdigest()
    slug = '%s/vcc-validazione-logo-%s-%s' % (OWNER, SESSION, revision)
    params = dict(kind='leave_one_lineage_out_bench_level_A', slug=slug, effects_only=True,
                  release_sha256=params_old['release_sha256'], manifest_sha256=hashlib.sha256(manifest).hexdigest(),
                  coords=params_old['coords'], axis=params_old['axis'], embedded_sha256=embedded,
                  recorded_production_effects_sha256=recorded,
                  reference_package_run_sha256=sha(source), not_vcc_scores=True, loss=None, optimizer=None)
    plan_path = HERE / ('analisi_%s.json' % revision)      # optional: analysis arms, external arms, contrasts
    plan = read(plan_path) if plan_path.is_file() else {}
    for key in ('analysis_arms', 'external_arms', 'contrasts'):
        if plan.get(key):
            params[key] = plan[key]
    members.update({'driver.py': driver, 'metrics.py': measures, 'bench_core.py': core,
                    'manifest_fold.json': manifest,
                    'params.json': (json.dumps(params, indent=1) + '\n').encode()})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0)), members[name], zipfile.ZIP_DEFLATED)
    code = head + base64.b64encode(buffer.getvalue()).decode() + tail
    compile(code, 'run.py', 'exec')
    compile(driver.decode('utf-8'), 'driver.py', 'exec')
    (stage / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    (stage / 'params.json').write_bytes(members['params.json'])
    meta = read(FIT_R1 / 'package/kernel-metadata.json')
    meta.update(id=slug, title=slug.split('/')[1], is_private=True, enable_gpu=False)
    meta['dataset_sources'] = sorted(set(meta['dataset_sources']) | set(plan.get('extra_dataset_sources', [])))
    meta['kernel_sources'] = sorted(set(meta['kernel_sources']) | set(plan.get('extra_kernel_sources', [])))
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    write_new(HERE / revision / 'prepared.json', dict(
        utc=now(), slug=slug, stage=stage.relative_to(REPO).as_posix(), code=pin(stage / 'run.py'),
        params=pin(stage / 'params.json'), driver=dict(path='banco/logo_driver.py', sha256_lf=embedded['driver.py']),
        measures=dict(path='banco/metrics.py', sha256_lf=embedded['metrics.py']),
        core=dict(path='banco/bench_core.py', sha256_lf=embedded['bench_core.py']),
        manifest=dict(pin(MANIFEST), path=MANIFEST.relative_to(REPO).as_posix()),
        release=dict(pin(RELEASE), path=RELEASE.relative_to(REPO).as_posix()),
        t1_verification=dict(pin(T1_VERIFICATION), path=T1_VERIFICATION.relative_to(REPO).as_posix()),
        analysis_plan=dict(pin(plan_path), path=plan_path.relative_to(REPO).as_posix()) if plan else None,
        recorded_production_effects_sha256=recorded, reused_fit_package=dict(pin(source), unchanged_members=len(
            params_old['embedded_sha256']) - 1), metadata=meta, compute_started=False))
    for name, body in (('driver.py', driver), ('metrics.py', measures), ('bench_core.py', core)):
        compile(body.decode('utf-8'), name, 'exec')
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()), kernels=len(meta['kernel_sources']),
                          datasets=meta['dataset_sources'], recorded=recorded)))


def preflight(out):
    from pipeline_state import CONFIG
    import csv
    observed, active = [], {}
    for owner in CONFIG:
        rc, body = call(owner, ['kernels', 'list', '--mine', '--page-size', '20', '--sort-by', 'dateRun', '--csv'])
        if rc:
            raise RuntimeError('account listing failed: ' + owner)
        refs = [r['ref'] for r in csv.DictReader(io.StringIO(body)) if r.get('ref')]
        active[owner] = 0
        for ref in refs:
            rc, status = call(owner, ['kernels', 'status', ref])
            busy = bool(rc) or 'RUNNING' in status or 'QUEUED' in status
            active[owner] += int(busy)
            observed.append(dict(owner=owner, job=ref, returncode=rc, status=status, counted_active=busy))
    write_new(out, dict(utc=now(), scope='20 latest dateRun kernels per account; quota not exposed by this check',
                        active=active, slot_limit_per_account=SLOT_LIMIT, observed=observed))
    print(json.dumps(dict(active=active)))


def lancia(revision, preflight_path):
    here = HERE / revision
    proof = read(here / 'prepared.json')
    pre = read(preflight_path)
    if (datetime.now(timezone.utc) - datetime.fromisoformat(pre['utc'])).total_seconds() > 900:
        raise ValueError('fresh preflight required')
    if pre['active'].get(OWNER, 0) >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full')
    stage = REPO / proof['stage']
    if sha(stage / 'run.py') != proof['code']['sha256'] or sha(stage / 'params.json') != proof['params']['sha256']:
        raise ValueError('prepared package changed')
    rc, body = call(OWNER, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'])
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=now(), slug=proof['slug'], owner=OWNER, stage=proof['stage'], code_sha256=proof['code']['sha256'],
                   params_sha256=proof['params']['sha256'], preflight_sha256=sha(preflight_path), private=True,
                   authorization='standing owner authorization for Colab and Kaggle compute (27 September 2026, '
                                 'confirmed for several accounts on 30 September); CPU only, nothing paid, no upload '
                                 'of data: the kernel mounts sources already on Kaggle',
                   incidents=['E-20261003-001', 'E-20260929-004', 'E-20260929-005'],
                   guards=['one explicit push by this command, no loop', 'dedup lookup before the push',
                           'fresh slot preflight', 'every input resolved by size and sha256 on the runtime before '
                           'any computation', 'new output names only'],
                   state='intent', accepted=False)
    write_new(here / 'launch.json', receipt)
    rc, body = call(OWNER, ['kernels', 'push', '-p', str(stage)])
    receipt.update(returncode=rc, answer=body, state='push_returned', accepted=rc == 0 and 'successfully pushed' in body)
    if receipt['accepted']:
        rc, status = call(OWNER, ['kernels', 'status', proof['slug']])
        receipt.update(remote_status_returncode=rc, remote_status=status, remote_status_utc=now())
    (here / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status')}))


def stato(revision, out):
    proof = read(HERE / revision / 'prepared.json')
    rc, status = call(OWNER, ['kernels', 'status', proof['slug']])
    write_new(out, dict(utc=now(), slug=proof['slug'], returncode=rc, status=status))
    print(status)


def raccogli(revision):
    here = HERE / revision
    launch = read(here / 'launch.json')
    rc, status = call(OWNER, ['kernels', 'status', launch['slug']])
    print(status)
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    done = 'COMPLETE' in status
    out = here / ('completion' if done else 'failure')
    out.mkdir(exist_ok=False)
    write_new(out / 'provider_status.json', dict(utc=now(), returncode=rc, status=status))
    pattern = ('results.json|status.json|parity.json|consumption.json|table_audit.json|per_target.csv|'
               'runtime_versions.json|recipe_reference_t36.json|.*\\.log')
    rc, answer = call(OWNER, ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern', pattern])
    write_new(out / 'retrieval.json', dict(utc=now(), returncode=rc, answer=answer[-2000:]))
    if not done:
        return
    saved = saved_kernel(OWNER, launch['slug'].split('/')[1])
    stage = REPO / launch['stage']
    assert sha(stage / 'run.py') == launch['code_sha256'], 'launched package changed'
    same = saved.blob.source.replace(CRLF, LF) == (stage / 'run.py').read_text(encoding='utf-8').replace(CRLF, LF)
    results = read(out / 'results.json')
    write_new(out / 'verification.json', dict(
        utc=now(), job=launch['slug'], version=saved.metadata.current_version_number, saved_code_matches=same,
        code_sha256=launch['code_sha256'], results=pin(out / 'results.json'), per_target=pin(out / 'per_target.csv'),
        consumption=pin(out / 'consumption.json'), parity=results['parity'],
        manifest_sha256=results['manifest_sha256'], release_sha256=results['release_sha256'],
        verified=bool(same and all(p['equal'] for p in results['parity'].values()))))
    print(json.dumps(dict(saved_code_matches=same, parity={a: p['equal'] for a, p in results['parity'].items()})))


if __name__ == '__main__':
    {'package': package, 'preflight': preflight, 'lancia': lancia, 'stato': stato,
     'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
