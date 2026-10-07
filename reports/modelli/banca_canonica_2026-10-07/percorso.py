"""Single entry of the reusable path: verified bank -> source effects -> frozen release -> fit.

    percorso.py piano <out.json>            metadata plan of every derivation, from verified rows
    percorso.py preflight <out.json>        slots and state of the three Kaggle accounts
    percorso.py prepara <fonte>             build the cloud package of one derivation
    percorso.py lancia <fonte> <preflight>  push it once (ledger, dedup, slot check)
    percorso.py raccogli <fonte>            fetch its small receipts and verify the saved code
    percorso.py righe|ammissione|fit|riuso|registro ...   the other steps (README.md, section 2)

Nothing here re-ingests raw data or downloads a matrix. Every output is written once
(exclusive create); a rerun needs a new revision, never an overwrite.
"""
import ast
import base64
import csv
import hashlib
import io
import json
import os
import sys
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REUSE = REPO / 'reports/modelli/percorso_riusabile_2026-10-05'
DATA = Path(os.environ.get('VCC2026_DATA_ROOT', 'C:/Users/ferra/vcc2026-data'))
EXPECTED = REPO / 'reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json'
EXPECTED_SHA = '304e8a660d7f69952c62c2e6ccf3a990da48647a186e179db4584941b4b21a30'
AXIS_SHA = '25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201'
PANEL_SHA = 'c9c4c9a69f76afd4507e9a7619fe9925c19ff34e5878c7854493683b23bea5ca'
RECIPE = dict(phi=.2, min_control_frac=1e-6, min_cells=10., pseudo=.5, pseudo_scale='constant', min_expected=1.)
ROWS = HERE / 'rows_r1'  # committed manifest (state.json) of the verified rows tables
ROWS_DATA = DATA / 'processed/banca_canonica_2026-10-07'  # the tables themselves, outside the repository
REVISION = os.environ.get('VCC_REV', 'r1')
sys.path.insert(0, str(REUSE))
from pipeline_state import CONFIG  # noqa: E402
from preflight_slots_fast_v1 import call  # noqa: E402


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


def expected_units():
    assert sha(EXPECTED) == EXPECTED_SHA, 'frozen coverage changed'
    return json.loads(EXPECTED.read_text(encoding='utf-8'))['expected_storage_units']


def specs():
    return json.loads((HERE / 'derivazioni.json').read_text(encoding='utf-8'))


def panel():
    path = DATA / 'raw/controls/pert_counts.csv'
    targets = [r[0] for r in csv.reader(path.open(encoding='utf-8'))][1:]
    assert hashlib.sha256('\n'.join(targets).encode()).hexdigest() == PANEL_SHA, 'panel changed'
    return path, targets


def rows_of(unit):
    """Verified local rows.csv of every bank part of one unit."""
    state = json.loads((ROWS / 'state.json').read_text(encoding='utf-8'))
    out = []
    for record in state['units']:
        if record['unit'] == unit:
            assert record['verified'], 'unverified rows: ' + unit
            path = ROWS_DATA / record['path']
            assert sha(path) == record['sha256'], 'rows table changed: ' + unit
            with path.open(encoding='utf-8', newline='') as f:
                out.append((record, list(csv.DictReader(f))))
    assert out, 'no rows for ' + unit
    return out


def unit_pins(unit, record):
    bank = record['bank']
    receipt = REPO / bank['receipt']
    assert sha(receipt) == bank['receipt_sha256'], 'bank receipt changed: ' + unit
    files = {name: bank['files'][name] for name in ('count_sum.npz', 'mask.npz', 'rows.csv')}
    files['complete.json'] = pin(receipt)
    out = dict(unit=unit, kernel=bank['kernel'], relative_path=bank.get('relative_path') or 'bank/' + unit,
               files=files, producer=bank['saved_version'], mount=dict(kind='kernel', ref=bank['kernel']))
    copy = bank.get('mountable_copy')
    if copy:
        # The producer cannot be mounted; its declared copy carries the same receipt and pins.
        listed = copy['files']
        if isinstance(listed, list):  # aliased layout: pins are listed by original path
            listed = {f['original_path'].rsplit('/', 1)[1]: dict(bytes=f['bytes'], sha256=f['sha256']) for f in listed}
        assert all(listed[n] == bank['files'][n] for n in ('count_sum.npz', 'mask.npz', 'rows.csv')),             'copy of another bank: ' + unit
        out['mount'] = dict(kind='dataset', ref=copy['dataset'], version=copy['version'])
    return out


def plan_source(name, spec, targets):
    """What the consumer will find, from metadata only: roles, controls, cells per context."""
    wanted, special = set(targets), {'NTC', 'UNASSIGNED', 'NO_METADATA'}
    rename = spec.get('context_rename', {})
    roles, contexts = Counter(), {}
    for unit in spec['units']:
        for _, rows in rows_of(unit):
            for r in rows:
                n, t = int(float(r['n'])), r['target']
                role = ('control' if t == 'NTC' else 'aux_unassigned' if t == 'UNASSIGNED' else
                        'metadata_unresolved' if t == 'NO_METADATA' else
                        'panel_target' if t in wanted else 'outside_frozen_panel')
                roles[role] += n
                if role in ('control', 'panel_target'):
                    key = (rename.get(r['context'], r['context']), r['condition'])
                    c = contexts.setdefault(key, dict(control=Counter(), target=Counter(), by_target=Counter()))
                    if role == 'control':
                        c['control'][r['donor_or_clone']] += n
                    else:
                        c['target'][r['donor_or_clone']] += n
                        c['by_target'][t] += n
    out = []
    for (context, condition), c in sorted(contexts.items()):
        unmatched = sorted(d for d in c['target'] if not c['control'].get(d))
        out.append(dict(context=context, condition=condition, control_cells=sum(c['control'].values()),
                        donors_with_controls=len(c['control']), donors_with_targets=len(c['target']),
                        donors_without_controls=unmatched, panel_targets=len(c['by_target']),
                        panel_targets_min_cells=sum(v >= RECIPE['min_cells'] for v in c['by_target'].values()),
                        target_cells=sum(c['target'].values())))
    return dict(name=name, arm=spec.get('arm'), units=spec['units'], cells_by_role=dict(roles), contexts=out,
                runnable=bool(out) and all(not c['donors_without_controls'] and c['control_cells'] > 0 for c in out)
                and any(c['panel_targets_min_cells'] for c in out))


def piano(out):
    _, targets = panel()
    document = specs()
    plans = {name: plan_source(name, spec, targets) for name, spec in document['sources'].items()}
    blocked = {}
    for name in document['not_launched']:
        spec = dict(units=[name], arm='not_launched')
        blocked[name] = dict(plan_source(name, spec, targets), declared_reason=document['not_launched'][name])
    write_new(out, dict(utc=now(), expected_sha256=EXPECTED_SHA, rows=sha(ROWS / 'state.json'),
                        recipe=RECIPE, sources=plans, not_launched=blocked,
                        scope='metadata plan only; no count was read'))
    for name, p in {**plans, **blocked}.items():
        print(name, 'runnable' if p['runnable'] else 'NOT runnable',
              [(c['context'], c['control_cells'], c['panel_targets_min_cells'], len(c['donors_without_controls']))
               for c in p['contexts']][:6])


def stage_dir(name):
    return HERE / 'derivazioni' / name / REVISION


def slug_of(name, spec):
    return '%s/vcc-fonte-%s-%s' % (spec['owner'], name.replace('_', '-'), REVISION)


def prepara(name):
    spec = specs()['sources'][name]
    units = expected_units()
    panel_file, targets = panel()
    axis = DATA / 'raw/controls/gene_names.csv'
    assert sha(axis) == AXIS_SHA, 'axis changed'
    plan = plan_source(name, spec, targets)
    if not plan['runnable']:
        raise ValueError('metadata plan says this derivation cannot run: ' + name)
    stage = stage_dir(name) / 'package'
    stage.mkdir(parents=True, exist_ok=False)
    pinned = [unit_pins(u, units[u]) for u in spec['units']]
    owners = {u['mount']['ref'].split('/')[0] for u in pinned}
    if owners != {spec['owner']}:
        raise ValueError('bank and consumer on different accounts: access must be proven first')
    params = dict(kind='production_source_fragment', name=name, study=spec['study'], modality=spec['modality'],
                  arm=spec['arm'], units=pinned, recipe=RECIPE,
                  axis=dict(sha256=AXIS_SHA, genes=18533), panel=dict(targets=targets, panel_sha256=PANEL_SHA),
                  embedded_inputs={'gene_names.csv': pin(axis), 'pert_counts.csv': pin(panel_file)},
                  context_rename=spec.get('context_rename', {}), merge_blocks=bool(spec.get('merge_blocks')),
                  context_is_donor=bool(spec.get('context_is_donor')), compare_to=spec.get('compare_to'),
                  hidden_targets=[], held_groups=[], protected_units=['h1_test'],
                  min_ram_bytes=int(spec.get('min_ram_gib', 8)) << 30, caveat=spec.get('caveat'),
                  expected_sha256=EXPECTED_SHA, claims_complete_catalogue=False)
    (stage / 'params.json').write_text(json.dumps(params, indent=1) + '\n', encoding='utf-8')
    sources = {n: (HERE / 'consumer' / n).read_bytes() for n in ('adapter.py', 'estimator.py', 'runtime.py')}
    sources.update({'gene_names.csv': axis.read_bytes(), 'pert_counts.csv': panel_file.read_bytes(),
                    'params.json': (stage / 'params.json').read_bytes()})
    payload = {n: dict(data=base64.b64encode(zlib.compress(b)).decode(), sha256=hashlib.sha256(b).hexdigest())
               for n, b in sources.items()}
    code = 'import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\n'
    code += 'os.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP=' + repr(payload) + '\n'
    code += ('for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));'
             'assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n')
    code += 'runpy.run_path("runtime.py",run_name="__main__")\n'
    ast.parse(code)
    if len(code.encode()) > 900000:
        raise ValueError('code size budget exceeded')
    (stage / 'run.py').write_text(code, encoding='utf-8')
    slug = slug_of(name, spec)
    datasets = [spec['compare_to']['dataset']] if spec.get('compare_to') else []
    datasets += sorted({u['mount']['ref'] for u in pinned if u['mount']['kind'] == 'dataset'})
    meta = dict(id=slug, title=slug.split('/')[1], code_file='run.py', language='python', kernel_type='script',
                is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=False,
                dataset_sources=datasets,
                kernel_sources=sorted({u['mount']['ref'] for u in pinned if u['mount']['kind'] == 'kernel'}),
                competition_sources=[])
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
    write_new(stage_dir(name) / 'prepared.json', dict(
        utc=now(), slug=slug, stage=stage.relative_to(REPO).as_posix(), code=pin(stage / 'run.py'),
        params=pin(stage / 'params.json'), metadata=pin(stage / 'kernel-metadata.json'),
        modules={n: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest()) for n, b in sources.items()},
        plan=plan, full_training=False, compute_started=False))
    print(json.dumps(dict(slug=slug, code_bytes=len(code.encode()), contexts=len(plan['contexts']))))


def listing(owner):
    rc, body = call(owner, ['kernels', 'list', '--mine', '--page-size', '20', '--sort-by', 'dateRun', '--csv'])
    if rc:
        raise RuntimeError('account listing failed: ' + owner)
    return owner, [r['ref'] for r in csv.DictReader(io.StringIO(body)) if r.get('ref')]


def preflight(out):
    """Latest twenty jobs per account. A status that cannot be read counts as an occupied slot."""
    with ThreadPoolExecutor(3) as pool:
        listed = list(pool.map(listing, CONFIG))
    pairs = sorted((owner, ref) for owner, refs in listed for ref in refs)

    def status(pair):
        rc, body = call(pair[0], ['kernels', 'status', pair[1]])
        return dict(owner=pair[0], job=pair[1], returncode=rc, status=body)
    with ThreadPoolExecutor(5) as pool:
        observed = list(pool.map(status, pairs))
    active = Counter(r['owner'] for r in observed
                     if r['returncode'] or any(s in r['status'] for s in ('RUNNING', 'QUEUED')))
    write_new(out, dict(utc=now(), scope='20 latest dateRun per account', observed=observed,
                        active={o: active.get(o, 0) for o in CONFIG}, slot_limit_per_account=5,
                        quota_remaining='not exposed by this check'))
    print(json.dumps(dict(active={o: active.get(o, 0) for o in CONFIG}, queries=len(observed))))


def lancia(name, preflight_path):
    spec = specs()['sources'][name]
    here = stage_dir(name)
    proof = json.loads((here / 'prepared.json').read_text(encoding='utf-8'))
    pre = json.loads(Path(preflight_path).read_text(encoding='utf-8'))
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(pre['utc'])).total_seconds()
    if age > 900:
        raise ValueError('fresh preflight required')
    owner = spec['owner']
    ledgers = list((HERE / 'derivazioni').glob('*/*/launch.json'))
    mine = sum(1 for p in ledgers if json.loads(p.read_text())['owner'] == owner
               and datetime.fromisoformat(json.loads(p.read_text())['utc']) > datetime.fromisoformat(pre['utc']))
    if pre['active'].get(owner, 0) + mine >= pre['slot_limit_per_account']:
        raise ValueError('owner slots full: ' + owner)
    stage = REPO / proof['stage']
    for key, filename in (('code', 'run.py'), ('params', 'params.json')):
        if sha(stage / filename) != proof[key]['sha256']:
            raise ValueError('prepared package changed')
    rc, body = call(owner, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'])
    if rc or proof['slug'] in body:
        raise ValueError('job already exists or dedup lookup failed')
    receipt = dict(utc=now(), slug=proof['slug'], owner=owner, stage=proof['stage'],
                   code_sha256=proof['code']['sha256'], params_sha256=proof['params']['sha256'],
                   preflight_sha256=sha(preflight_path), state='intent', accepted=False, full_training=False)
    ledger = here / 'launch.json'
    write_new(ledger, receipt)
    rc, body = call(owner, ['kernels', 'push', '-p', str(stage)])
    receipt.update(returncode=rc, answer=body, state='push_returned',
                   accepted=rc == 0 and 'successfully pushed' in body)
    if receipt['accepted']:
        rc, status = call(owner, ['kernels', 'status', proof['slug']])
        receipt.update(remote_status_returncode=rc, remote_status=status)
    ledger.write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt.get(k) for k in ('slug', 'accepted', 'remote_status')}))
    if not receipt['accepted']:
        raise RuntimeError('push rejected; intent preserved, diagnose before any retry')


def saved_kernel(owner, slug):
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


def raccogli(name, pattern='fit_receipt.json|resources.json'):
    here = stage_dir(name)
    launch = json.loads((here / 'launch.json').read_text(encoding='utf-8'))
    owner, slug = launch['slug'].split('/')
    rc, status = call(owner, ['kernels', 'status', launch['slug']])
    print(status)
    if rc or 'COMPLETE' not in status:
        if 'ERROR' in status or 'CANCEL' in status:
            failed = here / 'failure'
            failed.mkdir(exist_ok=False)
            write_new(failed / 'provider_status.json', dict(utc=now(), returncode=rc, status=status))
            call(owner, ['kernels', 'output', launch['slug'], '-p', str(failed), '--file-pattern', 'resources.json'])
        return False
    out = here / 'completion'
    out.mkdir(exist_ok=False)
    write_new(out / 'provider_status.json', dict(utc=now(), returncode=rc, status=status))
    rc, answer = call(owner, ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern', pattern])
    write_new(out / 'retrieval.json', dict(returncode=rc, answer=answer))
    if rc:
        raise ValueError('small receipt retrieval failed')
    saved = saved_kernel(owner, slug)
    stage = REPO / launch['stage']
    code, params = stage / 'run.py', stage / 'params.json'
    assert sha(code) == launch['code_sha256'] and sha(params) == launch['params_sha256'], 'launched package changed'
    assert saved.blob.source.replace('\r\n', '\n') == code.read_text(encoding='utf-8').replace('\r\n', '\n'), 'saved code differs'
    p = json.loads(params.read_text(encoding='utf-8'))
    proof = json.loads((out / 'fit_receipt.json').read_text(encoding='utf-8'))
    assert proof['state'] == 'derived_production_fragment' and proof['name'] == name
    assert proof['params_sha256'] == launch['params_sha256'] and proof['recipe'] == p['recipe']
    assert proof['input_hashes'] == {u['unit']: u['files'] for u in p['units']}
    assert proof['axis_sha256'] == AXIS_SHA and proof['panel_sha256'] == PANEL_SHA
    assert proof['matrix_hash_verified_in_consumer'] and not proof['mixer_consumed']
    assert set(proof['targets']) <= set(p['panel']['targets'])
    record = dict(utc=now(), job=launch['slug'], version=saved.metadata.current_version_number,
                  saved_code_matches=True, code_sha256=sha(code), params_sha256=sha(params),
                  receipt=pin(out / 'fit_receipt.json'), targets=proof['targets'], n_cells=proof['n_cells'],
                  contexts=len(proof['contexts']), outputs=proof['outputs'], verified=True, mixer_consumed=False,
                  scope='saved code and real runtime receipt; the table stays in the cloud and the fit must hash it')
    write_new(out / 'verification.json', record)
    print(json.dumps({k: record[k] for k in ('job', 'version', 'targets', 'contexts', 'verified')}))
    return True


OTHER = {'righe': 'fetch_rows.py', 'ammissione': 'ammissione.py', 'registro': 'registro.py',
         'fit': 'fit/prepara_fit.py', 'riuso': 'fit/riuso.py', 'a549': 'a549_identita.py'}


if __name__ == '__main__':
    command, args = sys.argv[1], sys.argv[2:]
    if command in OTHER:  # the other steps of the same path, each in its own file
        import runpy
        sys.argv = [str(HERE / OTHER[command]), *args]
        sys.path.insert(0, str(HERE))
        runpy.run_path(sys.argv[0], run_name='__main__')
    else:
        {'piano': piano, 'preflight': preflight, 'prepara': prepara, 'lancia': lancia,
         'raccogli': raccogli}[command](*args)
