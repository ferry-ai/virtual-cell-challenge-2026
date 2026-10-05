"""Recover only small scientific status/resource receipts of closed source jobs."""
import json,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

def main():
    dest=HERE/sys.argv[1];dest.mkdir(exist_ok=False)
    progress=json.loads((HERE/'sourcefits_launch_r1/progress_r1.json').read_text())
    complete=[r['job'] for r in progress['jobs'] if r['result'][0]==0 and 'COMPLETE' in r['result'][1]]
    def recover(job):
        target=dest/job.replace('/','__');target.mkdir()
        rc,_=call(job.split('/')[0],['kernels','output',job,'-p',str(target),'--file-pattern','job_status.json|runtime_resources.json'])
        status=target/'job_status.json'
        if rc or not status.is_file():return {'job':job,'verified':False,'reason':'status receipt unavailable','returncode':rc}
        if status.stat().st_size>1024**2:raise ValueError('unexpected status size')
        return {'job':job,'verified':True,'status_sha256':sha(status),'statuses':json.loads(status.read_text()),
                'resources':json.loads((target/'runtime_resources.json').read_text()) if (target/'runtime_resources.json').exists() else None}
    with ThreadPoolExecutor(3) as pool:result=list(pool.map(recover,complete))
    (dest/'verification.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'jobs':result},indent=1))
    print(json.dumps(result))

if __name__=='__main__':main()
