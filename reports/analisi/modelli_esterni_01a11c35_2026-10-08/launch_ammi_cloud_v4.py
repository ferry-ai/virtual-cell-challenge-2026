"""Dispatch exactly one prepared AMMI fit after fresh mount/slot/GPU checks."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256
from check_ammi_remote_v1 import safe_error

def read(p):return json.loads(Path(p).read_text())
def launch(prepared_path,access_preflight,quota_preflight,out):
    prepared=read(prepared_path);access=read(access_preflight);quota=read(quota_preflight)
    owner=prepared['slug'].split('/')[0]
    if owner!='davidmaisterx' or not prepared['private']:raise ValueError('authorized private account required')
    for pre in (access,quota):
        if (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()>900:
            raise ValueError('fresh preflight required')
    state=next(a for a in access['accounts'] if a['owner']==owner)
    if state['active_or_unknown']>=access['slot_limit_per_account']-access.get('reserve_slots',1):
        raise ValueError('no unreserved runtime slot')
    if not state['sources'] or any(not s['native_admissible'] for s in state['sources']):
        raise ValueError('native mount access incomplete')
    gpu=next(a for a in quota['accounts'] if a['owner']==owner)
    if gpu.get('GPU_unreserved_seconds',0)<=0 or gpu.get('pay_to_scale_enabled'):
        raise ValueError('free GPU quota not established without purchases')
    meta=read(checked(prepared['metadata']));checked(prepared['code'])
    if meta['id']!=prepared['slug'] or meta['is_private'] is not True or meta['enable_gpu'] is not True:
        raise ValueError('private CUDA metadata differs')
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle')
    from kaggle.api.kaggle_api_extended import KaggleApi
    service=KaggleApi();service.authenticate()
    if any(k.ref==prepared['slug'] for k in service.kernels_list(mine=True,search=prepared['slug'].split('/')[1],page_size=100)):
        raise ValueError('job exists; inspect status instead of duplicate push')
    write(str(out)+'.intent.json',dict(slug=prepared['slug'],code_sha256=prepared['code']['sha256'],
        metadata_sha256=prepared['metadata']['sha256'],access_preflight_sha256=sha256(access_preflight),
        quota_preflight_sha256=sha256(quota_preflight),private=True,gpu=True))
    with Path(str(out)+'.lock').open('x') as stream:stream.write(prepared['slug'])
    try:
        result=service.kernels_push(prepared['stage'])
        error=getattr(result,'error',None)
        response=dict(utc=datetime.now(timezone.utc).isoformat(),slug=prepared['slug'],accepted=not bool(error),
            provider_error=str(error) if error else None)
        if not error:response['state']=str(service.kernels_status(prepared['slug']).status).split('.')[-1]
    except Exception as error:
        response=dict(utc=datetime.now(timezone.utc).isoformat(),slug=prepared['slug'],accepted='unknown',
            **safe_error(error),
            next_action='inspect exact remote state before any retry')
    write(out,response);print(json.dumps(response))

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('prepared','access-preflight','quota-preflight','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();launch(a.prepared,a.access_preflight,a.quota_preflight,a.out)
