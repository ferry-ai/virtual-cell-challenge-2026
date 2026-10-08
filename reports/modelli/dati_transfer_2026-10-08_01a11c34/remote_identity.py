"""Read one saved kernel identity in an account-isolated process."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from percorso import BANK

spec=importlib.util.spec_from_file_location('canonical',BANK/'percorso.py')
bank=importlib.util.module_from_spec(spec);spec.loader.exec_module(bank)
try:
    if '/' not in sys.argv[2]:
        saved=bank.saved_kernel(sys.argv[1],sys.argv[2])
    else:
        for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
        os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/bank.CONFIG[sys.argv[1]])
        from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest
        api=KaggleApi();api.authenticate();request=ApiGetKernelRequest()
        request.user_name,request.kernel_slug=sys.argv[2].split('/')
        with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(request)
    print(json.dumps(dict(source_sha256=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest(),
        version=saved.metadata.current_version_number,is_private=saved.metadata.is_private)))
except Exception as exc:
    response=getattr(exc,'response',None)
    print(str(exc)+((': '+response.text[:4000]) if response is not None else ''),file=sys.stderr)
    raise SystemExit(1)
