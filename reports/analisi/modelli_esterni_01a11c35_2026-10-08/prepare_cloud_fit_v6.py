"""Build an immutable private Kaggle package; never launch or print locators."""
import argparse
import base64
import csv
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from job_preflight import validate
from pie_adapter import sha256
from feature_policy import validate_queries

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = Path('C:/Users/ferra/vcc2026-data')
OWNER = REPO/'reports/modelli/dati_transfer_2026-10-08_01a11c34'


def write(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=1, allow_nan=False)


def prepare(regime, revision, out, receipt_path, runtime_owner, inputs_path, inputs_sha256):
    if runtime_owner not in {'davideferrante11','davidmaisterx','davideferante'}:
        raise ValueError('unconfigured account')
    if out.resolve().is_relative_to(REPO):
        raise ValueError('private package must remain outside repository')
    if out.exists() or receipt_path.exists():
        raise FileExistsError('immutable destination exists')
    if sha256(inputs_path) != inputs_sha256:
        raise ValueError('runtime routing contract changed')
    inputs = json.loads(inputs_path.read_text())
    for name in ('view', 'private_locators'):
        item = inputs[name]; path = Path(item['path'])
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError('runtime input identity differs')
    view = json.loads(Path(inputs['view']['path']).read_text())
    mounts = set(inputs['kernel_sources'])
    loc = json.loads(Path(inputs['private_locators']['path']).read_text())
    required = set()
    for chunk in view['chunks']:
        producer = chunk['producer']
        if producer in mounts:
            source = inputs['sources'][producer]
            if source['private'] and producer.split('/')[0] != runtime_owner:
                raise ValueError('private native mount belongs to another account')
        else:
            key = producer + '/' + chunk['producer_file']
            required.add(key)
            item = loc['files'].get(key)
            if not item or any(item[k] != chunk[k] for k in ('sha256','bytes')):
                raise ValueError('no exact authorized route for required chunk')
    if required != set(loc['files']):
        raise ValueError('locator set must contain exactly the required downloaded chunks')
    del loc
    expected_regime = regime.split('-')[0]
    if view['regime'] != expected_regime:
        raise ValueError('regime mismatch')
    job_id = f'esm2-{regime.lower()}-01a11c35-{revision}'
    bundle = out/'bundle'; bundle.mkdir(parents=True)
    modules = ['cloud_fit.py','chunk_store_v2.py','run_sufficient_probe_v2.py',
        'feature_policy.py','target_sufficient_ridge_v2.py','embedding_ridge.py',
        'pie_adapter.py','job_preflight.py','private_download_v2.py']
    for name in modules:
        shutil.copy2(HERE/name, bundle/name)
    shutil.copy2(HERE/'runtime_view_resolver_v2.py', bundle/'runtime_view_resolver.py')
    shutil.copy2(Path(inputs['view']['path']), bundle/'view.json')
    shutil.copy2(Path(inputs['private_locators']['path']), bundle/'private_locators.json')
    locator_doc = json.loads((bundle/'private_locators.json').read_text())
    locator_doc['runtime_owner'] = runtime_owner
    locator_doc['routing_authorization'] = 'Explicit private transfers: call_f35d9965d6a941308163b640c833f8eb plus call_d00b2526c23e4a11b662023128fe9811'
    (bundle/'private_locators.json').write_text(json.dumps(locator_doc,indent=1),encoding='utf-8')
    del locator_doc
    release_path = REPO/inputs['release']['path']
    if sha256(release_path) != inputs['release']['sha256']:
        raise ValueError('release pointer changed')
    release = json.loads(release_path.read_text())
    split_path = Path(release['split']['path'])
    if sha256(split_path) != release['split']['sha256']:
        raise ValueError('split pointer changed')
    split = json.loads(split_path.read_text())
    shutil.copy2(split_path, bundle/'frozen_split.json')
    audit = json.loads((HERE/'public_audit_r1.json').read_text())
    panel_pin = audit['local_inputs']['pert_counts.csv']
    panel_path = Path(panel_pin['path'])
    if sha256(panel_path) != panel_pin['sha256']:
        raise ValueError('panel changed')
    with panel_path.open(encoding='utf-8-sig', newline='') as f:
        panel = sorted({r['target_gene'] for r in csv.DictReader(f)})
    if len(panel) != 300:
        raise ValueError('first production query contract requires frozen panel300')
    if expected_regime == 'production':
        queries = [dict(target=t,context_id='target_only',context_group='target_only') for t in panel]
    elif expected_regime == 'T':
        hidden = split['hidden_targets']
        if len(hidden) != 66:
            raise ValueError('hidden panel changed')
        contexts = {c['context_id']:c['context_group'] for c in view['chunks']}
        queries = [dict(target=t,context_id=c,context_group=g) for c,g in sorted(contexts.items()) for t in hidden]
    else:
        if len(split['held_groups']) != 1:
            raise ValueError('one held lineage per first C/J job required')
        seen = {t for chunk in view['chunks'] for t in chunk['targets']}
        selected = sorted(set(panel) & seen) if expected_regime == 'C' else split['hidden_targets']
        if expected_regime == 'J' and len(selected) != 66:
            raise ValueError('hidden query panel differs')
        queries = [dict(target=t,context_id=regime,context_group=split['held_groups'][0]) for t in selected]
    context_map = {c['context_id']:c['context_group'] for c in view['chunks']}
    validate_queries(expected_regime, {t for c in view['chunks'] for t in c['targets']},
                     list(context_map.values()), list(context_map), queries)
    query_contract = dict(panel_targets=panel,query_targets=sorted({q['target'] for q in queries}),
        unqueried_panel_targets=sorted(set(panel)-{q['target'] for q in queries}),
        policy=('C: only seen targets; unqueried panel targets require explicit baseline fallback in full-panel evaluation'
                if expected_regime=='C' else 'T/J: preregistered hidden panel only' if expected_regime in {'T','J'}
                else 'production: full frozen panel'),
        context_id_semantics='held-lineage fold identifier' if expected_regime in {'C','J'} else 'training context or target_only')
    write(bundle/'query_contract.json',query_contract)
    assets = {Path(i['path']).name:i for i in audit['acquisition_plan'] if i['path'].startswith('esm2/')}
    # Only public asset URLs enter this config; private bearers stay in their separate file.
    assets = {name:{k:item[k] for k in ('bytes','sha256','url')} for name,item in assets.items()}
    verified = json.loads((HERE/'feature_coverage_r1.json').read_text())['esm2_sha256']
    for name in assets:
        assets[name]['sha256'] = verified[name]
    locators = json.loads((bundle/'private_locators.json').read_text())
    private_bytes = sum(i['bytes'] for i in locators['files'].values())
    del locators
    config = dict(job_id=job_id,regime=expected_regime,fold=regime,view_sha256=inputs['view']['sha256'],
        esm2=assets,queries=queries,private_bytes=private_bytes,
        authorization={'fit_human_message':'C/J approval call_19aa555691d3489b86f2cb1e6acd364e item 0',
            'transfer_human_message':'Explicit private transfers: call_f35d9965d6a941308163b640c833f8eb plus call_d00b2526c23e4a11b662023128fe9811',
            'runtime_owner':runtime_owner,'visibility':'private; publication unnecessary'},
        incidents=['E-20260929-003','E-20260929-004','E-20260929-005'],
        colab_status='dispatcher last observed 2026-10-03; not verified active',
        uses_gpu=False, scientific_benefit='not_evaluated')
    write(bundle/'job_config.json', config)
    remote_bundle = PurePosixPath('/kaggle/temp')/(job_id+'-bundle')
    contract = dict(schema_version=1,job_id=job_id+'-package',
        inputs=[dict(id=p.name,bytes=p.stat().st_size,sha256=sha256(p),
            paths={'local':str(p.resolve()),'runtime':str(remote_bundle/p.name)})
            for p in sorted(bundle.iterdir())],
        outputs=[dict(id='new-fit',must_be_absent=True,paths={
            'local':str((out/'local-fit-not-executed').resolve()),
            'runtime':str(PurePosixPath('/kaggle/working')/job_id/'fit')})],
        environment={'packages':{'numpy':None,'scipy':None},
                     'imports':['numpy','scipy.linalg'], 'probes':[]})
    for item in contract['inputs'] + contract['outputs']:
        remote = item['paths']['runtime']
        if not remote.startswith('/kaggle/') or '\\' in remote or not PurePosixPath(remote).is_absolute():
            raise ValueError('runtime paths must be absolute POSIX paths')
    write(bundle/'preflight.json',contract)
    write(out/'local_preflight.json',validate(contract,'local'))
    packed = io.BytesIO()
    with zipfile.ZipFile(packed,'w',compression=zipfile.ZIP_LZMA) as archive:
        for p in sorted(bundle.iterdir()): archive.write(p,arcname=p.name)
    payload = base64.b64encode(packed.getvalue()).decode('ascii')
    source = ('import base64,io,zipfile,sys,os\nfrom pathlib import Path\n'
        'assert os.name=="posix", "This private job requires a Linux runtime"\n'
        'os.environ["OPENBLAS_NUM_THREADS"]="2"\nos.environ["OMP_NUM_THREADS"]="2"\n'
        'os.environ["MKL_NUM_THREADS"]="2"\n'
        f'root=Path({str(remote_bundle)!r})\nroot.mkdir(parents=True,exist_ok=False)\n'
        f'payload={payload!r}\n'
        'with zipfile.ZipFile(io.BytesIO(base64.b64decode(payload))) as z:\n'
        '    assert all(Path(n).name==n for n in z.namelist())\n    z.extractall(root)\n'
        'del payload\nsys.path.insert(0,str(root))\nfrom cloud_fit import main\nmain(root)\n')
    (out/'run.py').write_text(source,encoding='utf-8',newline='\n')
    metadata = dict(id=runtime_owner+'/'+job_id,title=job_id,code_file='run.py',language='python',
        kernel_type='script',is_private=True,enable_gpu=False,enable_internet=True,
        dataset_sources=[],competition_sources=[],kernel_sources=inputs['kernel_sources'])
    write(out/'kernel-metadata.json',metadata)
    receipt = dict(job_id=job_id,slug=metadata['id'],stage=str(out.resolve()),private=True,
        runtime_inputs=dict(path=str(inputs_path.resolve()),sha256=inputs_sha256),
        regime=expected_regime,fold=regime,view_sha256=config['view_sha256'],private_bytes=private_bytes,
        code_sha256=sha256(out/'run.py'),metadata_sha256=sha256(out/'kernel-metadata.json'),
        modules={p.name:sha256(p) for p in bundle.glob('*.py')},
        queries=len(queries),query_contract=query_contract,kernel_sources=inputs['kernel_sources'],
        preparation_only=True,local_preflight_sha256=sha256(out/'local_preflight.json'))
    write(receipt_path,receipt)
    print(json.dumps({k:receipt[k] for k in ('job_id','regime','queries','private_bytes','preparation_only')}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--regime',choices=['production','T','C-K562','C-iPSC','J-K562','J-iPSC'],required=True)
    p.add_argument('--revision',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--runtime-owner',required=True)
    p.add_argument('--runtime-inputs',type=Path,required=True)
    p.add_argument('--runtime-inputs-sha256',required=True)
    a=p.parse_args();prepare(a.regime,a.revision,a.out,a.receipt,a.runtime_owner,a.runtime_inputs,a.runtime_inputs_sha256)
