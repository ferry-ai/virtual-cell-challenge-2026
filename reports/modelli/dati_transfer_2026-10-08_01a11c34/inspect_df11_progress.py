"""One bounded, read-only snapshot of df11/r5 status, live logs and metadata."""
import argparse
from datetime import datetime, timezone
import json
import re
import time
import requests
from percorso import HERE, read, pin, write_new, now
from issue_ammi_private_access import authenticate

SOURCE='davideferrante11/dt-ntc-inputs-01a11c34-r5'


def clean(value):
    if isinstance(value,str):return re.sub(r'https?://[^\s"\'<>]+','[URL REDACTED]',value)
    if isinstance(value,list):return [clean(x) for x in value]
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k.lower() not in ('url','token','api_key','authorization')}
    return value


def snapshot(out, logs_timeout=15):
    api=authenticate('davideferrante11');owner,slug=SOURCE.split('/')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest,ApiListKernelSessionOutputRequest
    from kaggle.api.kaggle_api_extended import KaggleEnv
    result=dict(utc=now(),source=SOURCE,read_only=True,remote_jobs_launched=0,
                launch_intent=read(HERE/'neural_launches/r5/df11_ntc/launch_intent.json')['utc'],
                first_running_observation=read(HERE/'neural_launches/r5/df11_ntc/status_after_push.json')['utc'])
    state=api.kernels_status(SOURCE)
    result['state']=str(state.status).split('.')[-1]
    result['failure_message']=clean(state.failure_message)
    metadata={};listed=[];savedlog='';logs=[]
    with api.build_kaggle_client() as client:
        req=ApiGetKernelRequest();req.user_name=owner;req.kernel_slug=slug
        saved=client.kernels.kernels_api_client.get_kernel(req);meta=saved.metadata
        import hashlib
        source_hash=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
        expected_hash=read(HERE/'neural_launches/r5/df11_ntc/launch_intent.json')['code']['sha256']
        result['kernel_identity']=dict(version=meta.current_version_number,private=meta.is_private,
            ref=meta.ref,source_sha256=source_hash,source_matches_launch=source_hash==expected_hash,
            last_run_time=str(meta.last_run_time),machine_shape=meta.machine_shape,enable_gpu=meta.enable_gpu)
        if source_hash!=expected_hash:raise ValueError('remote source differs from launch')
        token=None;seen=set()
        try:
            while True:
                req=ApiListKernelSessionOutputRequest();req.user_name=owner;req.kernel_slug=slug
                api._set_paging(req,100,token)
                response=client.kernels.kernels_api_client.list_kernel_session_output(req)
                if response.log:savedlog=clean(response.log)[:100000]
                for item in response.files or []:
                    name=item.file_name
                    if name.startswith(slug+'/'):name=name[len(slug)+1:]
                    listed.append(name)
                    if name in ('progress.json','initial_resources.json','schema_preflight.json','campaign_complete.json','failure.json') or re.fullmatch(r'ntc/[^/]+/complete.json',name):
                        with requests.get(item.url,stream=True,timeout=(10,20)) as download:
                            download.raise_for_status();payload=bytearray()
                            for chunk in download.iter_content(16384):
                                payload.extend(chunk)
                                if len(payload)>500000:raise ValueError('metadata size limit')
                            metadata[name]=clean(json.loads(payload))
                token=response.next_page_token
                if not token:break
                if token in seen:raise ValueError('pagination repeated')
                seen.add(token)
        except Exception as exc:
            result['output_inventory_error']=type(exc).__name__
        # Mirror the installed Kaggle SDK's logs route, adding finite timeouts.
        http=client._http_client;http._init_session()
        base=http._endpoint if http._env==KaggleEnv.PROD else http._endpoint+'/api'
        url=base+'/v1/kernels/logs/stream/'+SOURCE
        headers=dict(http._session.headers);headers['Accept']='text/event-stream, */*';headers.pop('Content-Type',None)
        started=time.monotonic();size=0
        try:
            with http._session.get(url,stream=True,headers=headers,auth=http._session.auth,timeout=(10,logs_timeout)) as response:
                result['logs_http_status']=response.status_code
                result['logs_content_type']=response.headers.get('Content-Type')
                response.raise_for_status()
                for raw in response.iter_lines(chunk_size=256,decode_unicode=True):
                    if isinstance(raw,bytes):raw=raw.decode('utf-8',errors='replace')
                    if raw:
                        size+=len(raw)
                        if size>100000:result['logs_truncated']=True;break
                        line=raw[5:].lstrip() if raw.startswith('data:') else raw
                        if line=='END_OF_LOG':result['log_end_sentinel']=True;break
                        try:event=json.loads(line)
                        except ValueError:event=dict(data=line)
                        logs.append(clean(event))
                    if time.monotonic()-started>25:result['live_snapshot_limit_reached']=True;break
        except Exception as exc:
            result['logs_read_ended_with']=type(exc).__name__
        result['logs_observation_seconds']=time.monotonic()-started
    result.update(utc_complete=now(),listed_output_names=listed,metadata=metadata,
        completed_parts_observed=[name.split('/')[1] for name,d in metadata.items()
            if name.startswith('ntc/') and name.endswith('/complete.json') and d.get('status')=='COMPLETE'],
        saved_log=savedlog,live_log_events=logs,
        missing_live_files_do_not_imply_zero_completed_parts=True,
        RNA_arrays_downloaded=False,metadata_verified_for_training=False)
    write_new(out,result)
    print(json.dumps(dict(output=str(out),state=result['state'],listed_files=len(listed),
        metadata_files=len(metadata),live_log_events=len(logs),logs_read_ended_with=result.get('logs_read_ended_with'))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('out');p.add_argument('--logs-timeout',type=int,default=15);a=p.parse_args()
    try:snapshot(a.out,min(a.logs_timeout,40))
    except Exception as exc:
        print('Progress inspection failed: '+type(exc).__name__)
        import traceback
        print(json.dumps([dict(file=frame.filename,line=frame.lineno,function=frame.name)
            for frame in traceback.extract_tb(exc.__traceback__)]))
        raise SystemExit(1)
