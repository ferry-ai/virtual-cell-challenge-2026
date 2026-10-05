"""One same-code retry for a verified pre-wrapper failure, preserving intent."""
import hashlib,json,shutil
from datetime import datetime,timezone
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

original=HERE/'extended_mix_launch_r1/vcc-effects-mix-t25-bank-r1.json'
previous=json.loads(original.read_text())
oldref=previous['slug']
owner=previous['owner']
failure=HERE/'mix_failure_r1'
assert (failure/'vcc-effects-mix-t25-bank-r1.log').read_text().strip()=='[]'
assert not (failure/'runtime_resources.json').exists()
assert not (failure/'status.json').exists()
rc,state=call(owner,['kernels','status',oldref])
assert rc==0 and 'ERROR' in state
prepath=HERE/'preflight_mix_retry_r1.json'
pre=json.loads(prepath.read_text())
assert (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()<900
assert pre['active'].get(owner,0)<5
slug='vcc-effects-mix-t25-bank-r1-retry1'
ref=owner+'/'+slug
assert not any(r['job']==ref for r in pre['observed'])
dest=HERE/'extended_mix_launch_r2'
dest.mkdir(exist_ok=True)
ledger=dest/(slug+'.json')
assert not ledger.exists(),'retry intent already exists'
oldstage=HERE/'extended_mix_launch_r1/vcc-effects-mix-t25-bank-r1'
assert sha(oldstage/'run.py')==previous['code_sha256']
assert sha(oldstage/'params.json')==previous['params_sha256']
stage=dest/slug
stage.mkdir(exist_ok=False)
for name in ('run.py','params.json','kernel-metadata.json'):
    shutil.copy2(oldstage/name,stage/name)
metadata=json.loads((stage/'kernel-metadata.json').read_text())
metadata['id']=ref
metadata['title']=slug
(stage/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2))
diagnosis={'utc':datetime.now(timezone.utc).isoformat(),'job':oldref,'provider_status':state,
           'runtime_resources_saved':False,'scientific_status_saved':False,
           'saved_log_sha256':sha(failure/'vcc-effects-mix-t25-bank-r1.log'),
           'saved_log_empty':True,'cause':'unknown provider failure before wrapper evidence',
           'retry_policy':'one same-code retry; no second retry without new diagnosis'}
diag=failure/'diagnosis.json'
diag.open('x').write(json.dumps(diagnosis,indent=2))
receipt={**previous,'utc':datetime.now(timezone.utc).isoformat(),'slug':ref,'stage':str(stage),
         'accepted':False,'state':'intent','supersedes_failed':oldref,
         'same_code_as':oldref,'failure_diagnosis_sha256':sha(diag),
         'preflight_sha256':sha(prepath),'attempt':1}
for key in ('answer','returncode','remote_status','remote_status_returncode'):
    receipt.pop(key,None)
ledger.open('x').write(json.dumps(receipt,indent=2))
rc,answer=call(owner,['kernels','push','-p',str(stage)])
receipt.update(returncode=rc,answer=answer,accepted=rc==0 and 'successfully pushed' in answer,state='push_returned')
if receipt['accepted']:
    rc,remote=call(owner,['kernels','status',ref])
    receipt.update(remote_status=remote,remote_status_returncode=rc)
ledger.write_text(json.dumps(receipt,indent=2))
print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
assert receipt['accepted'],'retry push failed; inspect intent before proceeding'
