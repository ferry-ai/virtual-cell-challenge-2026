"""Diagnose only two new KOLF failures; retry once only if no runtime executed."""
import json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

def main():
    prepath=HERE/sys.argv[1];pre=json.loads(prepath.read_text())
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()<900
    out=HERE/'kolf_startup_failure_r1';out.mkdir(exist_ok=False)
    dest=HERE/'sourcefits_launch_r1';observed={r['job']:r for r in pre['observed']};active=dict(pre['active']);records=[]
    for unit in ('metabolic','strong'):
        old='vcc-effects-kolf-'+unit+'-r4';new=old+'-retry1';owner='davideferrante11'
        launch=json.loads((dest/(old+'.json')).read_text());assert 'ERROR' in observed[launch['slug']]['status']
        ledger=dest/(new+'.json');assert not ledger.exists()
        folder=out/old;folder.mkdir()
        rc,_=call(owner,['kernels','output',launch['slug'],'-p',str(folder),'--file-pattern','job_status.json|runtime_resources.json'])
        log=folder/(old+'.log');logs=log.read_text(encoding='utf-8') if log.exists() else None
        record={'job':launch['slug'],'provider_status':observed[launch['slug']]['status'],'fetch_returncode':rc,'runtime_resources_saved':(folder/'runtime_resources.json').exists(),'scientific_status_saved':(folder/'job_status.json').exists(),'log_sha256':sha(log) if log.exists() else None}
        records.append(record);(out/'diagnosis.json').write_text(json.dumps(records,indent=1))
        if rc or record['runtime_resources_saved'] or record['scientific_status_saved'] or logs is None or logs.strip()!='[]':
            print(json.dumps({**record,'action':'inspect actual log; no blind retry'}));continue
        assert active.get(owner,0)<5
        src=Path(launch['stage']);stage=dest/new;stage.mkdir(exist_ok=False)
        assert sha(src/'run.py')==launch['code_sha256']
        for name in ('run.py','params.json'):shutil.copy2(src/name,stage/name)
        meta=json.loads((src/'kernel-metadata.json').read_text());meta['id']=owner+'/'+new;meta['title']=new
        (stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
        for ref in meta['kernel_sources']:
            rc,status=call(owner,['kernels','status',ref]);assert rc==0 and 'COMPLETE' in status
        receipt={**{k:v for k,v in launch.items() if k not in ('answer','remote_status','remote_status_returncode','returncode')},'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'stage':str(stage),'code_sha256':sha(stage/'run.py'),'params_sha256':sha(stage/'params.json'),'supersedes_failed':launch['slug'],'retry_reason':'No scientific status, resource log or execution log; pre-runtime provider failure; same code retry once','diagnosis_sha256':sha(out/'diagnosis.json'),'accepted':False,'state':'intent','preflight_sha256':sha(prepath)}
        # Freeze the per-job diagnosis instead of binding a mutable batch ledger.
        (folder/'diagnosis.json').write_text(json.dumps(record,indent=1));receipt['diagnosis_sha256']=sha(folder/'diagnosis.json')
        ledger.open('x').write(json.dumps(receipt,indent=1))
        rc,answer=call(owner,['kernels','push','-p',str(stage)]);receipt.update(returncode=rc,answer=answer,accepted=rc==0 and 'successfully pushed' in answer,state='push_returned')
        if receipt['accepted']:
            rc,status=call(owner,['kernels','status',meta['id']]);receipt.update(remote_status=status,remote_status_returncode=rc);active[owner]=active.get(owner,0)+1
        ledger.write_text(json.dumps(receipt,indent=1));print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
        if not receipt['accepted']:raise RuntimeError('push failed, inspect receipt')
if __name__=='__main__':main()
