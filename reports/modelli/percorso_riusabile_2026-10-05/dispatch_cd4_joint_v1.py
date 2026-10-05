"""Parent dispatch of reviewed four-donor CD4 effect estimates; not full mix."""
import ast,base64,hashlib,json,shutil,sys
from datetime import datetime,timezone
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

def main():
    worker=HERE/'agenti/grok_transfer_esteso_r5'
    dispatch=json.loads((worker/'ready_dispatch.json').read_text())
    prepath=HERE/sys.argv[1];pre=json.loads(prepath.read_text())
    if (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()>900:raise ValueError('stale preflight')
    dest=HERE/'cd4_joint_launch_r1';dest.mkdir(exist_ok=True)
    active=dict(pre['active']);seen={r['job'] for r in pre['observed']}
    for job in dispatch['packages']:
        if job['phase']!='cd4_joint':continue
        slug=job['slug'];owner=job['owner'];src=worker/'packages'/slug
        ledger=dest/(slug+'.json')
        if ledger.exists():continue
        meta=json.loads((src/'kernel-metadata.json').read_text())
        if meta['id'] in seen:raise ValueError('remote duplicate')
        if active.get(owner,0)>=5:continue
        source=(src/'run.py').read_text(encoding='utf-8')
        embedded=next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
        for name,item in embedded.items():
            b=base64.b64decode(item['base64'])
            assert hashlib.sha256(b).hexdigest()==item['sha256']
            if name.endswith('.py'):assert b==(worker/name).read_bytes(),'worker code mismatch'
        params=json.loads(base64.b64decode(embedded['params.json']['base64']))
        assert params==json.loads((src/'params.json').read_text())
        assert len(params['donors'])==4 and params['matrix']=='count_sum'
        assert params['estimator']=={'phi':.2,'min_control_frac':1e-6,'min_cells':10.,'pseudo':.5,'pseudo_scale':'constant','min_expected':1.}
        assert set(meta['kernel_sources'])=={p['kernel'] for p in params['donors']}
        assert meta['kernel_sources']==job['kernel_sources'] and not meta['enable_gpu'] and not meta['enable_internet']
        inputs={}
        for ref in meta['kernel_sources']:
            rc,status=call(owner,['kernels','status',ref])
            if rc or 'COMPLETE' not in status:raise ValueError('input inaccessible or incomplete: '+ref)
            inputs[ref]=status
        stage=dest/slug;stage.mkdir(exist_ok=False)
        for name in ('params.json','kernel-metadata.json'):shutil.copy2(src/name,stage/name)
        guard='import json,os,shutil\nfrom pathlib import Path\nimport psutil\n'
        guard+='r={"ram_available":psutil.virtual_memory().available,"cpu_count":os.cpu_count(),"disk_available":shutil.disk_usage("/kaggle/working").free}\n'
        guard+='Path("/kaggle/working/runtime_resources.json").write_text(json.dumps(r));print(json.dumps(r),flush=True)\n'
        guard+='assert r["ram_available"]>12*1024**3 and r["disk_available"]>12*1024**3,"runtime capacity insufficient"\n'
        (stage/'run.py').write_text(guard+source,encoding='utf-8')
        receipt={'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'owner':owner,'stage':str(stage),'code_sha256':sha(stage/'run.py'),'params_sha256':sha(stage/'params.json'),'preflight_sha256':sha(prepath),'worker_dispatch_sha256':sha(worker/'ready_dispatch.json'),'inputs':inputs,'accepted':False,'state':'intent','full_training':False,'scope':'production effects for one CD4 condition with four donors; C/J evaluation requires separately held-out effects before statistics'}
        ledger.open('x').write(json.dumps(receipt,indent=1))
        rc,answer=call(owner,['kernels','push','-p',str(stage)])
        receipt.update(returncode=rc,answer=answer,accepted=rc==0 and 'successfully pushed' in answer,state='push_returned')
        if receipt['accepted']:
            rc,status=call(owner,['kernels','status',meta['id']]);receipt.update(remote_status=status,remote_status_returncode=rc)
            active[owner]=active.get(owner,0)+1;seen.add(meta['id'])
        ledger.write_text(json.dumps(receipt,indent=1))
        print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
        if not receipt['accepted']:raise RuntimeError('push failed; inspect ledger before retry')
if __name__=='__main__':main()
