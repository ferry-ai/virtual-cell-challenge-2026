"""Retrieve only a small runtime receipt; bind it to saved code and source inputs."""
import hashlib,json,os,requests
from pathlib import Path
from datetime import datetime,timezone
from pipeline_state import HERE,CONFIG,sha
from preflight_slots_fast_v1 import call


def main():
    stage=HERE/'access_runtime_r1';job=json.loads((stage/'launch.json').read_text())['job']
    rc,text=call('davidmaisterx',['kernels','status',job])
    if rc or 'KernelWorkerStatus.COMPLETE' not in text:
        print(json.dumps({'complete':False,'status':text}));return
    out=stage/'verified';out.mkdir(exist_ok=False)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davidmaisterx'])
    for key in ('KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest,ApiListKernelSessionOutputRequest
    api=KaggleApi();api.authenticate();req=ApiGetKernelRequest();req.user_name,req.kernel_slug=job.split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    expected=(stage/'run.py').read_text()
    if saved.blob.source.replace('\r\n','\n')!=expected.replace('\r\n','\n'):
        raise ValueError('saved code differs beyond line endings')
    raw=None;token=None
    while True:
        listing=ApiListKernelSessionOutputRequest();listing.user_name,listing.kernel_slug=job.split('/')
        listing.page_size=100
        if token:listing.page_token=token
        with api.build_kaggle_client() as client:page=client.kernels.kernels_api_client.list_kernel_session_output(listing)
        for item in page.files or []:
            if item.file_name=='runtime_receipt.json':
                data=bytearray()
                with requests.get(item.url,stream=True,timeout=(20,30)) as response:
                    response.raise_for_status()
                    for b in response.iter_content(65536):
                        data.extend(b)
                        if len(data)>1<<20:raise ValueError('receipt too large')
                if raw is not None:raise ValueError('duplicate receipt')
                raw=bytes(data)
        token=page.next_page_token
        if not token:break
    if raw is None:raise ValueError('missing runtime receipt')
    receipt=json.loads(raw);prepared=json.loads((stage/'prepared.json').read_text())
    if (not receipt['complete'] or receipt['training_used'] or
        receipt['producer_input_manifest_sha256']!=prepared['sources']['params.json'] or
        not receipt['norman_reader_lineage_verified'] or
        set(receipt['ipsc_files_hash_checked'])!=set(prepared['params']['ipsc']['files'])):
        raise ValueError('runtime input proof incomplete')
    with api.build_kaggle_client() as client:after=client.kernels.kernels_api_client.get_kernel(req)
    if after.metadata.current_version_number!=saved.metadata.current_version_number or after.blob.source!=saved.blob.source:
        raise ValueError('saved version changed')
    (out/'runtime_receipt.json').open('xb').write(raw)
    result={'utc':datetime.now(timezone.utc).isoformat(),'job':job,
            'version':saved.metadata.current_version_number,'saved_source_sha256':hashlib.sha256(saved.blob.source.encode()).hexdigest(),
            'local_raw_code_sha256':sha(stage/'run.py'),'receipt_sha256':sha(out/'runtime_receipt.json'),
            'runtime_mount_hashes_and_norman_reader_lineage_verified':True,'fit_admitted':False,'training_used':False}
    (out/'verification.json').open('x').write(json.dumps(result,indent=1))
    print(json.dumps(result))


if __name__=='__main__':main()
