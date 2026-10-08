"""Inspect provider output availability without exposing download capabilities."""
import argparse
import json
from percorso import HERE, read, write_new, now
from quick_generation_cloud import api_for_owner

p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('label');a=p.parse_args()
folder=HERE/a.folder;proof=read(folder/'prepared.json');api=api_for_owner(proof['owner'])
from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
status=str(api.kernels_status(proof['slug']).status).split('.')[-1]
req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=proof['slug'].split('/');req.page_size=100
files=[]
while True:
    with api.build_kaggle_client() as client:res=client.kernels.kernels_api_client.list_kernel_session_output(req)
    files.extend(dict(name=f.file_name,bytes=getattr(f,'size',None)) for f in res.files or [])
    if not res.next_page_token:break
    req.page_token=res.next_page_token
report=dict(utc=now(),job=proof['slug'],status=status,files=files,arrays_downloaded=False)
write_new(folder/('output_availability_'+a.label+'.json'),report)
print(json.dumps(report))
