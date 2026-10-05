"""Launch reviewed, independent source-effect jobs; never declare a full fit."""
import ast,base64,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

WORKER=HERE/'agenti/grok_transfer_esteso_r4'
SELECT=('orion_hct116','orion_hek293t','rpe1','jurkat_nadig','k562_essential')

def main():
    dest=HERE/'sourcefits_launch_r1';dest.mkdir(exist_ok=True)
    prepath=HERE/'preflight_sourcefits_r1.json'
    pre=json.loads(prepath.read_text())
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    if age>900:raise ValueError('fresh preflight required')
    dispatch=json.loads((WORKER/'ready_dispatch.json').read_text())
    jobs={p['slug']:p for p in dispatch['packages']}
    active=dict(pre['active'])
    seen={r['job'] for r in pre['observed']}
    for name in SELECT:
        slug='vcc-effects-'+name.replace('_','-')+'-r4'
        job=jobs[slug];owner=job['owner'];stage=WORKER/'packages'/slug
        ledger=dest/(slug+'.json')
        if ledger.exists():continue
        meta=json.loads((stage/'kernel-metadata.json').read_text())
        if meta['id'] in seen:raise ValueError('remote job already exists')
        if active.get(owner,0)>=5:continue
        if meta['enable_gpu'] or meta['kernel_sources']!=[job['kernel']]:raise ValueError('input mismatch')
        source=(stage/'run.py').read_text()
        payload=next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
        for module,item in payload.items():
            body=base64.b64decode(item['base64'])
            if hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('embedded hash mismatch')
            if module.endswith('.py') and body!=(WORKER/module).read_bytes():raise ValueError('worker module changed')
        params=json.loads(base64.b64decode(payload['params.json']['base64']))
        if params!=json.loads((stage/'params.json').read_text()):raise ValueError('params differ')
        # Runtime resource measurement precedes hashing/loading matrices. Keep the
        # worker byte snapshots unchanged; an explicit wrapper guards this launch.
        copied=dest/slug
        copied.mkdir(exist_ok=False)
        import shutil
        shutil.copy2(stage/'params.json',copied/'params.json')
        shutil.copy2(stage/'kernel-metadata.json',copied/'kernel-metadata.json')
        guard='import json,os,shutil\nfrom pathlib import Path\nimport psutil\n'
        guard+='r={"ram_available":psutil.virtual_memory().available,"cpu_count":os.cpu_count(),"disk_available":shutil.disk_usage("/kaggle/working").free}\n'
        guard+='Path("/kaggle/working/runtime_resources.json").write_text(json.dumps(r));print(json.dumps(r),flush=True)\n'
        guard+='assert r["ram_available"]>12*1024**3 and r["disk_available"]>12*1024**3,"runtime capacity insufficient"\n'
        (copied/'run.py').write_text(guard+source,encoding='utf-8')
        rc,status=call(owner,['kernels','status',job['kernel']])
        if rc or 'COMPLETE' not in status:raise ValueError('producer not complete: '+job['kernel'])
        receipt={'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'owner':owner,'unit':name,
                 'producer':job['kernel'],'producer_version_pin':job['version'],'producer_status':status,
                 'code_sha256':sha(copied/'run.py'),'params_sha256':sha(copied/'params.json'),
                 'preflight_sha256':sha(prepath),'worker_dispatch_sha256':sha(WORKER/'ready_dispatch.json'),
                 'stage':str(copied),'accepted':False,'state':'intent','full_training':False,
                 'scope':'independent per-source effect estimation; CD4 joint estimation and full mix not adopted'}
        ledger.open('x').write(json.dumps(receipt,indent=1))
        rc,answer=call(owner,['kernels','push','-p',str(copied)])
        receipt.update(returncode=rc,accepted=rc==0 and 'successfully pushed' in answer,state='push_returned',answer=answer)
        if receipt['accepted']:
            rc,remote=call(owner,['kernels','status',meta['id']]);receipt.update(remote_status=remote,remote_status_returncode=rc)
            active[owner]=active.get(owner,0)+1;seen.add(meta['id'])
        ledger.write_text(json.dumps(receipt,indent=1))
        print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
        if not receipt['accepted']:raise RuntimeError('push failed; inspect receipt without duplicating')

if __name__=='__main__':main()
