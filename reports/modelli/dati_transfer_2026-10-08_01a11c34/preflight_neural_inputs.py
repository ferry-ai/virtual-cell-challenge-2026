"""Read-only, account-isolated input access and recent-slot checks; no launches."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from percorso import HERE, now, pin, read, write_new
from cloud_campaign import CONFIG


def check(owner, prepared):
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiGetKernelRequest, ApiGetDatasetRequest
    api=KaggleApi();api.authenticate()
    result=dict(owner=owner,utc=now(),sources=[],observed=[],errors=[])
    try:
        refs=[k.ref for k in api.kernels_list(mine=True,page_size=20,sort_by='dateRun') if k.ref]
        def status(ref):
            try:return dict(ref=ref,state=str(api.kernels_status(ref).status).split('.')[-1])
            except Exception as exc:return dict(ref=ref,state='UNKNOWN',error=type(exc).__name__)
        with ThreadPoolExecutor(max_workers=4) as pool:
            result['observed']=list(pool.map(status,refs))
        result['active_or_unknown']=sum(x['state'] not in ('COMPLETE','ERROR','CANCELLED') for x in result['observed'])
    except Exception as exc:
        result.update(active_or_unknown=5,list_error=type(exc).__name__)
    sources=set()
    for job in prepared['jobs']:
        if job['slug'].split('/')[0]!=owner:continue
        metadata=read(job['metadata']['path'])
        for kind,field in [('kernel','kernel_sources'),('dataset','dataset_sources')]:
            sources.update((kind,ref) for ref in metadata[field])
    def source(item):
        kind,ref=item
        try:
            with api.build_kaggle_client() as client:
                if kind=='kernel':
                    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=ref.split('/')
                    meta=client.kernels.kernels_api_client.get_kernel(req).metadata
                else:
                    req=ApiGetDatasetRequest();req.owner_slug,req.dataset_slug=ref.split('/')
                    meta=client.datasets.dataset_api_client.get_dataset(req)
            private=meta.is_private
            return dict(kind=kind,ref=ref,private=private,version=meta.current_version_number,
                        accessible=True,native_admissible=(kind=='dataset' or private is False or ref.split('/')[0]==owner))
        except Exception as exc:
            return dict(kind=kind,ref=ref,accessible=False,native_admissible=False,
                        error=type(exc).__name__,http_status=getattr(getattr(exc,'response',None),'status_code',None))
    with ThreadPoolExecutor(max_workers=4) as pool:
        result['sources']=list(pool.map(source,sorted(sources)))
    result['utc_complete']=now()
    return result


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--out',type=Path);p.add_argument('--owner',choices=list(CONFIG));a=p.parse_args()
    prepared=read(a.prepared)
    if a.owner:
        try:print(json.dumps(check(a.owner,prepared)))
        except Exception as exc:print(json.dumps(dict(owner=a.owner,error=type(exc).__name__,active_or_unknown=5)))
        return
    if a.out.exists():raise FileExistsError(a.out)
    def child(owner):
        env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
        env.update(KAGGLE_CONFIG_DIR=str(Path.home()/CONFIG[owner]),PYTHONUTF8='1')
        try:
            run=subprocess.run([sys.executable,__file__,'--owner',owner,'--prepared',str(a.prepared)],
                env=env,capture_output=True,text=True,timeout=300)
            return json.loads(run.stdout)
        except Exception as exc:return dict(owner=owner,error=type(exc).__name__,active_or_unknown=5)
    observed=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(child,owner) for owner in CONFIG]):
            value=future.result();observed.append(value)
            print(json.dumps(dict(owner=value['owner'],active=value['active_or_unknown'],
                sources=len(value.get('sources',[])),rejected=sum(not x['native_admissible'] for x in value.get('sources',[])),
                error=value.get('error'))),flush=True)
    dispatcher=Path('G:/Il mio Drive/vcc2026/runs/jobs/dispatcher.log')
    colab=dict(live_verified=False)
    try:
        colab['accessible']=dispatcher.is_file()
        if colab['accessible']:colab['file_mtime_utc']=datetime.fromtimestamp(dispatcher.stat().st_mtime,timezone.utc).isoformat()
    except OSError as exc:colab.update(accessible=False,error=type(exc).__name__)
    result=dict(utc=now(),prepared=pin(a.prepared),accounts=observed,colab=colab,
        scope='20 most recent kernels per configured account; all mounts of prepared jobs',
        slot_limit_per_account=5,reserve_slots=1,quota_remaining='not exposed by this API check',
        CPU_RAM_disk='must be measured inside each destination runtime before extraction',
        remote_arrays_hashed=False,no_compute_launched=True)
    write_new(a.out,result)


if __name__=='__main__':main()
