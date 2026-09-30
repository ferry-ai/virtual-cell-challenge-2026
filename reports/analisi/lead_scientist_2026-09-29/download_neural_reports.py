"""Fetch bounded small reports from the SDK's static output listing, without signed URLs in logs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kernel',choices=['davidmaisterx/vcc-lead-neural-sources-r1','davidmaisterx/vcc-lead-neural-seed1-r1',
                                      'davidmaisterx/vcc-lead-neural-cluster0-r1'],required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    import requests
    api=KaggleApi();api.authenticate()
    args.out.mkdir(parents=True)
    result={'started_utc':datetime.now(timezone.utc).isoformat(),'kernel':args.kernel,'files':[],
            'large_outputs_preserved_remotely':[],'method':'installed SDK static-output service, not kernels-list-files'}
    total=0;token=None
    try:
        with api.build_kaggle_client() as client:
            while True:
                request=ApiListKernelSessionOutputRequest()
                request.user_name,request.kernel_slug=args.kernel.split('/')
                api._set_paging(request,200,token)
                response=client.kernels.kernels_api_client.list_kernel_session_output(request)
                if token is None and response.log:
                    (args.out/'kernel_static.log').write_text(response.log,encoding='utf-8')
                for item in response.files or []:
                    name=item.file_name
                    pure=PurePosixPath(name.replace('\\','/'))
                    if pure.is_absolute() or '..' in pure.parts or ':' in name:
                        raise ValueError('Unsafe output path')
                    if pure.suffix.lower() not in {'.json','.csv','.log','.txt'}:
                        if pure.suffix.lower() in {'.npz','.pt'}:
                            result['large_outputs_preserved_remotely'].append(name)
                        continue
                    target=args.out/Path(*pure.parts)
                    target.parent.mkdir(parents=True,exist_ok=True)
                    size=0;digest=hashlib.sha256()
                    try:
                        with requests.get(item.url,stream=True,timeout=60) as download:
                            if download.status_code != 200:
                                raise RuntimeError(f'HTTP {download.status_code} downloading {name}')
                            with target.open('xb') as stream:
                                for block in download.iter_content(chunk_size=1024*1024):
                                    size+=len(block);total+=len(block)
                                    if size>10_000_000 or total>100_000_000:
                                        raise ValueError('Small-report byte bound exceeded')
                                    digest.update(block);stream.write(block)
                    except requests.RequestException:
                        raise RuntimeError(f'Network failure downloading named output {name}; signed URL omitted') from None
                    result['files'].append({'name':name,'bytes':size,'sha256':digest.hexdigest()})
                token=response.next_page_token
                if not token:
                    break
        result['complete']=True
    finally:
        result['finished_utc']=datetime.now(timezone.utc).isoformat()
        result['downloaded_bytes']=total
        (args.out/'download_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(result['files']),'bytes':total,'large_outputs_retained':len(result['large_outputs_preserved_remotely']),
                      'complete':result.get('complete',False)}))


if __name__=='__main__':
    main()
