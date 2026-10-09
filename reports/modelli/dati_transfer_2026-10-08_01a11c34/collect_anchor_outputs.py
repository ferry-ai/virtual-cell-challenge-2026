"""Retrieve only finished AMMI aggregate effects/metadata; never raw or NTC RNA."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from percorso import HERE, ROOT, read, now, pin, sha, write_new
from cloud_campaign import CONFIG


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--prepared',type=Path,default=HERE/'neural_inputs_cloud_prepared_r4.json')
    p.add_argument('--metadata',type=Path);a=p.parse_args()
    if a.out.exists() or a.out.resolve().is_relative_to(ROOT):raise ValueError('new data-root destination required')
    job=next(j for j in read(a.prepared)['jobs'] if 'ammi-' in j['slug'])
    owner,slug=job['slug'].split('/')
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    import requests
    api=KaggleApi();api.authenticate()
    if str(api.kernels_status(job['slug']).status).split('.')[-1]!='COMPLETE':raise ValueError('not complete')
    metadata=a.metadata or HERE/'neural_launches/terminal_metadata'/owner/(slug+'_r2')/'anchors/complete.json'
    done=read(metadata);expected={'anchors/'+r['id']+'/effects_'+r['id']+'.npz':r['effects_sha256'] for r in done['requests']}
    allowed=set(expected)|{'anchors/'+r['id']+'/manifest.json' for r in done['requests']}|{'anchors/complete.json','initial_resources.json'}
    selected={};token=None;seen=set()
    while True:
        req=ApiListKernelSessionOutputRequest();req.user_name=owner;req.kernel_slug=slug;req.page_size=200
        if token:req.page_token=token
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(req)
        for item in response.files or []:
            name=item.file_name
            if name.startswith(slug+'/'):name=name[len(slug)+1:]
            if name in allowed:selected[name]=item.url
        token=response.next_page_token
        if not token:break
        if token in seen:raise ValueError('repeated page token')
        seen.add(token)
    if set(selected)!=allowed:raise ValueError('missing aggregate outputs: '+str(sorted(allowed-set(selected))))
    a.out.mkdir(parents=True,exist_ok=False);files=[]
    for name in sorted(selected):
        path=a.out/name;path.parent.mkdir(parents=True,exist_ok=True)
        h=hashlib.sha256();started=time.monotonic()
        with requests.get(selected[name],stream=True,timeout=(15,60)) as response:
            response.raise_for_status()
            with path.with_suffix(path.suffix+'.partial').open('xb') as out:
                for block in response.iter_content(1<<20):
                    if block:out.write(block);h.update(block)
        if name in expected and h.hexdigest()!=expected[name]:raise ValueError('aggregate output hash differs')
        path.with_suffix(path.suffix+'.partial').rename(path)
        files.append(dict(file=name,bytes=path.stat().st_size,sha256=h.hexdigest(),seconds=time.monotonic()-started))
        print(json.dumps(dict(file=name,bytes=path.stat().st_size,verified=name in expected)),flush=True)
    if sha(a.out/'anchors/complete.json')!=sha(metadata):raise ValueError('remote completion changed')
    write_new(a.receipt,dict(utc=now(),slug=job['slug'],status='PASS',out=str(a.out),files=files,
        completion=pin(a.out/'anchors/complete.json'),raw_or_NTC_RNA_downloaded=False,
        signed_urls_persisted=False,aggregate_effect_files_rehashed=len(expected)))


if __name__=='__main__':main()
