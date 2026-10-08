"""Verify native kernel sources from the actual destination account before dispatch."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from pie_adapter import sha256

CONFIG={'davideferrante11':'.kaggle-davideferrante11','davidmaisterx':'.kaggle','davideferante':'.kaggle-codex'}


def admissible(destination, source, is_private):
    return isinstance(is_private,bool) and (not is_private or source.split('/')[0] == destination)


def main(prepared_path,out):
    if out.exists():raise FileExistsError(out)
    prepared=json.loads(prepared_path.read_text())
    destination=prepared['slug'].split('/')[0]
    for name in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):
        os.environ.pop(name,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[destination])
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest
    api=KaggleApi();api.authenticate();checks=[]
    with api.build_kaggle_client() as client:
        for source in prepared['kernel_sources']:
            request=ApiGetKernelRequest();request.user_name,request.kernel_slug=source.split('/')
            try:
                saved=client.kernels.kernels_api_client.get_kernel(request)
                private=saved.metadata.is_private
                checks.append(dict(source=source,private=private,version=saved.metadata.current_version_number,
                    native_admissible=admissible(destination,source,private)))
                del saved
            except Exception as exc:
                checks.append(dict(source=source,native_admissible=False,error_type=type(exc).__name__))
    result=dict(utc=datetime.now(timezone.utc).isoformat(),destination=destination,
        prepared_sha256=sha256(prepared_path),status='PASS' if all(c['native_admissible'] for c in checks) else 'FAIL',
        sources=checks,output_chunk_access='verified later by runtime resolver',source_or_locators_printed=False)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=1)
    print(json.dumps(dict(status=result['status'],destination=destination,sources=len(checks),
                         rejected=[c['source'] for c in checks if not c['native_admissible']])))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.prepared,a.out)
