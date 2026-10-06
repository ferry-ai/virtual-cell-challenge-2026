import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from preflight_slots_fast_v1 import call

here=Path(__file__).resolve().parent
proof=json.loads((here/'prepared_r2.json').read_text())
prepath=here/'preflight_r1.json'
pre=json.loads(prepath.read_text())
age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
if age>600 or any(r['returncode'] for r in pre['observed']):
    raise ValueError('fresh complete preflight required')
owner=proof['slug'].split('/')[0]
if pre['active'].get(owner,0)>=5:
    raise ValueError('owner slots full')
stage=Path(proof['stage'])
for name,key in [('run.py','code'),('params.json','params')]:
    if hashlib.sha256((stage/name).read_bytes()).hexdigest()!=proof[key]['sha256']:
        raise ValueError('prepared package changed')
rc,body=call(owner,['kernels','list','--mine','--search',proof['slug'].split('/')[1],'--csv'])
if rc or proof['slug'] in body:
    raise ValueError('job already exists or dedup lookup failed')
ledger=here/'launch.json'
receipt=dict(utc=datetime.now(timezone.utc).isoformat(),slug=proof['slug'],owner=owner,
             stage=str(stage),code_sha256=proof['code']['sha256'],params_sha256=proof['params']['sha256'],
             preflight_sha256=hashlib.sha256(prepath.read_bytes()).hexdigest(),state='intent',accepted=False,
             full_training=False,not_heldout_validation=True)
with ledger.open('x',encoding='utf-8') as f:
    json.dump(receipt,f,indent=1)
rc,body=call(owner,['kernels','push','-p',str(stage)])
receipt.update(returncode=rc,answer=body,state='push_returned',accepted=rc==0 and 'successfully pushed' in body)
if receipt['accepted']:
    rc,status=call(owner,['kernels','status',proof['slug']])
    receipt.update(remote_status_returncode=rc,remote_status=status)
ledger.write_text(json.dumps(receipt,indent=1)+'\n',encoding='utf-8')
print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}))
if not receipt['accepted']:
    raise RuntimeError('push rejected; preserve intent, diagnose before retry')
