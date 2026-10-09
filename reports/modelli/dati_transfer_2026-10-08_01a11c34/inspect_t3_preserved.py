"""Read-only inventory and small receipts for the stopped T3 output; no RNA download."""
import json
import os
from pathlib import Path
import requests
from percorso import HERE, now, read, write_new, pin
from cloud_campaign import CONFIG

owner='davideferrante11';slug='dt-t3-generate-01a11c34-r5'
for k in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(k,None)
os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest
api=KaggleApi();api.authenticate()
state=str(api.kernels_status(owner+'/'+slug).status).split('.')[-1]
files=[];token=None;selected={};allowed={'failure.json','compact_diagnostics.json','salvage.json',
    'recovery.json','generation_stage45_manifest.json','generation_manifest.json','packaging.json','generation_preflight.json'}
while True:
    req=ApiListKernelSessionOutputRequest();req.user_name=owner;req.kernel_slug=slug;req.page_size=100
    if token:req.page_token=token
    with api.build_kaggle_client() as c:response=c.kernels.kernels_api_client.list_kernel_session_output(req)
    for item in response.files or []:
        files.append(item.file_name)
        if item.file_name.split('/')[-1] in allowed:selected[item.file_name]=item.url
    token=response.next_page_token
    if not token:break
out=HERE/'t3_preserved_metadata_r1';out.mkdir(exist_ok=False)
receipts=[]
for name,url in selected.items():
    if '..' in Path(name).parts or Path(name).is_absolute():raise ValueError('unsafe output name')
    path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
    with requests.get(url,timeout=(15,60),stream=True) as response:
        response.raise_for_status();content=bytearray()
        for block in response.iter_content(65536):
            content.extend(block)
            if len(content)>1_000_000:raise ValueError('receipt too large')
    json.loads(content);path.write_bytes(content);receipts.append(pin(path))
write_new(HERE/'t3_preserved_inventory_r1.json',dict(utc=now(),slug=owner+'/'+slug,status=state,
    output_files=files,receipts=receipts,raw_or_generated_cells_downloaded=False,
    numerical_output_rehashed=False,new_fit_or_generation=False,new_upload=False))
print(json.dumps(dict(state=state,files=len(files),receipts=len(receipts),
    possible_cells=[n for n in files if n.endswith(('.h5ad','.vcc','.zst'))])))
