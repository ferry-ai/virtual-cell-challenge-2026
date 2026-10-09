"""Stop the exact current generation session on the user's explicit instruction."""
import json
import re
from urllib.parse import urlparse
from percorso import HERE,read,write_new,now
from quick_generation_cloud import api_for_owner

proof=read(HERE/'generation_recovery/r4/prepared.json')
api=api_for_owner(proof['owner'])
status=str(api.kernels_status(proof['slug']).status).split('.')[-1]
report=dict(utc=now(),job=proof['slug'],status_before=status,user_instruction='ferma tutto',new_jobs_or_submissions=False)
if status not in ('COMPLETE','ERROR','CANCELLED'):
    from kaggle.api.kaggle_api_extended import ApiDownloadKernelOutputRequest
    from kagglesdk.kernels.types.kernels_api_service import ApiCancelKernelSessionRequest
    req=ApiDownloadKernelOutputRequest();req.owner_slug,req.kernel_slug=proof['slug'].split('/');req.version_number=1
    with api.build_kaggle_client() as client:res=client.kernels.kernels_api_client.download_kernel_output(req)
    values=[v for v in vars(res).values() if isinstance(v,str)]
    ids=[]
    for value in values:
        ids.extend(re.findall(r'/download_zip/(\d+)',urlparse(value).path))
    if len(set(ids))!=1:
        report['cancel_confirmed']=False;report['reason']='no unambiguous session identifier in official redirect'
    else:
        req=ApiCancelKernelSessionRequest();req.kernel_session_id=int(ids[0])
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.cancel_kernel_session(req)
        report.update(session_id=int(ids[0]),cancel_error=response.error_message,cancel_requested=True)
        report['status_after']=str(api.kernels_status(proof['slug']).status).split('.')[-1]
else:report['already_terminal']=True
write_new(HERE/'stop_delivery_r1.json',report)
print(json.dumps(report))
