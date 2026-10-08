"""Read output filenames only; never print signed download URLs."""
import json
import os
from pathlib import Path
import sys
from cloud_campaign import CONFIG
from percorso import now,write_new


def main(owner,slug,out):
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiListKernelSessionOutputRequest
    api=KaggleApi();api.authenticate();token=None;files=[]
    with api.build_kaggle_client() as client:
        while True:
            request=ApiListKernelSessionOutputRequest();request.user_name,request.kernel_slug=slug.split('/')
            api._set_paging(request,100,token)
            response=client.kernels.kernels_api_client.list_kernel_session_output(request)
            files.extend(item.file_name for item in response.files or []);token=response.next_page_token
            if not token:break
    write_new(out,dict(utc=now(),login_account=owner,producer=slug,files=files,downloaded=False))
    print(json.dumps(dict(files=len(files),cache_files=[f for f in files if 'cache' in f])))


if __name__=='__main__':main(sys.argv[1],sys.argv[2],Path(sys.argv[3]))
