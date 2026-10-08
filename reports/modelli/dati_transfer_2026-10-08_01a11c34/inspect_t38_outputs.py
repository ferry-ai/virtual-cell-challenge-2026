"""List output identities only; never print signed URLs or download arrays."""
import json
from quick_generation_cloud import api_for_owner
from percorso import HERE, write_new, now
api=api_for_owner('davideferrante11')
from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
request=ApiListKernelSessionOutputRequest()
request.user_name='davideferrante11';request.kernel_slug='dt-t3-generate-01a11c34-r2';request.page_size=100
files=[]
while True:
    with api.build_kaggle_client() as client: response=client.kernels.kernels_api_client.list_kernel_session_output(request)
    for item in response.files or []: files.append(dict(name=item.file_name,bytes=getattr(item,'size',None)))
    if not response.next_page_token:break
    request.page_token=response.next_page_token
report=dict(utc=now(),files=files,prediction_files=[x for x in files if x['name'].endswith(('.h5ad','.vcc'))],arrays_downloaded=False)
write_new(HERE/'generation_recovery/r1/output_inventory_after_failure.json',report)
print(json.dumps(report))
