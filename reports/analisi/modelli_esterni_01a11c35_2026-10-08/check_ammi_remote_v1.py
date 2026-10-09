"""Read exact AMMI job status and identity; never push or fetch biological outputs."""
import argparse
import hashlib
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
from ammi_io_v4 import write


def safe_error(error):
    response=getattr(error,'response',None)
    result=dict(error_type=type(error).__name__,http_status=getattr(response,'status_code',None))
    if response is not None:
        try:
            body=response.json()
            message=body.get('message',body.get('error',None)) if isinstance(body,dict) else None
            if isinstance(message,str) and len(message)<2000:
                result['provider_message']=re.sub(r'https?://\S+','[URL removed]',message)[:500]
        except (ValueError,TypeError):pass
    return result


def check(prepared_path,out):
    prepared=json.loads(Path(prepared_path).read_text());owner,slug=prepared['slug'].split('/')
    if owner!='davidmaisterx':raise ValueError('unexpected owner')
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle')
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiGetKernelRequest
    service=KaggleApi();service.authenticate()
    result=dict(utc=datetime.now(timezone.utc).isoformat(),slug=prepared['slug'],read_only=True)
    result['listed_exact_match']=any(k.ref==prepared['slug'] for k in service.kernels_list(mine=True,search=slug,page_size=100))
    try:result['state']=str(service.kernels_status(prepared['slug']).status).split('.')[-1]
    except Exception as error:result.update(state='UNRESOLVED',**safe_error(error))
    if result['listed_exact_match']:
        request=ApiGetKernelRequest();request.user_name=owner;request.kernel_slug=slug
        with service.build_kaggle_client() as client:
            remote=client.kernels.kernels_api_client.get_kernel(request)
        raw=remote.blob.source.replace('\r\n','\n').encode()
        local=Path(prepared['code']['path']).read_bytes().replace(b'\r\n',b'\n')
        result.update(remote_code_LF_sha256=hashlib.sha256(raw).hexdigest(),
            remote_code_matches=raw==local,private=remote.metadata.is_private,
            enable_gpu=remote.metadata.enable_gpu,version=remote.metadata.current_version_number,
            machine_shape=str(remote.metadata.machine_shape))
        if not result['remote_code_matches'] or not result['private'] or not result['enable_gpu']:
            raise ValueError('remote code/privacy/GPU configuration differs')
    write(out,result);print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--prepared',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();check(a.prepared,a.out)
