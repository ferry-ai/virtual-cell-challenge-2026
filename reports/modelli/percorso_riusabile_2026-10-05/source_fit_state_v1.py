"""Incremental source-fit supervision: cached small receipts, fresh status, no matrices."""
import argparse,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from preflight_slots_fast_v1 import call

SOURCE_PROOF='''import json,hashlib,sys
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest
a=KaggleApi();a.authenticate();r=ApiGetKernelRequest();r.user_name,r.kernel_slug=sys.argv[1].split('/')
with a.build_kaggle_client() as c:s=c.kernels.kernels_api_client.get_kernel(r)
expected=Path(sys.argv[2]).read_text(encoding='utf-8')
assert s.blob.source.replace(chr(13)+chr(10),chr(10))==expected.replace(chr(13)+chr(10),chr(10)), 'saved source differs'
print(json.dumps({'version':s.metadata.current_version_number,'saved_source_sha256':hashlib.sha256(s.blob.source.encode()).hexdigest(),'saved_code_matches':True}))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',required=True);p.add_argument('--out',required=True);p.add_argument('--previous',required=True);a=p.parse_args()
    out=HERE/a.out;out.mkdir(exist_ok=False)
    prepath=HERE/a.preflight;pre=json.loads(prepath.read_text())
    observed={r['job']:r for r in pre['observed']}
    previous_path=HERE/a.previous;previous=json.loads(previous_path.read_text())
    cached={r['job']:r for r in previous['jobs'] if r.get('verified')}
    launches=[]
    for f in sorted((HERE/'sourcefits_launch_r1').glob('*.json')):
        d=json.loads(f.read_text())
        if d.get('accepted') and d.get('slug') and d.get('owner'):launches.append(d)
    results=[]
    for launch in launches:
        job=launch['slug'];observation=observed.get(job)
        if not observation:raise ValueError('launched job absent from fresh preflight: '+job)
        if job in cached and cached[job].get('saved_code_matches'):
            results.append({**cached[job],'reused_receipt_from':str(previous_path),'provider_status':observation['status']});continue
        if observation['returncode'] or 'COMPLETE' not in observation['status']:
            results.append({'job':job,'verified':False,'provider_status':observation['status']});continue
        target=out/job.replace('/','__');target.mkdir()
        record={'job':job,'verified':False,'provider_status':observation['status']}
        if job in cached:
            record.update(cached[job]);record['reused_receipt_from']=str(previous_path)
        else:
            rc,_=call(launch['owner'],['kernels','output',job,'-p',str(target),'--file-pattern','job_status.json|runtime_resources.json'])
            statuspath=target/'job_status.json'
            if rc or not statuspath.is_file():raise ValueError('new status retrieval failed: '+job)
            if statuspath.stat().st_size>1024**2:raise ValueError('receipt unexpectedly large')
            record.update(statuses=json.loads(statuspath.read_text()),status_sha256=sha(statuspath),status_path=str(statuspath))
            resource=target/'runtime_resources.json'
            if resource.exists():record['resources']=json.loads(resource.read_text())
        env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
        env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[launch['owner']])
        codepath=Path(launch['stage'])/'run.py'
        if sha(codepath)!=launch['code_sha256']:raise ValueError('frozen launched code changed')
        proof=subprocess.run([sys.executable,'-c',SOURCE_PROOF,job,str(codepath)],env=env,capture_output=True,text=True,timeout=90)
        if proof.returncode:raise ValueError('saved source verification failed: '+job)
        record.update(json.loads(proof.stdout))
        record['verified']=all(s.get('status')=='derived' and not s.get('blocked_output_splits') for s in record['statuses'])
        record['claims_complete_training']=False
        record['verification_scope']='saved code and small scientific status; output matrices must be hash verified by consumer'
        (target/'verification.json').write_text(json.dumps(record,indent=1));results.append(record)
    payload={'utc':datetime.now(timezone.utc).isoformat(),'preflight_sha256':sha(prepath),'previous_sha256':sha(previous_path),'jobs':results,'claims_complete_training':False}
    (out/'verification.json').write_text(json.dumps(payload,indent=1))
    print(json.dumps([{'job':r['job'],'verified':r.get('verified'),'scientific_status':[s['status'] for s in r.get('statuses',[])]} for r in results]))

if __name__=='__main__':main()
