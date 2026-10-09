"""Read configured account GPU quotas and current sessions, without launching."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from ammi_io_v4 import write

CONFIG={'davideferrante11':'.kaggle-davideferrante11','davidmaisterx':'.kaggle','davideferante':'.kaggle-codex'}
def check(owner):
    from kaggle.api.kaggle_api_extended import KaggleApi
    service=KaggleApi();service.authenticate()
    quota=service.quota_view();gpu=quota.gpu_quota
    result=dict(owner=owner,utc=datetime.now(timezone.utc).isoformat(),
        GPU_total_seconds=gpu.total_time_allowed.total_seconds(),GPU_used_seconds=gpu.time_used.total_seconds(),
        GPU_reserved_seconds=gpu.time_reserved.total_seconds(),pay_to_scale_enabled=gpu.is_pay_to_scale_enabled,
        quota_refresh=quota.quota_refresh_time.isoformat(),scope='20 latest jobs plus known active producer')
    refs={k.ref for k in service.kernels_list(mine=True,page_size=20,sort_by='dateRun') if k.ref}
    if owner=='davideferrante11':refs.add(owner+'/dt-ntc-inputs-01a11c34-r5')
    def status(ref):
        try:return dict(ref=ref,status=str(service.kernels_status(ref).status).split('.')[-1])
        except Exception as error:return dict(ref=ref,status='UNKNOWN',error=type(error).__name__)
    with ThreadPoolExecutor(max_workers=4) as pool:result['jobs']=list(pool.map(status,sorted(refs)))
    result['active_or_unknown']=sum(x['status'] not in ('COMPLETE','ERROR','CANCELLED') for x in result['jobs'])
    result['GPU_remaining_seconds']=max(0,result['GPU_total_seconds']-result['GPU_used_seconds'])
    result['GPU_unreserved_seconds']=max(0,result['GPU_remaining_seconds']-result['GPU_reserved_seconds'])
    return result

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--owner',choices=list(CONFIG));p.add_argument('--out');a=p.parse_args()
    if a.owner:
        try:result=check(a.owner)
        except Exception as error:result=dict(owner=a.owner,error=type(error).__name__,GPU_remaining_seconds=None)
        print(json.dumps(result));return
    def child(owner):
        env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
        env.update(KAGGLE_CONFIG_DIR=str(Path.home()/CONFIG[owner]),PYTHONUTF8='1')
        run=subprocess.run([sys.executable,__file__,'--owner',owner],env=env,capture_output=True,text=True,timeout=300)
        return json.loads(run.stdout)
    with ThreadPoolExecutor(max_workers=3) as pool:accounts=list(pool.map(child,CONFIG))
    result=dict(utc=datetime.now(timezone.utc).isoformat(),accounts=accounts,no_compute_launched=True,
        runtime_RAM_disk_CPU_CUDA='must be measured inside each actual job before training',
        input_access='separate DATI plan and final mount preflight required')
    write(a.out,result)
    print(json.dumps([dict(owner=x['owner'],GPU_remaining_seconds=x.get('GPU_remaining_seconds'),
                         active_or_unknown=x.get('active_or_unknown'),error=x.get('error')) for x in accounts]))

if __name__=='__main__':main()
