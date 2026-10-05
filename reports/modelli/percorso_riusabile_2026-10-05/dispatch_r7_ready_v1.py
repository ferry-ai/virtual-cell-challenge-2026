"""Dispatch ready independent r7 jobs with immutable parent copies and dedup."""
import ast, base64, hashlib, json, shutil, sys
from datetime import datetime, timezone
from pipeline_state import HERE, sha
from preflight_slots_fast_v1 import call

worker = HERE/'agenti/grok_transfer_esteso_r7'
prepath = HERE/sys.argv[1]
pre = json.loads(prepath.read_text())
assert 'active' in pre and (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()<900
ready_path = worker/'ready_dispatch.json'
ready = json.loads(ready_path.read_text())
dest = HERE/'r7_ready_launch_r1'
dest.mkdir(exist_ok=True)
active = dict(pre['active'])
seen = {r['job'] for r in pre['observed']}
for job in ready['packages']:
    if not (job.get('push_now') and job.get('ready_for_parent')):
        continue
    slug, owner = job['slug'], job['owner']
    assert slug in ('vcc-effects-h1-joint-r7','vcc-effects-hek293t-j-a549-f4-r7')
    ledger = dest/(slug+'.json')
    if ledger.exists():
        continue
    src = worker/'packages'/slug
    meta = json.loads((src/'kernel-metadata.json').read_text())
    assert meta['id'] not in seen and active.get(owner, 0)<5
    assert meta['kernel_sources']==job['kernel_sources']
    assert not meta['enable_gpu'] and not meta['enable_internet']
    source = (src/'run.py').read_text(encoding='utf-8')
    embedded = next(ast.literal_eval(n.value) for n in ast.parse(source).body
                    if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
    for name, item in embedded.items():
        body = base64.b64decode(item['base64'])
        assert hashlib.sha256(body).hexdigest()==item['sha256']
        if name.endswith('.py'):
            ast.parse(body)
    params = json.loads(base64.b64decode(embedded['params.json']['base64']))
    assert params==json.loads((src/'params.json').read_text())
    if 'h1-joint' in slug:
        assert {b['unit'] for b in params['banks']}=={'h1_train','h1_val'}
        assert params['h1_test_included'] is False and params['panel']['n']==300
    inputs = {}
    for ref in meta['kernel_sources']:
        rc, status = call(owner, ['kernels','status',ref])
        assert rc==0 and 'COMPLETE' in status, 'input inaccessible/incomplete: '+ref
        inputs[ref] = status
    stage = dest/slug
    stage.mkdir(exist_ok=False)
    for name in ('params.json','kernel-metadata.json'):
        shutil.copy2(src/name, stage/name)
    guard = 'import json,os,shutil\nfrom pathlib import Path\nimport psutil\n'
    guard += 'r={"ram_available":psutil.virtual_memory().available,"cpu_count":os.cpu_count(),"disk_available":shutil.disk_usage("/kaggle/working").free}\n'
    guard += 'Path("/kaggle/working/runtime_resources.json").write_text(json.dumps(r));print(json.dumps(r),flush=True)\n'
    guard += 'assert r["ram_available"]>12*1024**3 and r["disk_available"]>12*1024**3,"runtime capacity insufficient"\n'
    (stage/'run.py').write_text(guard+source, encoding='utf-8')
    receipt = {'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'owner':owner,
               'stage':str(stage),'code_sha256':sha(stage/'run.py'),'params_sha256':sha(stage/'params.json'),
               'preflight_sha256':sha(prepath),'worker_dispatch_sha256':sha(ready_path),
               'inputs':inputs,'accepted':False,'state':'intent','full_training':False}
    ledger.open('x').write(json.dumps(receipt, indent=2))
    rc, answer = call(owner, ['kernels','push','-p',str(stage)])
    receipt.update(returncode=rc, answer=answer, accepted=rc==0 and 'successfully pushed' in answer,
                   state='push_returned')
    if receipt['accepted']:
        rc, status = call(owner, ['kernels','status',meta['id']])
        receipt.update(remote_status=status,remote_status_returncode=rc)
        active[owner] = active.get(owner,0)+1
        seen.add(meta['id'])
    ledger.write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
    if not receipt['accepted']:
        raise RuntimeError('push failed; inspect intent before retry')
