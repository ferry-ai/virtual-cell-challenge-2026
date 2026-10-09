"""Fetch only frozen-bank evidence, without biological source arrays or logs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import requests
from esm2_closure_cloud_v1 import api,PREPARED,read,write,compact_error

NAMES={'results.json','status.json','per_target.csv','parity.json','consumption.json',
       'table_audit.json','runtime_versions.json','external_arms.json','common_support.json',
       'analysis_data_files.json','preflight.json','initial_resources.json'}

def collect(out,receipt):
    if out.exists() or receipt.exists():raise FileExistsError('fresh evidence destination required')
    service=api();prepared=read(PREPARED);bank=read(prepared['bank_prepared'])
    owner,slug=bank['slug'].split('/')
    state=str(service.kernels_status(bank['slug']).status).split('.')[-1]
    if state not in ('COMPLETE','ERROR'):raise ValueError('terminal bank required')
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    selected={};tokens=set();token=None
    while True:
        request=ApiListKernelSessionOutputRequest()
        request.user_name=owner;request.kernel_slug=slug;request.page_size=200
        if token:request.page_token=token
        with service.build_kaggle_client() as client:
            response=client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            if item.file_name in NAMES:
                if item.file_name in selected:raise ValueError('duplicate evidence output')
                selected[item.file_name]=item.url
        token=response.next_page_token
        if not token:break
        if token in tokens:raise ValueError('pagination cycle')
        tokens.add(token)
    required={'results.json','status.json','per_target.csv','parity.json','consumption.json','external_arms.json'}
    if state=='COMPLETE' and not required<=set(selected):raise ValueError('bank evidence missing')
    out.mkdir(parents=True)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),slug=bank['slug'],remote_state=state,
        output=str(out),files={},executor='MODELLI-ESTERNI',metrics_changed=False,
        raw_RNA_downloaded=False,private_urls_persisted=False)
    try:
        for name,url in sorted(selected.items()):
            path=out/name;digest=hashlib.sha256();size=0
            with requests.get(url,stream=True,timeout=(15,60)) as response:
                response.raise_for_status()
                with path.open('xb') as stream:
                    for block in response.iter_content(1<<20):
                        size+=len(block)
                        if size>100_000_000:raise ValueError('evidence file exceeds declared metadata bound')
                        stream.write(block);digest.update(block)
            report['files'][name]=dict(path=str(path),bytes=size,sha256=digest.hexdigest())
        report['status']='RETRIEVED_REQUIRES_SCIENTIFIC_READOUT'
    except Exception as error:
        report.update(status='INCOMPLETE',error=compact_error(error))
    write(receipt,report)
    print(json.dumps(dict(status=report['status'],files=len(report['files']))))

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();collect(a.out,a.receipt)
