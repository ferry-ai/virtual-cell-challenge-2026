"""Level B on one fold: six members with the real scorer, bench_v2 unchanged, on the extracted panel cells.

    prepara_livello_b.py effetti <line> <revision>            fetch the fold's arms from the level-A kernel, stage a dataset
    prepara_livello_b.py dataset-create <line> <revision>     upload it as one private dataset of the bench's account
    prepara_livello_b.py dataset-status <line> <revision> <out.json>
    prepara_livello_b.py package <line> <revision>            build the bench kernel (needs the collected extraction)
    prepara_livello_b.py lancia <line> <revision> <preflight.json>
    prepara_livello_b.py stato <line> <revision> <out.json>
    prepara_livello_b.py raccogli <line> <revision>

The arms are the files level A wrote for the fold (stage 100 on a cache without the held lineage). They are
copied to the account that holds the real cells because a private kernel output is not mounted across accounts.
The kernel verifies every file by sha256 before any generation or scoring.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prepara_banco as B  # noqa: E402
import prepara_estrazione as E  # noqa: E402

DATA = Path('C:/Users/ferra/vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08')
BENCH = B.REPO / 'reports/generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py'
# A plan is chosen by the revision name: which level-A run wrote the arms, which arms, which bench runs.
# Revisions not named here use the contract's plan (LIVELLO_B.md).
CONTRACT_PLAN = {
    'level_a': 'r1', 'arms': ('T0', 'T1', 'R1', 'P4'),
    'steps': [{'name': 'control', 'targets': 'all', 'arms': ['T0', 'T0shuffle'], 'pairs': ['T0:T0shuffle'],
               'gen_seeds': 1},
              {'name': 'changed', 'targets': 'changed', 'arms': ['T0', 'T1', 'R1'],
               'pairs': ['T1:T0', 'R1:T0', 'R1:T1'], 'gen_seeds': 5},
              {'name': 'full', 'targets': 'all', 'arms': ['T0', 'T1', 'P4'], 'pairs': ['T1:T0', 'T0:P4'],
               'gen_seeds': 5}]}
PLANS = {
    # exploratory (ESPLORATIVO_SENZA_KOLF.md): t36 without the KOLF tables, and with KOLF voting once
    'x1': {'level_a': 'r3', 'arms': ('T0', 'P4h', 'P4kh'),
           'steps': [{'name': 'full', 'targets': 'all', 'arms': ['T0', 'P4h', 'P4kh'],
                      'pairs': ['P4h:T0', 'P4kh:T0', 'P4h:P4kh'], 'gen_seeds': 5}]},
}


def plan_of(revision):
    return PLANS.get(revision, CONTRACT_PLAN)


SCORER = '0.16.0'
SNAPSHOT_MODULES = ('__init__.py', 'bench.py', 'config.py', 'de_tools.py', 'inference.py', 'sampling.py',
                    'generator.py', 'genes.py', 'manifest.py', 'resources.py', 'trials.py')
KERNEL = r'''
import base64, hashlib, io, json, os, subprocess, sys, time, zipfile
from pathlib import Path
P = json.loads(__PARAMS__)
SNAPSHOT = "__SNAPSHOT__"
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
t0 = time.time()
log = {"steps": {}}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mount(slug):
    hits = [p for p in INPUT.glob("**/" + slug) if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


raw = base64.b64decode(SNAPSHOT)
if hashlib.sha256(raw).hexdigest() != P["snapshot_sha256"]:
    raise SystemExit("the code snapshot inside run.py is not the launcher's")
repo = OUT / "repo"
zipfile.ZipFile(io.BytesIO(raw)).extractall(repo)
r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "cell-eval2==" + P["scorer_version"]],
                   capture_output=True, text=True)
(OUT / "pip.log").write_text(r.stdout[-5000:] + "\n--- stderr ---\n" + r.stderr[-5000:])
import importlib.metadata as md
if md.version("cell-eval2") != P["scorer_version"]:
    raise SystemExit("cell-eval2 %s in the runtime, %s required" % (md.version("cell-eval2"), P["scorer_version"]))
versions = {}
for pkg in ("cell-eval2", "numpy", "scipy", "pandas", "polars", "anndata", "h5py"):
    try:
        versions[pkg] = md.version(pkg)
    except Exception:
        versions[pkg] = None
(OUT / "env.json").write_text(json.dumps({"python": sys.version.split()[0], "cpus": os.cpu_count(),
                                          "versions": versions}, indent=1))
REAL, EFF = mount(P["real_kernel"]), mount(P["effects_dataset"])
real, real_targets = REAL / "real_cells.npz", REAL / "targets.json"
checked = {}
for path, want in [(real, P["real_sha256"]), (real_targets, P["real_targets_sha256"])] + [
        (EFF / (a + ".npz"), d) for a, d in P["arms_sha256"].items()]:
    got = sha(path)
    checked[path.name] = got
    if got != want:
        raise SystemExit(f"input changed: {path.name} {got} != {want}")
if sha(repo / "bench_v2.py") != P["bench_sha256"]:
    raise SystemExit("bench_v2.py is not the archived file")
(OUT / "inputs_verified.json").write_text(json.dumps(checked, indent=1))

import numpy as np
with np.load(real, allow_pickle=False) as z:
    labels = z["labels"].astype(str)
symbols = [t["symbol"] for t in json.loads(real_targets.read_text())]
present = [s for s in symbols if (labels == s).sum() >= 4]
changed = [s for s in P["changed_targets"] if s in present]
(OUT / "targets_all.json").write_text(json.dumps([{"symbol": s} for s in present]))
(OUT / "targets_changed.json").write_text(json.dumps([{"symbol": s} for s in changed]))
# control arm: the reference with its rows exchanged among the bench targets (no fixed point)
with np.load(EFF / "T0.npz", allow_pickle=False) as z:
    targets, genes, lfc, observed = z["targets"].astype(str), z["genes"], z["lfc"], z["observed"]
pos = {t: i for i, t in enumerate(targets)}
rows = np.array([pos[s] for s in present])
rng = np.random.default_rng([P["shuffle_seed"], rows.size])
while True:
    perm = rng.permutation(rows.size)
    if not (perm == np.arange(rows.size)).any():
        break
np.savez_compressed(OUT / "T0shuffle.npz", targets=np.array(present), genes=genes, lfc=lfc[rows][perm],
                    observed=observed[rows][perm])
log["targets"] = {"all": len(present), "changed": changed, "requested": len(symbols)}
env = {**os.environ, "PYTHONPATH": str(repo / "src"), "VCC2026_DATA_ROOT": str(OUT / "data_root"),
       "PYTHONIOENCODING": "utf-8"}
(OUT / "data_root").mkdir()
common = ["--real", real, "--n-pred", P["n_pred"], "--emission", "t28", "--seed", P["bench_seed"]]


def arm(*names):
    out = []
    for n in names:
        out += ["--arm", "%s=%s" % (n, OUT / "T0shuffle.npz" if n == "T0shuffle" else EFF / (n + ".npz"))]
    return out


steps, subset = {}, {}
for s in P["steps"]:
    args = [*common, "--targets", OUT / ("targets_%s.json" % s["targets"]), *arm(*s["arms"])]
    for pair in s["pairs"]:
        args += ["--pair", pair]
    steps[s["name"]] = [*args, "--gen-seeds", s["gen_seeds"], "--out", OUT / ("bench_" + s["name"])]
    subset[s["name"]] = s["targets"]
ok = True
for name, args in steps.items():
    if subset[name] == "changed" and len(changed) < 4:
        log["steps"][name] = {"skipped": "fewer than 4 changed targets with real cells"}
        continue
    started = time.time()
    r = subprocess.run([sys.executable, str(repo / "bench_v2.py"), *map(str, args)], capture_output=True, text=True,
                       env=env)
    (OUT / (name + ".log")).write_text(r.stdout[-20000:] + "\n--- stderr ---\n" + r.stderr[-20000:])
    log["steps"][name] = {"returncode": r.returncode, "seconds": round(time.time() - started, 1)}
    print(json.dumps({name: log["steps"][name]}), flush=True)
    (OUT / "bench_done.json").write_text(json.dumps({**log, "ok": False, "partial": True}, indent=1))
    ok = ok and r.returncode == 0
log["ok"] = ok
log["seconds"] = round(time.time() - t0, 1)
(OUT / "bench_done.json").write_text(json.dumps(log, indent=1))
import shutil
shutil.rmtree(repo, ignore_errors=True)
if not ok:
    raise SystemExit("a bench step failed: see the logs")
'''


def folder(line, revision):
    return HERE / ('livello_b_%s_%s' % (line, revision))


def effetti(line, revision):
    """Fetch the fold's arms from the level-A kernel into the data root and stage the dataset folder."""
    spec = E.LINES[line]
    here = folder(line, revision)
    here.mkdir(exist_ok=False)
    plan = plan_of(revision)
    launch = B.read(HERE / plan['level_a'] / 'launch.json')
    consumption = {(c['label'], c['context']): c
                   for c in B.read(HERE / plan['level_a'] / 'completion/consumption.json')}
    stage = DATA / ('effetti_%s_%s' % (line, revision))
    stage.mkdir(parents=True, exist_ok=False)
    pattern = '|'.join('effects/%s__%s.npz' % (a, spec['fold']) for a in plan['arms'])
    rc, answer = B.call(B.OWNER, ['kernels', 'output', launch['slug'], '-p', str(stage), '--file-pattern', pattern])
    files = {}
    for a in plan['arms']:
        got = next(stage.rglob('%s__%s.npz' % (a, spec['fold'])))
        dest = stage / (a + '.npz')
        got.rename(dest)
        want = consumption[(a, spec['fold'])]['effects_sha256']
        assert B.sha(dest) == want, 'effects of %s differ from the level-A receipt' % a
        files[a] = dict(B.pin(dest), level_a_sources=consumption[(a, spec['fold'])]['sources_linked'])
    for leftover in sorted(stage.rglob('*'), reverse=True):
        if leftover.is_dir() and not any(leftover.iterdir()):
            leftover.rmdir()
        elif leftover.is_file() and leftover.suffix == '.log' and leftover.stat().st_size == 0:
            leftover.unlink()            # the empty log the CLI writes next to a kernel output
    dataset = '%s/vcc-validazione-effetti-%s-%s-%s' % (spec['owner'], line, B.SESSION, revision)
    (stage / 'dataset-metadata.json').write_text(json.dumps(dict(
        title=dataset.split('/')[1], id=dataset, licenses=[dict(name='other')]), indent=1) + '\n')
    (stage / 'README.json').write_text(json.dumps(dict(
        what='fold effects of the independent validation, contract v1: stage 100 on a cache without the held lineage',
        fold=spec['fold'], level_a_kernel=launch['slug'], files=files, not_production=True), indent=1) + '\n')
    B.write_new(here / 'effetti.json', dict(utc=B.now(), dataset=dataset, private=True, stage=stage.as_posix(),
                                            fold=spec['fold'], level_a_kernel=launch['slug'],
                                            level_a_run=plan['level_a'], files=files,
                                            retrieval=dict(returncode=rc, answer=answer[-600:])))
    print(json.dumps(dict(dataset=dataset, files={a: f['bytes'] for a, f in files.items()})))


def dataset_create(line, revision):
    spec = E.LINES[line]
    here = folder(line, revision)
    record = B.read(here / 'effetti.json')
    import os
    from pipeline_state import CONFIG
    env = {k: v for k, v in os.environ.items()
           if k not in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[spec['owner']])
    run = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), 'datasets', 'create', '-p',
                          str(Path(record['stage']).resolve())], env=env, capture_output=True, encoding='utf-8',
                         errors='replace', timeout=1800)
    B.write_new(here / 'dataset_create.json', dict(utc=B.now(), dataset=record['dataset'], returncode=run.returncode,
                                                   answer=(run.stdout + run.stderr)[-800:],
                                                   note='confirm with dataset-status: the progress bar is not text'))
    print(json.dumps(dict(returncode=run.returncode, tail=(run.stdout + run.stderr)[-200:])))


def dataset_status(line, revision, out):
    spec = E.LINES[line]
    record = B.read(folder(line, revision) / 'effetti.json')
    rc, status = B.call(spec['owner'], ['datasets', 'status', record['dataset']])
    rc2, files = B.call(spec['owner'], ['datasets', 'files', record['dataset'], '--csv', '--page-size', '50'])
    listed = {l.split(',')[0]: l.split(',')[1] for l in files.splitlines()[1:] if l.strip()}
    B.write_new(out, dict(utc=B.now(), dataset=record['dataset'], status=status, files=listed,
                          ready=rc == 0 and rc2 == 0 and status.strip() == 'ready'))
    print(json.dumps(dict(status=status, files=listed)))


def package(line, revision):
    spec = E.LINES[line]
    here = folder(line, revision)
    record = B.read(here / 'effetti.json')
    extraction = HERE / ('celle_%s_r1' % line)
    done = B.read(extraction / 'completion/extract_done.json')
    assert done['ok'], 'the extraction did not complete'
    ext_launch = B.read(extraction / 'launch.json')
    consumo = B.read(E.CONSUMO)
    members = {'bench_v2.py': BENCH.read_bytes()}
    for name in SNAPSHOT_MODULES:
        members['src/vcc2026/' + name] = (B.REPO / 'src/vcc2026' / name).read_bytes()
    for name in ('config.yaml', 'trials.yaml'):
        members['configs/' + name] = (B.REPO / 'configs' / name).read_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(members):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0)), members[name], zipfile.ZIP_DEFLATED)
    snapshot = buffer.getvalue()
    slug = '%s/vcc-validazione-banco-%s-%s-%s' % (spec['owner'], line, B.SESSION, revision)
    params = dict(scorer_version=SCORER, snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),
                  real_kernel=ext_launch['slug'].split('/')[1], effects_dataset=record['dataset'].split('/')[1],
                  real_sha256=done['sidecar']['sha256'],
                  real_targets_sha256=B.sha(extraction / 'completion/targets.json'),
                  arms_sha256={a: f['sha256'] for a, f in record['files'].items()},
                  bench_sha256=hashlib.sha256(members['bench_v2.py']).hexdigest(),
                  changed_targets=sorted(consumo['targets_with_added_votes']), shuffle_seed=20261008,
                  n_pred=400, gen_seeds=5, bench_seed=2026, fold=spec['fold'], steps=plan_of(revision)['steps'])
    code = KERNEL.replace('__PARAMS__', repr(json.dumps(params))).replace('__SNAPSHOT__',
                                                                          base64.b64encode(snapshot).decode())
    compile(code, 'run.py', 'exec')
    stage = here / 'package'
    stage.mkdir(exist_ok=False)
    (stage / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=True,
                dataset_sources=[record['dataset']], kernel_sources=[ext_launch['slug']], competition_sources=[])
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    B.write_new(here / 'prepared.json', dict(
        utc=B.now(), slug=slug, owner=spec['owner'], stage=stage.relative_to(B.REPO).as_posix(),
        code=B.pin(stage / 'run.py'), params=params, snapshot_members=sorted(members),
        bench=dict(B.pin(BENCH), path=BENCH.relative_to(B.REPO).as_posix()), metadata=meta, compute_started=False))
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()), arms=sorted(params['arms_sha256']))))


def lancia(line, revision, preflight_path):
    E_here = folder(line, revision)
    proof = B.read(E_here / 'prepared.json')
    owner = proof['owner']
    pre = B.read(preflight_path)
    if (B.datetime.now(B.timezone.utc) - B.datetime.fromisoformat(pre['utc'])).total_seconds() > 900:
        raise ValueError('fresh preflight required')
    if pre['active'].get(owner, 0) >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full')
    stage = B.REPO / proof['stage']
    if B.sha(stage / 'run.py') != proof['code']['sha256']:
        raise ValueError('prepared package changed')
    rc, body = B.call(owner, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'])
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=B.now(), slug=proof['slug'], owner=owner, stage=proof['stage'],
                   code_sha256=proof['code']['sha256'], preflight_sha256=B.sha(preflight_path), private=True,
                   authorization='standing owner authorization for Colab and Kaggle compute (27 September 2026); CPU '
                                 'only, nothing paid',
                   incidents=['E-20261003-001'], guards=['one explicit push, no loop', 'dedup lookup', 'slot preflight',
                                                         'every input verified by sha256 on the runtime'],
                   state='intent', accepted=False)
    B.write_new(E_here / 'launch.json', receipt)
    rc, body = B.call(owner, ['kernels', 'push', '-p', str(stage)])
    receipt.update(returncode=rc, answer=body, state='push_returned',
                   accepted=rc == 0 and 'successfully pushed' in body and 'not valid' not in body)
    if receipt['accepted']:
        rc, status = B.call(owner, ['kernels', 'status', proof['slug']])
        receipt.update(remote_status=status, remote_status_utc=B.now())
    (E_here / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status', 'answer')}))


def stato(line, revision, out):
    proof = B.read(folder(line, revision) / 'prepared.json')
    rc, status = B.call(proof['owner'], ['kernels', 'status', proof['slug']])
    B.write_new(out, dict(utc=B.now(), slug=proof['slug'], returncode=rc, status=status))
    print(status)


def raccogli(line, revision):
    here = folder(line, revision)
    launch = B.read(here / 'launch.json')
    rc, status = B.call(launch['owner'], ['kernels', 'status', launch['slug']])
    print(status)
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    out = here / ('completion' if 'COMPLETE' in status else 'failure')
    out.mkdir(exist_ok=False)
    B.write_new(out / 'provider_status.json', dict(utc=B.now(), returncode=rc, status=status))
    pattern = ('bench_done.json|env.json|inputs_verified.json|targets_.*json|.*paired.json|.*run.json|.*bench.json|'
               '.*scaled_local.csv|.*\\.log')
    rc, answer = B.call(launch['owner'], ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern',
                                          pattern])
    B.write_new(out / 'retrieval.json', dict(utc=B.now(), returncode=rc, answer=answer[-2000:]))


if __name__ == '__main__':
    {'effetti': effetti, 'dataset-create': dataset_create, 'dataset-status': dataset_status, 'package': package,
     'lancia': lancia, 'stato': stato, 'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
