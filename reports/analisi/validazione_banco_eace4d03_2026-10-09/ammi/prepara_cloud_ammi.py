"""Stage, launch and collect the cloud read of the AMMI `none` exports on both folds (LETTURA_AMMI_NONE.md).

The two exports were downloaded from the account that trained them and are uploaded here as ONE private dataset
of the account where every other input is already mounted (authorization: owner in chat, 9 October 2026, 21:42:
two files, 36,281,758 bytes). The kernel is CPU only, finds each input by pinned size and sha256, and runs
`lettura_esterni.py` with the frozen `metrics.py` and `bench_core.py`.

    prepara_cloud_ammi.py stage                      copy the two verified exports into a dataset folder
    prepara_cloud_ammi.py dataset-create
    prepara_cloud_ammi.py dataset-status <out.json>
    prepara_cloud_ammi.py package <revision>
    prepara_cloud_ammi.py lancia <revision> <preflight.json>
    prepara_cloud_ammi.py stato <revision> <out.json>
    prepara_cloud_ammi.py raccogli <revision>
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'esm2'))
sys.path.insert(0, str(REPO / 'reports/modelli/percorso_riusabile_2026-10-05'))
import lettura_esterni as L  # noqa: E402
import prepara_cloud as PC  # noqa: E402
import prepara_spec_ammi as PS  # noqa: E402

OWNER = 'davideferrante11'
SESSION = 'eace4d03'
DATASET = '%s/vcc-validazione-ammi-none-%s-r1' % (OWNER, SESSION)
DATA = Path('C:/Users/ferra/vcc2026-data/processed')
STAGE = DATA / 'validazione_banco_eace4d03_2026-10-09/dataset_ammi_none_r1'
LOCAL_ARMS = {'C-K562': DATA / 'validazione_indipendente_8a8ca58a_2026-10-08/effetti_k562_r1',
              'C-iPSC': DATA / 'validazione_indipendente_8a8ca58a_2026-10-08/effetti_ipsc_r1'}
AUTHORIZED_BYTES = 36281758
KERNEL_SOURCES = ['davideferrante11/vcc-validazione-logo-01a11c35-esm2closure-r1',
                  'davideferrante11/dt-ammi-anchors-01a11c34-r4', 'davidmaisterx/vcc-prod-kolf-pan-genome-mask-r1']
DATASET_SOURCES = [DATASET, 'davideferrante11/vcc-k562-t25-cache-r1']
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
sizes = {}
for p in INPUT.rglob("*"):
    if p.is_file():
        sizes.setdefault(p.stat().st_size, []).append(p)


def find(pin, label):
    for p in sizes.get(pin["bytes"], []):
        if sha(p) == pin["sha256"]:
            return str(p)
    raise SystemExit("input not mounted with the pinned content: " + label)


status = {"folds": {}, "inputs": {}, "python": platform.python_version()}
for fold, spec in P["specs"].items():
    for group in ("arms", "extra"):
        for name, entry in spec[group].items():
            entry["path"] = find(entry, fold + "/" + name)
    for name in ("truth", "published_results"):
        spec[name]["path"] = find(spec[name], fold + "/" + name)
    status["inputs"][fold] = {n: e["path"] for n, e in spec["extra"].items()} | {"truth": spec["truth"]["path"]}
    spec_path = WORK / ("spec_%s.json" % fold)
    spec_path.write_text(json.dumps(spec, indent=1))
    out = WORK / ("ammi_none_%s.json" % fold)
    r = subprocess.run([sys.executable, "-W", "ignore", str(PKG / "lettura_esterni.py"), "--spec", str(spec_path),
                        "--out", str(out), "--bench-dir", str(PKG)], capture_output=True, text=True)
    (WORK / ("log_%s.txt" % fold)).write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
    done = json.loads(out.read_text()) if out.is_file() else {}
    status["folds"][fold] = {"returncode": r.returncode, "parity": (done.get("parity") or {}).get("passed"),
                             "stopped": done.get("stopped")}
import numpy
status.update(numpy=numpy.__version__, seconds=round(time.time() - t0, 1),
              usable=all(f["returncode"] == 0 and f["parity"] for f in status["folds"].values()))
(WORK / "status.json").write_text(json.dumps(status, indent=1))
print(json.dumps(status), flush=True)
import shutil
shutil.rmtree(PKG)
if not status["usable"]:
    raise SystemExit("read not usable: see status.json")
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def kaggle(owner, args, timeout=1800):
    from pipeline_state import CONFIG
    env = {k: v for k, v in os.environ.items()
           if k not in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[owner])
    run = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), *args], env=env, capture_output=True,
                         encoding='utf-8', errors='replace', timeout=timeout)
    return run.returncode, (run.stdout + run.stderr)


def stage():
    downloads = PC.read(HERE / 'ammi_none_download_r2.json')['files']
    STAGE.mkdir(parents=True, exist_ok=False)
    files = {}
    for fold, rec in downloads.items():
        pin = PS.pins(fold)['AN']
        dest = STAGE / ('%s_AN.npz' % fold)
        shutil.copyfile(rec['path'], dest)
        if L.sha(dest) != pin['sha256'] or dest.stat().st_size != pin['bytes']:
            raise SystemExit('staged export differs from the producer receipt: ' + fold)
        files[dest.name] = dict(bytes=dest.stat().st_size, sha256=pin['sha256'], fold=fold, produced_by=pin['source'])
    total = sum(f['bytes'] for f in files.values())
    if total != AUTHORIZED_BYTES or len(files) != 2:
        raise SystemExit('the staged dataset is not the one the owner authorized')
    (STAGE / 'dataset-metadata.json').write_text(json.dumps(dict(
        title=DATASET.split('/')[1], id=DATASET, licenses=[dict(name='other')]), indent=1) + '\n')
    PC.write_new(HERE / 'ammi_none_dataset_r1.json', dict(
        utc=now(), dataset=DATASET, private=True, stage=STAGE.as_posix(), files=files, total_bytes=total,
        authorization='owner in chat, 9 October 2026, 21:42: two AMMI none exports, 36,281,758 bytes, to one private dataset'))
    print(json.dumps(dict(dataset=DATASET, files=files and len(files), total_bytes=total)))


def dataset_create():
    record = PC.read(HERE / 'ammi_none_dataset_r1.json')
    rc, answer = kaggle(OWNER, ['datasets', 'create', '-p', str(Path(record['stage']).resolve())])
    PC.write_new(HERE / 'ammi_none_dataset_create_r1.json', dict(utc=now(), dataset=record['dataset'], returncode=rc,
                                                                 answer=answer[-600:]))
    print(json.dumps(dict(returncode=rc, tail=answer[-160:])))


def dataset_status(out):
    record = PC.read(HERE / 'ammi_none_dataset_r1.json')
    rc, status = kaggle(OWNER, ['datasets', 'status', record['dataset']], 120)
    rc2, files = kaggle(OWNER, ['datasets', 'files', record['dataset'], '--csv', '--page-size', '50'], 120)
    listed = {l.split(',')[0]: l.split(',')[1] for l in files.splitlines()[1:] if l.strip() and ',' in l}
    PC.write_new(out, dict(utc=now(), dataset=record['dataset'], status=status.strip(), files=listed,
                           ready=rc == 0 and rc2 == 0 and status.strip() == 'ready'))
    print(json.dumps(dict(status=status.strip(), files=listed)))


def spec_for(fold):
    p = PS.pins(fold)
    arms = {}
    for arm in PS.ARMS:
        local = LOCAL_ARMS[fold] / (arm + '.npz')
        if L.sha(local) != p['arms'][arm]:
            raise SystemExit('local copy of %s/%s differs from the closure receipt' % (fold, arm))
        arms[arm] = dict(bytes=local.stat().st_size, sha256=p['arms'][arm])
    return {'fold': fold, 'truth_table': p['truth_table'], 'lineage': PS.LINEAGE[fold], 'arms': arms,
            'extra': {'A0': dict(bytes=p['A0']['bytes'], sha256=p['A0']['sha256']),
                      'AN': dict(bytes=p['AN']['bytes'], sha256=p['AN']['sha256'])},
            'pairs': [['AN', 'A0'], ['A0', 'T0'], ['AN', 'T0']],
            'truth': dict(bytes=p['truth']['bytes'], sha256=p['truth']['sha256']),
            'published_results': dict(bytes=p['published_results']['bytes'], sha256=p['published_results']['sha256'])}


def package(revision):
    stage_dir = HERE / ('cloud_' + revision) / 'package'
    stage_dir.mkdir(parents=True, exist_ok=False)
    specs = {fold: spec_for(fold) for fold in ('C-K562', 'C-iPSC')}
    members = {'lettura_esterni.py': (HERE / 'lettura_esterni.py').read_bytes(),
               'metrics.py': (L.FROZEN_BENCH / 'metrics.py').read_bytes(),
               'bench_core.py': (L.FROZEN_BENCH / 'bench_core.py').read_bytes()}
    for name, want in L.PINNED.items():
        if hashlib.sha256(members[name]).hexdigest() != want:
            raise SystemExit(name + ' is not the frozen file')
    # a kernel named like the dataset was refused by the provider (409, cloud_r1/launch.json): distinct name
    slug = '%s/vcc-validazione-lettura-ammi-%s-%s' % (OWNER, SESSION, revision)
    params = dict(kind='external_arm_read_level_A', slug=slug, plan='LETTURA_AMMI_NONE.md', specs=specs,
                  embedded_sha256={k: hashlib.sha256(v).hexdigest() for k, v in members.items()},
                  not_vcc_scores=True, trains_nothing=True)
    members['params.json'] = (json.dumps(params, indent=1) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 9, 0, 0, 0)), members[name], zipfile.ZIP_DEFLATED)
    code = RUN.replace('__ZIP__', base64.b64encode(buffer.getvalue()).decode())
    compile(code, 'run.py', 'exec')
    (stage_dir / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=False,
                dataset_sources=DATASET_SOURCES, kernel_sources=KERNEL_SOURCES, competition_sources=[])
    (stage_dir / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    PC.write_new(stage_dir.parent / 'prepared.json', dict(
        utc=now(), slug=slug, owner=OWNER, stage=stage_dir.relative_to(REPO).as_posix(), code=PC.pin(stage_dir / 'run.py'),
        reader=dict(path='ammi/lettura_esterni.py', sha256=L.sha(HERE / 'lettura_esterni.py')), frozen=L.PINNED,
        folds=list(specs), metadata=meta, compute_started=False))
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()))))


def lancia(revision, preflight_path):
    folder = HERE / ('cloud_' + revision)
    proof, pre = PC.read(folder / 'prepared.json'), PC.read(preflight_path)
    if (datetime.now(timezone.utc) - datetime.fromisoformat(pre['utc'])).total_seconds() > 900:
        raise ValueError('fresh preflight required')
    if pre['active'].get(OWNER, 0) >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full')
    stage_dir = REPO / proof['stage']
    if L.sha(stage_dir / 'run.py') != proof['code']['sha256']:
        raise ValueError('prepared package changed')
    rc, body = kaggle(OWNER, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'], 120)
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=now(), slug=proof['slug'], owner=OWNER, stage=proof['stage'], code_sha256=proof['code']['sha256'],
                   preflight_sha256=L.sha(preflight_path), private=True,
                   authorization='owner in chat, 9 October 2026, 21:42: read the AMMI none exports now on a private CPU '
                                 'kernel of davideferrante11; CPU only, nothing paid',
                   incidents=['E-20261003-001'], guards=['one explicit push, no loop', 'dedup lookup', 'slot preflight',
                                                         'every input found by pinned size and sha256 on the runtime',
                                                         'parity with the published run before any read'],
                   state='intent', accepted=False)
    PC.write_new(folder / 'launch.json', receipt)
    rc, body = kaggle(OWNER, ['kernels', 'push', '-p', str(stage_dir)], 300)
    receipt.update(returncode=rc, answer=body.strip(), state='push_returned',
                   accepted=rc == 0 and 'successfully pushed' in body and 'not valid' not in body)
    if receipt['accepted']:
        rc, status = kaggle(OWNER, ['kernels', 'status', proof['slug']], 120)
        receipt.update(remote_status=status.strip(), remote_status_utc=now())
    (folder / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status', 'answer')}))


def stato(revision, out):
    proof = PC.read(HERE / ('cloud_' + revision) / 'prepared.json')
    rc, status = kaggle(OWNER, ['kernels', 'status', proof['slug']], 120)
    PC.write_new(out, dict(utc=now(), slug=proof['slug'], returncode=rc, status=status.strip()))
    print(status.strip())


def raccogli(revision):
    folder = HERE / ('cloud_' + revision)
    launch = PC.read(folder / 'launch.json')
    rc, status = kaggle(OWNER, ['kernels', 'status', launch['slug']], 120)
    print(status.strip())
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    out = folder / ('completion' if 'COMPLETE' in status else 'failure')
    out.mkdir(exist_ok=False)
    PC.write_new(out / 'provider_status.json', dict(utc=now(), returncode=rc, status=status.strip()))
    rc, answer = kaggle(OWNER, ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern',
                                'ammi_none_.*\\.json|spec_.*\\.json|status.json|log_.*\\.txt|.*\\.log'], 600)
    PC.write_new(out / 'retrieval.json', dict(utc=now(), returncode=rc, answer=answer[-2000:]))


if __name__ == '__main__':
    {'stage': stage, 'dataset-create': dataset_create, 'dataset-status': dataset_status, 'package': package,
     'lancia': lancia, 'stato': stato, 'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
