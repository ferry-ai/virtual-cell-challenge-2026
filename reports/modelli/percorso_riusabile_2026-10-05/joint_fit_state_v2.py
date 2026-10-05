"""Small scientific receipts and failed-kernel logs for accepted CD4 joints."""
import json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from preflight_slots_fast_v1 import call
from source_fit_state_v1 import SOURCE_PROOF

def main():
    prepath=HERE/sys.argv[1];pre=json.loads(prepath.read_text())
    out=HERE/sys.argv[2];out.mkdir(exist_ok=False)
    observed={r['job']:r for r in pre['observed']};results=[]
    previous=HERE/sys.argv[3] if len(sys.argv)>3 else None
    cached={r['job']:r for r in json.loads(previous.read_text())['jobs'] if r.get('saved_code_matches')} if previous else {}
    for ledger in sorted((HERE/'cd4_joint_launch_r1').glob('*.json')):
        launch=json.loads(ledger.read_text())
        if not launch.get('accepted'):continue
        job=launch['slug'];state=observed.get(job)
        if state is None:
            results.append({'job':job,'verified':False,'provider_status':None,'reason':'accepted after census; needs fresh observation'});continue
        if job in cached and cached[job]['provider_status']==state['status']:
            results.append({**cached[job],'reused_receipt_from':str(previous)});continue
        target=out/job.split('/')[-1];target.mkdir()
        record={'job':job,'provider_status':state['status'],'verified':False}
        if state['returncode'] or not any(s in state['status'] for s in ('COMPLETE','ERROR')):
            results.append(record);continue
        rc,_=call(launch['owner'],['kernels','output',job,'-p',str(target),'--file-pattern','job_status.json|runtime_resources.json'])
        record['output_fetch_returncode']=rc
        statuspath=target/'job_status.json'
        if statuspath.is_file():
            assert statuspath.stat().st_size<1024**2
            record.update(scientific_status=json.loads(statuspath.read_text()),status_sha256=sha(statuspath))
        resource=target/'runtime_resources.json'
        if resource.is_file():record['resources']=json.loads(resource.read_text())
        env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
        env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[launch['owner']])
        code=Path(launch['stage'])/'run.py';assert sha(code)==launch['code_sha256']
        p=subprocess.run([sys.executable,'-c',SOURCE_PROOF,job,str(code)],env=env,capture_output=True,text=True,timeout=90)
        if p.returncode:raise ValueError('saved joint code differs or inaccessible')
        record.update(json.loads(p.stdout))
        status=record.get('scientific_status',{})
        record['verified']='COMPLETE' in state['status'] and status.get('status')=='derived' and status.get('n_donors')==4
        if 'ERROR' in state['status'] or status.get('status') not in ('derived',None):
            rc,log=call(launch['owner'],['kernels','logs',job])
            (target/'kernel.log').write_text(log,encoding='utf-8');record['log_returncode']=rc;record['log_sha256']=sha(target/'kernel.log')
        results.append(record)
    (out/'verification.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'preflight_sha256':sha(prepath),'jobs':results,'scope':'saved code, four donor scientific status, runtime resources; matrix hashes remain consumer duty'},indent=1))
    print(json.dumps(results))
if __name__=='__main__':main()
