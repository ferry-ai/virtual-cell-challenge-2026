"""Bounded read-only AMMI phase snapshot; no RNA, arrays, source or full logs saved."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import time
import requests
from collect_ammi_evidence_v1 import metadata_name
from ammi_io_v4 import write


def snapshot(prepared_path,out):
    prepared=json.loads(Path(prepared_path).read_text());ref=prepared['slug'];owner,slug=ref.split('/')
    if owner!='davidmaisterx':raise ValueError('unexpected account')
    for k in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(k,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle')
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiListKernelSessionOutputRequest,KaggleEnv
    service=KaggleApi();service.authenticate()
    result=dict(utc=datetime.now(timezone.utc).isoformat(),slug=ref,read_only=True,
        state=str(service.kernels_status(ref).status).split('.')[-1],metadata={},timing_events=[])
    def events(value):
        if isinstance(value,str):
            for line in value.splitlines():
                start=line.find('{"event": "ammi_phase_timing"')
                if start>=0:
                    try:
                        event=json.JSONDecoder().raw_decode(line[start:])[0]
                        allowed={k:event[k] for k in ('event','phase','status','seconds','started_utc','finished_utc','error_type') if k in event}
                        result['timing_events'].append(allowed)
                    except ValueError:pass
        elif isinstance(value,dict):
            for item in value.values():events(item)
        elif isinstance(value,list):
            for item in value:events(item)
    with service.build_kaggle_client() as client:
        token=None;seen=set()
        while True:
            request=ApiListKernelSessionOutputRequest();request.user_name=owner;request.kernel_slug=slug;request.page_size=200
            if token:request.page_token=token
            reply=client.kernels.kernels_api_client.list_kernel_session_output(request)
            events(reply.log or '')
            for item in reply.files or []:
                name=metadata_name(item.file_name,slug)
                if name is None:continue
                with requests.get(item.url,stream=True,timeout=(10,20)) as response:
                    response.raise_for_status();data=bytearray()
                    for block in response.iter_content(16384):
                        data.extend(block)
                        if len(data)>20_000_000:raise ValueError('metadata bound exceeded')
                value=json.loads(data)
                # Errors contain sanitized resolver messages, but do not persist
                # arbitrary text from an unknown provider/source in this snapshot.
                if name in ('ammi_failure.json','failure.json'):
                    value={k:value[k] for k in ('status','type','error_type','seconds','manifest_sha256') if k in value}
                result['metadata'][name]=value
            token=reply.next_page_token
            if not token:break
            if token in seen:raise ValueError('pagination repeated')
            seen.add(token)
        if result['state'] not in ('COMPLETE','ERROR'):
            http=client._http_client;http._init_session()
            base=http._endpoint if http._env==KaggleEnv.PROD else http._endpoint+'/api'
            headers=dict(http._session.headers);headers['Accept']='text/event-stream, */*';headers.pop('Content-Type',None)
            started=time.monotonic();size=0
            try:
                with http._session.get(base+'/v1/kernels/logs/stream/'+ref,stream=True,
                        headers=headers,auth=http._session.auth,timeout=(10,15)) as response:
                    response.raise_for_status()
                    for raw in response.iter_lines(chunk_size=256,decode_unicode=True):
                        if isinstance(raw,bytes):raw=raw.decode(errors='replace')
                        if raw:
                            size+=len(raw)
                            if size>200000:break
                            line=raw[5:].lstrip() if raw.startswith('data:') else raw
                            if line=='END_OF_LOG':break
                            try:events(json.loads(line))
                            except ValueError:events(line)
                        if time.monotonic()-started>20:break
            except Exception as error:result['live_log_read_error']=type(error).__name__
    result.update(utc_complete=datetime.now(timezone.utc).isoformat(),
        RNA_or_prediction_arrays_read=False,full_logs_saved=False,
        optimization_attested=('training_receipt.json' in result['metadata']
            or any(x.get('phase')=='fit' and x.get('status')=='COMPLETE' for x in result['timing_events'])))
    write(out,result)
    print(json.dumps(dict(slug=ref,state=result['state'],metadata=list(result['metadata']),
        timing_events=len(result['timing_events']),optimization_attested=result['optimization_attested'],
        live_log_read_error=result.get('live_log_read_error'))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for k in ('prepared','out'):p.add_argument('--'+k,required=True)
    a=p.parse_args();snapshot(a.prepared,a.out)
