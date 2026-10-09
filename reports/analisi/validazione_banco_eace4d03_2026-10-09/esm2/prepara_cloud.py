"""Package, launch and collect the cloud run of the fallback support audit (contract v3, sections 1-2).

One private CPU kernel on the account where every input is already mounted natively: the fold effects and
the published results of the closure run, the fallback and external arms delivered by MODELLI-ESTERNI, the
truth tables of release r1. Nothing is uploaded besides the code, nothing crosses accounts, nothing is
trained. The kernel finds each input by pinned size and sha256 and runs `supporto_fallback.py` unchanged.

    prepara_cloud.py package <revision>
    prepara_cloud.py preflight <out.json>
    prepara_cloud.py lancia <revision> <preflight.json>
    prepara_cloud.py stato <revision> <out.json>
    prepara_cloud.py raccogli <revision>
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'reports/modelli/percorso_riusabile_2026-10-05'))
import supporto_fallback as S  # noqa: E402

MODELLI = REPO / 'reports/analisi/modelli_esterni_01a11c35_2026-10-08'
RELEASE = REPO / 'reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json'
OWNER = 'davideferrante11'
SESSION = 'eace4d03'
SLOT_LIMIT = 5
FOLDS = ('C-K562', 'C-iPSC')
KERNEL_SOURCES = ['davideferrante11/vcc-validazione-logo-01a11c35-esm2closure-r1',
                  'davidmaisterx/vcc-prod-kolf-pan-genome-mask-r1']
DATASET_SOURCES = ['davideferrante11/vcc-esm2-closure-01a11c35-r1', 'davideferrante11/vcc-k562-t25-cache-r1']
RUN = r'''
import base64, hashlib, io, json, platform, subprocess, sys, time, zipfile
from pathlib import Path
INPUT, WORK = Path("/kaggle/input"), Path("/kaggle/working")
PKG = WORK / "pkg"
t0 = time.time()
with zipfile.ZipFile(io.BytesIO(base64.b64decode("__ZIP__"))) as z:
    z.extractall(PKG)
P = json.loads((PKG / "params.json").read_text())


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


for rel, digest in P["embedded_sha256"].items():
    if sha(PKG / rel) != digest:
        raise SystemExit("embedded file changed: " + rel)
files = [p for p in INPUT.rglob("*") if p.is_file()]
sizes = {}
for p in files:
    sizes.setdefault(p.stat().st_size, []).append(p)


def find(pin, label):
    for p in sizes.get(pin["bytes"], []):
        if sha(p) == pin["sha256"]:
            return str(p)
    raise SystemExit("input not mounted with the pinned content: " + label)


status = {"folds": {}, "inputs": {}, "python": platform.python_version()}
for fold, spec in P["specs"].items():
    for name, entry in spec["arms"].items():
        entry["path"] = find(entry, fold + "/" + name)
    for name in ("fallback", "E2", "E2g", "truth", "closure_results"):
        spec[name]["path"] = find(spec[name], fold + "/" + name)
    status["inputs"][fold] = {n: spec[n]["path"] for n in ("fallback", "E2", "E2g", "truth", "closure_results")}
    spec_path = WORK / ("spec_%s.json" % fold)
    spec_path.write_text(json.dumps(spec, indent=1))
    out = WORK / ("supporto_%s.json" % fold)
    r = subprocess.run([sys.executable, "-W", "ignore", str(PKG / "supporto_fallback.py"), "--spec", str(spec_path),
                        "--out", str(out), "--bench-dir", str(PKG)], capture_output=True, text=True)
    (WORK / ("log_%s.txt" % fold)).write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
    done = json.loads(out.read_text()) if out.is_file() else {}
    status["folds"][fold] = {"returncode": r.returncode, "parity": (done.get("parity") or {}).get("passed"),
                             "adapter": (done.get("adapter") or {}).get("passed"), "stopped": done.get("stopped")}
import numpy
status.update(numpy=numpy.__version__, seconds=round(time.time() - t0, 1),
              usable=all(f["returncode"] == 0 and f["parity"] and f["adapter"] for f in status["folds"].values()))
(WORK / "status.json").write_text(json.dumps(status, indent=1))
print(json.dumps(status), flush=True)
import shutil
shutil.rmtree(PKG)
if not status["usable"]:
    raise SystemExit("support audit not usable: see status.json")
'''


def sha(path):
    return S.sha(path)


def pin(path):
    return dict(bytes=Path(path).stat().st_size, sha256=sha(path))


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, payload):
    with Path(path).open('x', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=1)
        fh.write('\n')


def call(owner, args):
    from preflight_slots_fast_v1 import call as kaggle
    return kaggle(owner, args)


def spec_for(fold, local_arms_dir):
    """Pins only: the expected sha256 come from receipts, the sizes from local copies already verified against
    those receipts (arms) or from the receipts themselves. No runtime path here."""
    conversion = read(MODELLI / 'esm2_closure_conversion_r1.json')['folds'][fold]
    retrieval = read(MODELLI / 'esm2_closure_retrieval_r1.json')['files']
    external = read(retrieval['external_arms.json']['path'])
    consumption = {(c['label'], c['context']): c for c in read(retrieval['consumption.json']['path'])}
    published = read(retrieval['results.json']['path'])['folds'][fold]['truth']
    tname = next(t for t, v in published.items() if v['role'] == 'primary')
    release = read(RELEASE)['voted'][tname]
    arms = {}
    for arm in S.ARMS:
        local = Path(local_arms_dir) / (arm + '.npz')
        expected = consumption[(arm, fold)]['effects_sha256']
        if sha(local) != expected:
            raise SystemExit('local copy of %s/%s differs from the closure receipt' % (fold, arm))
        arms[arm] = dict(bytes=local.stat().st_size, sha256=expected)
    integration = conversion['integration']
    if integration['t0_sha256'] != arms['T0']['sha256']:
        raise SystemExit('the fallback was built on another T0')
    def ext(label):
        e = external['%s/%s' % (label, fold)]
        return dict(bytes=e['bytes'], sha256=e['sha256'])
    if ext('E2f')['sha256'] != integration['sha256']:
        raise SystemExit('the measured fallback is not the delivered one')
    return {'fold': fold, 'truth_table': tname, 'amplitude': integration['amplitude_applied_once_to_fallback'],
            'fallback_label': 'E2f', 'integration_contrast': 'C_integration',
            'expected_filled_pairs': integration['fallback_pairs'], 'arms': arms, 'fallback': ext('E2f'),
            'E2': ext('E2'), 'E2g': ext('E2g'), 'truth': dict(bytes=release['bytes'], sha256=release['sha256']),
            'closure_results': dict(bytes=retrieval['results.json']['bytes'], sha256=retrieval['results.json']['sha256'])}


def package(revision):
    stage = HERE / ('cloud_' + revision) / 'package'
    stage.mkdir(parents=True, exist_ok=False)
    data = Path('C:/Users/ferra/vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08')
    specs = {'C-K562': spec_for('C-K562', data / 'effetti_k562_r1'), 'C-iPSC': spec_for('C-iPSC', data / 'effetti_ipsc_r1')}
    members = {'supporto_fallback.py': (HERE / 'supporto_fallback.py').read_bytes(),
               'metrics.py': (S.FROZEN_BENCH / 'metrics.py').read_bytes()}
    if hashlib.sha256(members['metrics.py']).hexdigest() != S.METRICS_SHA256:
        raise SystemExit('metrics.py is not the frozen file')
    slug = '%s/vcc-validazione-supporto-%s-%s' % (OWNER, SESSION, revision)
    params = dict(kind='fallback_support_audit', slug=slug, contract='PROTOCOLLO_v3 sections 1-2 and ADDENDUM_v3_1',
                  specs=specs, embedded_sha256={k: hashlib.sha256(v).hexdigest() for k, v in members.items()},
                  not_vcc_scores=True, trains_nothing=True)
    members['params.json'] = (json.dumps(params, indent=1) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 9, 0, 0, 0)), members[name], zipfile.ZIP_DEFLATED)
    code = RUN.replace('__ZIP__', base64.b64encode(buffer.getvalue()).decode())
    compile(code, 'run.py', 'exec')
    (stage / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    (stage / 'params.json').write_bytes(members['params.json'])
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=False,
                dataset_sources=DATASET_SOURCES, kernel_sources=KERNEL_SOURCES, competition_sources=[])
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    write_new(stage.parent / 'prepared.json', dict(
        utc=now(), slug=slug, owner=OWNER, stage=stage.relative_to(REPO).as_posix(), code=pin(stage / 'run.py'),
        params=pin(stage / 'params.json'), audit=dict(path='esm2/supporto_fallback.py', sha256=sha(HERE / 'supporto_fallback.py')),
        measures=dict(path='banco/metrics.py of the frozen bench', sha256=S.METRICS_SHA256), folds=list(specs),
        metadata=meta, uploads_nothing_but_code=True, crosses_no_account=True, compute_started=False))
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()), folds=list(specs))))


def preflight(out):
    from pipeline_state import CONFIG
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
    here = HERE / ('cloud_' + revision)
    proof = read(here / 'prepared.json')
    pre = read(preflight_path)
    if (datetime.now(timezone.utc) - datetime.fromisoformat(pre['utc'])).total_seconds() > 900:
        raise ValueError('fresh preflight required')
    if pre['active'].get(OWNER, 0) >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full')
    stage = REPO / proof['stage']
    if sha(stage / 'run.py') != proof['code']['sha256']:
        raise ValueError('prepared package changed')
    rc, body = call(OWNER, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'])
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=now(), slug=proof['slug'], owner=OWNER, stage=proof['stage'], code_sha256=proof['code']['sha256'],
                   preflight_sha256=sha(preflight_path), private=True,
                   authorization='owner in chat, 9 October 2026, assignment of this session: cloud CPU for the benches; '
                                 'CPU only, nothing paid, nothing uploaded besides the code, no cross-account transfer',
                   incidents=['E-20261003-001'],
                   guards=['one explicit push by this command, no loop', 'dedup lookup before the push',
                           'fresh slot preflight', 'every input found by pinned size and sha256 on the runtime',
                           'parity with the published run before any diagnostic'],
                   state='intent', accepted=False)
    write_new(here / 'launch.json', receipt)
    rc, body = call(OWNER, ['kernels', 'push', '-p', str(stage)])
    receipt.update(returncode=rc, answer=body, state='push_returned',
                   accepted=rc == 0 and 'successfully pushed' in body and 'not valid' not in body)
    if receipt['accepted']:
        rc, status = call(OWNER, ['kernels', 'status', proof['slug']])
        receipt.update(remote_status_returncode=rc, remote_status=status, remote_status_utc=now())
    (here / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status', 'answer')}))


def stato(revision, out):
    proof = read(HERE / ('cloud_' + revision) / 'prepared.json')
    rc, status = call(OWNER, ['kernels', 'status', proof['slug']])
    write_new(out, dict(utc=now(), slug=proof['slug'], returncode=rc, status=status))
    print(status)


def raccogli(revision):
    here = HERE / ('cloud_' + revision)
    launch = read(here / 'launch.json')
    rc, status = call(OWNER, ['kernels', 'status', launch['slug']])
    print(status)
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    out = here / ('completion' if 'COMPLETE' in status else 'failure')
    out.mkdir(exist_ok=False)
    write_new(out / 'provider_status.json', dict(utc=now(), returncode=rc, status=status))
    rc, answer = call(OWNER, ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern',
                              'supporto_.*\\.json|spec_.*\\.json|status.json|log_.*\\.txt|.*\\.log'])
    write_new(out / 'retrieval.json', dict(utc=now(), returncode=rc, answer=answer[-2000:]))


if __name__ == '__main__':
    {'package': package, 'preflight': preflight, 'lancia': lancia, 'stato': stato,
     'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
