"""Six-member bench of the ESM2 fill arms on one fold (LIVELLO_B_ESM2.md): bench_v2 unchanged, real cells of 8 October.

    livello_b_esm2.py stage                          stage the six arm files as one dataset folder (no upload)
    livello_b_esm2.py dataset-create                 upload it as ONE private dataset of the account holding the cells
    livello_b_esm2.py dataset-status <out.json>
    livello_b_esm2.py package <k562|ipsc>            build the bench kernel of one fold
    livello_b_esm2.py lancia <k562|ipsc> <preflight.json>
    livello_b_esm2.py stato <k562|ipsc> <out.json>
    livello_b_esm2.py raccogli <k562|ipsc>

The kernel is the one of `prepara_livello_b.py` of the frozen bench with three declared changes, applied to its
text and checked one by one: a second mounted dataset for the fill arms, their sha256 verified with the others,
and the path of an arm looked up by name. T0 is read from the fold's dataset of 8 October, already on the
account. Authorization: owner in chat, 9 October 2026, 21:42 (AUTORIZZAZIONI_r1.json).
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = HERE.parents[3]
FROZEN = REPO / 'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco'
sys.path.insert(0, str(FROZEN))
import prepara_banco as B  # noqa: E402
import prepara_estrazione as E  # noqa: E402
import prepara_livello_b as PB  # noqa: E402

SESSION = 'eace4d03'
REVISION = 'e1'
OWNER = 'davidmaisterx'
DATASET = '%s/vcc-validazione-bracci-esm2-%s-r1' % (OWNER, SESSION)
STAGE = Path('C:/Users/ferra/vcc2026-data/processed/validazione_banco_eace4d03_2026-10-09/dataset_bracci_esm2_r1')
FILL_ARMS = ('E2f', 'E2gen', 'E2swap')
FOLD = {'k562': 'C-K562', 'ipsc': 'C-iPSC'}
STEPS = [{'name': 'control', 'targets': 'all', 'arms': ['T0', 'T0shuffle'], 'pairs': ['T0:T0shuffle'], 'gen_seeds': 1},
         {'name': 'full', 'targets': 'all', 'arms': ['T0', *FILL_ARMS],
          'pairs': ['E2f:T0', 'E2gen:T0', 'E2swap:T0', 'E2f:E2swap', 'E2f:E2gen'], 'gen_seeds': 5}]
# the three changes to the frozen kernel text: (old, new), each old fragment must occur exactly once
KERNEL_CHANGES = [
    ('REAL, EFF = mount(P["real_kernel"]), mount(P["effects_dataset"])\n',
     'REAL, EFF = mount(P["real_kernel"]), mount(P["effects_dataset"])\n'
     'EXTRA = mount(P["extra_dataset"])\n'
     'ARM_PATH = {a: EFF / (a + ".npz") for a in P["arms_sha256"]}\n'
     'ARM_PATH.update({a: EXTRA / f["file"] for a, f in P["extra_arms"].items()})\n'),
    ('        (EFF / (a + ".npz"), d) for a, d in P["arms_sha256"].items()]:\n',
     '        (EFF / (a + ".npz"), d) for a, d in P["arms_sha256"].items()] + [\n'
     '        (EXTRA / f["file"], f["sha256"]) for f in P["extra_arms"].values()]:\n'),
    ('        out += ["--arm", "%s=%s" % (n, OUT / "T0shuffle.npz" if n == "T0shuffle" else EFF / (n + ".npz"))]\n',
     '        out += ["--arm", "%s=%s" % (n, OUT / "T0shuffle.npz" if n == "T0shuffle" else ARM_PATH[n])]\n'),
]


def here(line):
    return HERE / ('livello_b_%s_%s' % (line, REVISION))


def arms_manifest(line):
    return B.read(ROOT / 'esm2' / ('bracci_%s_r1.json' % FOLD[line]))


def kaggle(args, timeout=1800):
    from pipeline_state import CONFIG
    env = {k: v for k, v in os.environ.items()
           if k not in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[OWNER])
    run = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), *args], env=env, capture_output=True,
                         encoding='utf-8', errors='replace', timeout=timeout)
    return run.returncode, (run.stdout + run.stderr)


def stage():
    STAGE.mkdir(parents=True, exist_ok=False)
    files = {}
    for line, fold in FOLD.items():
        manifest = arms_manifest(line)
        for arm in FILL_ARMS:
            src = Path(manifest['files'][arm]['path'])
            dest = STAGE / ('%s_%s.npz' % (fold, arm))
            shutil.copyfile(src, dest)
            if B.sha(dest) != manifest['files'][arm]['sha256']:
                raise SystemExit('staged copy differs: ' + dest.name)
            files[dest.name] = dict(B.pin(dest), fold=fold, arm=arm)
    (STAGE / 'dataset-metadata.json').write_text(json.dumps(dict(
        title=DATASET.split('/')[1], id=DATASET, licenses=[dict(name='other')]), indent=1) + '\n')
    B.write_new(HERE / 'bracci_esm2_dataset_r1.json', dict(
        utc=B.now(), dataset=DATASET, private=True, stage=STAGE.as_posix(), files=files,
        total_bytes=sum(f['bytes'] for f in files.values()),
        what='three fill arms per fold of the ESM2 fallback, stage-100 format, one mask and one scale; not production',
        authorization='owner in chat, 9 October 2026: six prediction files, 117,859,641 bytes, one new private dataset'))
    print(json.dumps(dict(dataset=DATASET, files=len(files), total_bytes=sum(f['bytes'] for f in files.values()))))


def dataset_create():
    record = B.read(HERE / 'bracci_esm2_dataset_r1.json')
    if record['total_bytes'] != 117859641 or len(record['files']) != 6:
        raise SystemExit('the staged dataset is not the one the owner authorized')
    rc, answer = kaggle(['datasets', 'create', '-p', str(Path(record['stage']).resolve())])
    B.write_new(HERE / 'bracci_esm2_dataset_create_r1.json', dict(
        utc=B.now(), dataset=record['dataset'], returncode=rc, answer=answer[-800:],
        note='confirm with dataset-status: the progress bar is not text'))
    print(json.dumps(dict(returncode=rc, tail=answer[-200:])))


def dataset_status(out):
    record = B.read(HERE / 'bracci_esm2_dataset_r1.json')
    rc, status = kaggle(['datasets', 'status', record['dataset']], 120)
    rc2, files = kaggle(['datasets', 'files', record['dataset'], '--csv', '--page-size', '50'], 120)
    listed = {l.split(',')[0]: l.split(',')[1] for l in files.splitlines()[1:] if l.strip() and ',' in l}
    B.write_new(out, dict(utc=B.now(), dataset=record['dataset'], status=status.strip(), files=listed,
                          ready=rc == 0 and rc2 == 0 and status.strip() == 'ready'
                          and sorted(k for k in listed if k.endswith('.npz')) == sorted(record['files'])))
    print(json.dumps(dict(status=status.strip(), files=listed)))


def package(line):
    folder = here(line)
    folder.mkdir(exist_ok=False)
    record = B.read(HERE / 'bracci_esm2_dataset_r1.json')
    old = B.read(FROZEN / ('livello_b_%s_r1' % line) / 'effetti.json')           # the fold's arms of 8 October
    extraction = FROZEN / ('celle_%s_r1' % line)
    done = B.read(extraction / 'completion/extract_done.json')
    ext_launch = B.read(extraction / 'launch.json')
    manifest = arms_manifest(line)
    if old['files']['T0']['sha256'] != manifest['reference_T0']['sha256']:
        raise SystemExit('the fill arms were built on another T0 than the one on the bench account')
    members = {'bench_v2.py': PB.BENCH.read_bytes()}
    for name in PB.SNAPSHOT_MODULES:
        members['src/vcc2026/' + name] = (REPO / 'src/vcc2026' / name).read_bytes()
    for name in ('config.yaml', 'trials.yaml'):
        members['configs/' + name] = (REPO / 'configs' / name).read_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0)), members[name], zipfile.ZIP_DEFLATED)
    snapshot = buffer.getvalue()
    previous = B.read(FROZEN / ('livello_b_%s_r1' % line) / 'prepared.json')['params']
    same_code = (previous['snapshot_sha256'] == hashlib.sha256(snapshot).hexdigest()
                 and previous['bench_sha256'] == hashlib.sha256(members['bench_v2.py']).hexdigest())
    fold = FOLD[line]
    extra = {arm: dict(file='%s_%s.npz' % (fold, arm), sha256=record['files']['%s_%s.npz' % (fold, arm)]['sha256'])
             for arm in FILL_ARMS}
    slug = '%s/vcc-validazione-banco-%s-%s-%s' % (OWNER, line, SESSION, REVISION)
    params = dict(scorer_version=PB.SCORER, snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),
                  real_kernel=ext_launch['slug'].split('/')[1], effects_dataset=old['dataset'].split('/')[1],
                  extra_dataset=record['dataset'].split('/')[1], real_sha256=done['sidecar']['sha256'],
                  real_targets_sha256=B.sha(extraction / 'completion/targets.json'),
                  arms_sha256={'T0': old['files']['T0']['sha256']}, extra_arms=extra,
                  bench_sha256=hashlib.sha256(members['bench_v2.py']).hexdigest(), changed_targets=[],
                  shuffle_seed=20261008, n_pred=400, gen_seeds=5, bench_seed=2026, fold=fold, steps=STEPS)
    code = PB.KERNEL
    for old_text, new_text in KERNEL_CHANGES:
        if code.count(old_text) != 1:
            raise SystemExit('the frozen kernel text changed: ' + old_text[:50])
        code = code.replace(old_text, new_text)
    code = code.replace('__PARAMS__', repr(json.dumps(params))).replace('__SNAPSHOT__', base64.b64encode(snapshot).decode())
    compile(code, 'run.py', 'exec')
    stage_dir = folder / 'package'
    stage_dir.mkdir()
    (stage_dir / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=True,
                dataset_sources=[old['dataset'], record['dataset']], kernel_sources=[ext_launch['slug']],
                competition_sources=[])
    (stage_dir / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    B.write_new(folder / 'prepared.json', dict(
        utc=B.now(), slug=slug, owner=OWNER, stage=stage_dir.relative_to(REPO).as_posix(), code=B.pin(stage_dir / 'run.py'),
        params=params, plan='LIVELLO_B_ESM2.md', kernel_changes=len(KERNEL_CHANGES),
        same_bench_and_snapshot_as_8_october=same_code, frozen_kernel_sha256=hashlib.sha256(PB.KERNEL.encode()).hexdigest(),
        bench=dict(B.pin(PB.BENCH), path=PB.BENCH.relative_to(REPO).as_posix()), metadata=meta, compute_started=False))
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()), same_bench_and_snapshot_as_8_october=same_code,
                          arms=['T0', *sorted(extra)])))


def lancia(line, preflight_path):
    folder = here(line)
    proof = B.read(folder / 'prepared.json')
    pre = B.read(preflight_path)
    if (B.datetime.now(B.timezone.utc) - B.datetime.fromisoformat(pre['utc'])).total_seconds() > 900:
        raise ValueError('fresh preflight required')
    if pre['active'].get(OWNER, 0) >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full')
    stage_dir = REPO / proof['stage']
    if B.sha(stage_dir / 'run.py') != proof['code']['sha256']:
        raise ValueError('prepared package changed')
    rc, body = kaggle(['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'], 120)
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=B.now(), slug=proof['slug'], owner=OWNER, stage=proof['stage'], code_sha256=proof['code']['sha256'],
                   preflight_sha256=B.sha(preflight_path), private=True,
                   authorization='owner in chat, 9 October 2026, 21:42: VALIDAZIONE runs the four-arm six-member bench on '
                                 'davidmaisterx, CPU only, nothing paid, no GPU',
                   incidents=['E-20261003-001'], guards=['one explicit push, no loop', 'dedup lookup', 'slot preflight',
                                                         'every input verified by sha256 on the runtime'],
                   state='intent', accepted=False)
    B.write_new(folder / 'launch.json', receipt)
    rc, body = kaggle(['kernels', 'push', '-p', str(stage_dir)], 300)
    receipt.update(returncode=rc, answer=body.strip(), state='push_returned',
                   accepted=rc == 0 and 'successfully pushed' in body and 'not valid' not in body)
    if receipt['accepted']:
        rc, status = kaggle(['kernels', 'status', proof['slug']], 120)
        receipt.update(remote_status=status.strip(), remote_status_utc=B.now())
    (folder / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status', 'answer')}))


def stato(line, out):
    proof = B.read(here(line) / 'prepared.json')
    rc, status = kaggle(['kernels', 'status', proof['slug']], 120)
    B.write_new(out, dict(utc=B.now(), slug=proof['slug'], returncode=rc, status=status.strip()))
    print(status.strip())


def raccogli(line):
    folder = here(line)
    launch = B.read(folder / 'launch.json')
    rc, status = kaggle(['kernels', 'status', launch['slug']], 120)
    print(status.strip())
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    out = folder / ('completion' if 'COMPLETE' in status else 'failure')
    out.mkdir(exist_ok=False)
    B.write_new(out / 'provider_status.json', dict(utc=B.now(), returncode=rc, status=status.strip()))
    pattern = ('bench_done.json|env.json|inputs_verified.json|targets_.*json|.*paired.json|.*run.json|.*bench.json|'
               '.*scaled_local.csv|.*\\.log')
    rc, answer = kaggle(['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern', pattern], 900)
    B.write_new(out / 'retrieval.json', dict(utc=B.now(), returncode=rc, answer=answer[-2000:]))


if __name__ == '__main__':
    {'stage': stage, 'dataset-create': dataset_create, 'dataset-status': dataset_status, 'package': package,
     'lancia': lancia, 'stato': stato, 'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
