"""Start the r7 production mix as soon as H1 is derived; include ready KOLF pan."""
import ast,base64,hashlib,json,shutil,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

worker=HERE/'agenti/grok_transfer_esteso_r7'
src=worker/'packages/vcc-effects-mix-t25-r7'
dest=HERE/'extended_mix_launch_r1'
dest.mkdir(exist_ok=True)
slug='vcc-effects-mix-t25-bank-r1'
owner='davideferrante11'
ledger=dest/(slug+'.json')
assert not ledger.exists(),'intent already exists; do not duplicate'
prepath=HERE/'preflight_r7_dispatch_r1.json'
pre=json.loads(prepath.read_text())
assert (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()<900,'fresh census required'
assert pre['active'].get(owner,0)+2<5,'conservative count includes both newly launched jobs'
assert not any(r['job']==owner+'/'+slug for r in pre['observed'])
status=json.loads((HERE/'h1_joint_completion_r1/status.json').read_text())
assert status['status']=='derived' and not status['blocked_output_splits']
params=json.loads((src/'params.json').read_text())
meta=json.loads((src/'kernel-metadata.json').read_text())
source=(src/'run.py').read_text(encoding='utf-8')
embedded=next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
for name,item in embedded.items():
    b=base64.b64decode(item['base64'])
    assert hashlib.sha256(b).hexdigest()==item['sha256']
assert json.loads(base64.b64decode(embedded['params.json']['base64']))==params
pan='davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1'
public=json.loads((HERE/'public_kolf_pan_r1/consumer_verified.json').read_text())
assert public['jobs'][0]['job']==pan and public['jobs'][0]['is_private'] is False
panentry=next(e for e in params['expected'] if e['unit']=='kolf_pan_genome')
assert panentry['slug']==pan
panentry['admission']='required'
if pan not in meta['kernel_sources']:
    meta['kernel_sources'].append(pan)
params['catalogue_gaps']=[s for s in params['catalogue_gaps'] if not s.startswith('kolf_pan_genome')]
repair='davideferrante11/vcc-effects-hek293t-j-a549-f4-r7'
rc,repair_status=call(owner,['kernels','status',repair])
if rc or 'COMPLETE' not in repair_status:
    meta['kernel_sources'].remove(repair)
    params['catalogue_gaps'].append('HEK J:A549:f4 repair pending; production statistic already present; validation deferred')
refs=meta['kernel_sources']
def input_status(ref):
    rc,answer=call(owner,['kernels','status',ref])
    assert rc==0 and 'COMPLETE' in answer,'input not mountable/complete: '+ref
    return ref,answer
with ThreadPoolExecutor(max_workers=5) as pool:
    inputs=dict(pool.map(input_status,refs))
assert len(refs)==len(set(refs))
assert params['panel']['n']==300
assert params['final_mix']['gamma']==1 and params['final_mix']['reliability_scale']==100
assert params['final_mix']['amplitude']==1.576
assert params['emission']['effects_scale']==1.5
meta['id']=owner+'/'+slug
meta['title']=slug
stage=dest/slug
stage.mkdir(exist_ok=False)
payload=json.dumps(params).encode()
embedded['params.json']={'base64':base64.b64encode(payload).decode(),'sha256':hashlib.sha256(payload).hexdigest()}
code='import json,os,shutil\nfrom pathlib import Path\nimport psutil\n'
code+='r={"ram_available":psutil.virtual_memory().available,"cpu_count":os.cpu_count(),"disk_available":shutil.disk_usage("/kaggle/working").free}\n'
code+='Path("/kaggle/working/runtime_resources.json").write_text(json.dumps(r));print(json.dumps(r),flush=True)\n'
code+='assert r["ram_available"]>12*1024**3 and r["disk_available"]>12*1024**3,"runtime capacity insufficient"\n'
code+='import base64,hashlib,runpy,sys\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(embedded)+'\n'
code+='for name,item in P.items():\n b=base64.b64decode(item["base64"]);assert hashlib.sha256(b).hexdigest()==item["sha256"];Path(name).write_bytes(b)\n'
code+='runpy.run_path("mix_model.py",run_name="__main__")\n'
(stage/'run.py').write_text(code,encoding='utf-8')
(stage/'params.json').write_text(json.dumps(params,indent=2),encoding='utf-8')
(stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
receipt={'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'owner':owner,'stage':str(stage),
         'code_sha256':sha(stage/'run.py'),'params_sha256':sha(stage/'params.json'),'preflight_sha256':sha(prepath),
         'parent_updates':['include verified public KOLF pan','defer nonrequired HEK validation repair if running'],
         'worker_package_code_sha256':sha(src/'run.py'),'inputs':inputs,'accepted':False,'state':'intent',
         'scope':'first admitted partial extended production transfer; not complete D053 catalogue',
         'submission_authorized':True,'comparative_bench_required_before_submission':False}
ledger.open('x').write(json.dumps(receipt,indent=2))
rc,answer=call(owner,['kernels','push','-p',str(stage)])
receipt.update(returncode=rc,answer=answer,accepted=rc==0 and 'successfully pushed' in answer,state='push_returned')
if receipt['accepted']:
    rc,remote=call(owner,['kernels','status',meta['id']])
    receipt.update(remote_status=remote,remote_status_returncode=rc)
ledger.write_text(json.dumps(receipt,indent=2))
print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
assert receipt['accepted'],'push failed; inspect intent before retry'
