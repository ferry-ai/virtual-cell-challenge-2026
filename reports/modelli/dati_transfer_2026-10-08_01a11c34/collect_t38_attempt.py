"""Read only terminal metadata and sanitized logs from a named delivery attempt."""
import argparse
import json
import re
import requests
from percorso import HERE,read,write_new,now
from quick_generation_cloud import api_for_owner


def main(revision,label):
    folder=HERE/'cloud_delivery'/revision;proof=read(folder/'prepared.json')
    api=api_for_owner(proof['owner']);state=str(api.kernels_status(proof['slug']).status).split('.')[-1]
    if state not in ('COMPLETE','ERROR','CANCELLED'):
        print(json.dumps(dict(state=state)));return
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
    request=ApiListKernelSessionOutputRequest();request.user_name,request.kernel_slug=proof['slug'].split('/')
    request.page_size=100
    names=[];metadata={};log='';seen=set()
    allowed={'delivery_failure.json','delivery_resource_preflight.json','packaging.json','upload_receipt.json',
        'generation_manifest.json','manifest_48_package_prediction.json'}
    while True:
        with api.build_kaggle_client() as client:r=client.kernels.kernels_api_client.list_kernel_session_output(request)
        if r.log:log=re.sub(r'https?://[^\s"<>]+','[URL REDACTED]',r.log)
        for item in r.files or []:
            name=item.file_name
            if name.startswith(request.kernel_slug+'/'):name=name[len(request.kernel_slug)+1:]
            names.append(name)
            if name in allowed:
                with requests.get(item.url,stream=True,timeout=(10,30)) as response:
                    response.raise_for_status();data=bytearray()
                    for chunk in response.iter_content(16384):
                        data.extend(chunk)
                        if len(data)>1000000:raise ValueError('receipt exceeds limit')
                    if b'"upload_url"' in data or b'kaggleusercontent.com' in data:raise ValueError('private locator in receipt')
                    metadata[name]=json.loads(data)
        if not r.next_page_token:break
        if r.next_page_token in seen:raise ValueError('pagination repeated')
        seen.add(r.next_page_token);request.page_token=r.next_page_token
    report=dict(utc=now(),state=state,job=proof['slug'],entry_id=proof['entry_id'],metadata=metadata,
                output_names=names,log=log,numerical_arrays_downloaded=False)
    write_new(folder/('terminal_'+label+'.json'),report)
    try:events=json.loads(log)
    except ValueError:events=[]
    important=[e for e in events if any(s in e.get('data','') for s in (
        '"stage"','Traceback','Error:','REFUSING','sha256','payload matches','validator'))]
    print(json.dumps(dict(state=state,metadata=metadata,important_events=important[-12:]),ensure_ascii=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('revision');p.add_argument('label');a=p.parse_args()
    try:main(a.revision,a.label)
    except Exception as exc:
        print('Attempt collection failed: '+type(exc).__name__);raise SystemExit(1)
