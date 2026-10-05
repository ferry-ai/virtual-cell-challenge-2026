"""Check cross-account output listing access without downloads or sharing changes."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from pipeline_state import CONFIG


def worker(job):
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiListKernelSessionOutputRequest
    api=KaggleApi();api.authenticate();q=ApiListKernelSessionOutputRequest()
    q.user_name,q.kernel_slug=job.split('/');q.page_size=1
    try:
        with api.build_kaggle_client() as client:
            result=client.kernels.kernels_api_client.list_kernel_session_output(q)
        return {'job':job,'output_listing_access':True,'files_returned':len(result.files or [])}
    except Exception as error:
        return {'job':job,'output_listing_access':False,'error_type':type(error).__name__,
                'http_status':getattr(getattr(error,'response',None),'status_code',None)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--account',choices=CONFIG,required=True)
    p.add_argument('--jobs',nargs='+',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();results=[]
    for job in a.jobs:
        r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',job],
            env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[a.account])},
            capture_output=True,encoding='utf-8',errors='replace',timeout=60)
        if r.returncode:
            raise RuntimeError('access probe process failed')
        results.append(json.loads(r.stdout))
    result={'utc':datetime.now(timezone.utc).isoformat(),'account':a.account,'jobs':results,
            'runtime_mount_verified':False,'downloads':0,'sharing_changes':False}
    a.out.open('x').write(json.dumps(result,indent=1));print(json.dumps(result))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        print(json.dumps(worker(sys.argv[2])))
    else:
        main()
