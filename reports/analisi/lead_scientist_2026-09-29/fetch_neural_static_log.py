"""Read static kernel session output/log through the installed SDK, never stream."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kernel',choices=['davidmaisterx/vcc-lead-neural-sources-r1','davidmaisterx/vcc-lead-neural-seed1-r1'],required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    api=KaggleApi()
    api.authenticate()
    with api.build_kaggle_client() as client:
        request=ApiListKernelSessionOutputRequest()
        request.user_name,request.kernel_slug=args.kernel.split('/')
        api._set_paging(request,200,None)
        response=client.kernels.kernels_api_client.list_kernel_session_output(request)
    log=response.log or ''
    args.out.mkdir(parents=True)
    (args.out/'static.log').write_text(log,encoding='utf-8')
    evidence={'observed_utc':datetime.now(timezone.utc).isoformat(),'kernel':args.kernel,
              'output_names':[item.file_name for item in response.files or []],
              'next_page_available':bool(response.next_page_token),'log_bytes':len(log.encode()),
              'log_sha256':hashlib.sha256(log.encode()).hexdigest(),'no_stream_or_restart':True}
    (args.out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence))


if __name__=='__main__':
    main()
