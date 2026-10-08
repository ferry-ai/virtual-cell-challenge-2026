"""Real cells of the held lineage for the panel targets, for level B (six members with the real scorer).

The six-member benches of 4 October extracted 150 targets per line chosen by a hash rule: on K562 only 6 of
them are panel targets, on H1 15. Level B of contract v1 needs the panel targets of the fold. This builds a
Kaggle CPU kernel that runs the archived `extract_cells.py` of the cell corpus (dataset rcell-gen-r1, unchanged)
on the prepass state of the held line, with a target list that is the panel targets the fold's truth table
carries. No effect is read: the list comes from the consumption receipt of release r1 (which sources vote
on which target), and the cells from the corpus shards already on Kaggle.

    prepara_estrazione.py package k562 <revision>
    prepara_estrazione.py lancia k562 <revision> <preflight.json>
    prepara_estrazione.py stato k562 <revision> <out.json>
    prepara_estrazione.py raccogli k562 <revision>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prepara_banco as B  # noqa: E402

CONSUMO = B.FIT_R1 / 'completion/consumo.json'
LINES = {
    'k562': {'fold': 'C-K562', 'key': 'replogle_k562_gwps|K562', 'truth_source': 'k562', 'owner': 'davidmaisterx',
             'prepass_kernel': 'rcell-prepass-k562-r1', 'datasets': ['rcell-gen-r1', 'rlab-k562-gwps-r3'],
             'cap': 128, 'max_controls': 2048, 'seed': 2026},
    # the pilot corpus holds the KOLF2.1J "strong perturbations" library; its key is resolved on the runtime as the
    # one key of the prepass state whose name contains the substring, and recorded
    'ipsc': {'fold': 'C-iPSC', 'key': None, 'key_contains': 'kolf_strong', 'truth_source': 'kolf_strong',
             'owner': 'davidmaisterx', 'prepass_kernel': 'rcell-prepass-k562-r1',
             'datasets': ['rcell-gen-r1', 'rlab-kolf-strong'], 'cap': 128, 'max_controls': 2048, 'seed': 2026},
}
KERNEL = r'''
import json, pickle, subprocess, sys, time
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
P = json.loads(__PARAMS__)
t0 = time.time()


def mount(slug):
    hits = [p for p in INPUT.glob("**/" + slug) if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


GEN = mount("rcell-gen-r1")
PRE = mount(P["prepass_kernel"]) / "prepass"
with open(PRE / "prepass.pkl", "rb") as fh:
    st = pickle.load(fh)
if P.get("key") is None:
    hits = [k for k in st["key_names"] if P["key_contains"] in k]
    if len(hits) != 1:
        raise SystemExit("keys containing %s: %s" % (P["key_contains"], hits))
    P["key"] = hits[0]
if P["key"] not in st["key_names"]:
    raise SystemExit("the prepass state does not know the key " + P["key"])
known = set(st["symbols"])
targets = [{"key": P["key"], "symbol": s} for s in P["symbols"]]
(OUT / "targets.json").write_text(json.dumps(targets, indent=0))
log = {"mounts": {"gen": str(GEN), "prepass": str(PRE)}, "holdout_group_of_prepass": st.get("holdout_group"),
       "key": P["key"], "keys_of_the_state": len(st["key_names"]),
       "symbols_requested": len(targets), "symbols_unknown_to_the_corpus": sorted(set(P["symbols"]) - known)}
r = subprocess.run([sys.executable, str(GEN / "extract_cells.py"), "--prepass", str(PRE), "--targets",
                    str(OUT / "targets.json"), "--shard-roots", str(INPUT), "--cap", str(P["cap"]),
                    "--max-controls", str(P["max_controls"]), "--seed", str(P["seed"]),
                    "--out", str(OUT / "real_cells.npz")], capture_output=True, text=True)
(OUT / "extract.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
log["extract"] = {"returncode": r.returncode, "seconds": round(time.time() - t0, 1)}
log["ok"] = r.returncode == 0
if log["ok"]:
    log["sidecar"] = json.loads((OUT / "real_cells.json").read_text())
(OUT / "extract_done.json").write_text(json.dumps(log, indent=1))
print(json.dumps({k: log[k] for k in ("ok", "extract", "symbols_unknown_to_the_corpus")}), flush=True)
if not log["ok"]:
    raise SystemExit("extract failed: see extract.log")
'''


def package(line, revision):
    spec = LINES[line]
    stage = HERE / ('celle_%s_%s' % (line, revision)) / 'package'
    stage.mkdir(parents=True, exist_ok=False)
    consumo = B.read(CONSUMO)
    symbols = sorted(t for t, v in consumo['votes_per_target'].items() if spec['truth_source'] in v)
    manifest = B.read(B.MANIFEST)
    fold = next(f for f in manifest['folds_C'] if f['id'] == spec['fold'])
    assert spec['truth_source'] in fold['exclude_tables']
    slug = '%s/vcc-validazione-celle-%s-%s-%s' % (spec['owner'], line, B.SESSION, revision)
    params = dict(key=spec['key'], key_contains=spec.get('key_contains'), symbols=symbols,
                  prepass_kernel=spec['prepass_kernel'], cap=spec['cap'],
                  max_controls=spec['max_controls'], seed=spec['seed'])
    code = KERNEL.replace('__PARAMS__', repr(json.dumps(params)))
    compile(code, 'run.py', 'exec')
    (stage / 'run.py').write_text(code, encoding='utf-8', newline='\n')
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=False,
                dataset_sources=['%s/%s' % (spec['owner'], d) for d in spec['datasets']],
                kernel_sources=['%s/%s' % (spec['owner'], spec['prepass_kernel'])], competition_sources=[])
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    B.write_new(stage.parent / 'prepared.json', dict(
        utc=B.now(), slug=slug, owner=spec['owner'], stage=stage.relative_to(B.REPO).as_posix(),
        code=B.pin(stage / 'run.py'), fold=spec['fold'], symbols=len(symbols), params={k: v for k, v in params.items()
                                                                                         if k != 'symbols'},
        symbols_from=dict(B.pin(CONSUMO), path=CONSUMO.relative_to(B.REPO).as_posix(),
                          rule='panel targets on which the source %s votes' % spec['truth_source']),
        extractor='extract_cells.py of dataset rcell-gen-r1, unchanged (reports/modelli/rete_cellulare_2026-10-03/)',
        metadata=meta, reads_no_effect=True, compute_started=False))
    print(json.dumps(dict(slug=slug, symbols=len(symbols), datasets=meta['dataset_sources'])))


def lancia(line, revision, preflight_path):
    here = HERE / ('celle_%s_%s' % (line, revision))
    proof = B.read(here / 'prepared.json')
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
                                 'only, nothing paid, nothing uploaded besides the code',
                   incidents=['E-20261003-001'], guards=['one explicit push, no loop', 'dedup lookup', 'slot preflight'],
                   state='intent', accepted=False)
    B.write_new(here / 'launch.json', receipt)
    rc, body = B.call(owner, ['kernels', 'push', '-p', str(stage)])
    receipt.update(returncode=rc, answer=body, state='push_returned',
                   accepted=rc == 0 and 'successfully pushed' in body and 'not valid' not in body)
    if receipt['accepted']:
        rc, status = B.call(owner, ['kernels', 'status', proof['slug']])
        receipt.update(remote_status=status, remote_status_utc=B.now())
    (here / 'launch.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status', 'answer')}))


def stato(line, revision, out):
    proof = B.read(HERE / ('celle_%s_%s' % (line, revision)) / 'prepared.json')
    rc, status = B.call(proof['owner'], ['kernels', 'status', proof['slug']])
    B.write_new(out, dict(utc=B.now(), slug=proof['slug'], returncode=rc, status=status))
    print(status)


def raccogli(line, revision):
    here = HERE / ('celle_%s_%s' % (line, revision))
    launch = B.read(here / 'launch.json')
    rc, status = B.call(launch['owner'], ['kernels', 'status', launch['slug']])
    print(status)
    if rc or not any(s in status for s in ('COMPLETE', 'ERROR', 'CANCEL')):
        return
    out = here / ('completion' if 'COMPLETE' in status else 'failure')
    out.mkdir(exist_ok=False)
    B.write_new(out / 'provider_status.json', dict(utc=B.now(), returncode=rc, status=status))
    rc, answer = B.call(launch['owner'], ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern',
                                          'extract_done.json|real_cells.json|targets.json|.*\\.log'])
    B.write_new(out / 'retrieval.json', dict(utc=B.now(), returncode=rc, answer=answer[-2000:]))


if __name__ == '__main__':
    {'package': package, 'lancia': lancia, 'stato': stato, 'raccogli': raccogli}[sys.argv[1]](*sys.argv[2:])
