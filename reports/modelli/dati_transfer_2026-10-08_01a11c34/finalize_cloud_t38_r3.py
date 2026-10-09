"""Verify the completed cloud upload and launch scoring for that same VCC entry."""
import hashlib
import json
import requests
from percorso import HERE,read,pin,sha,write_new,now
from prepare_t38_resume_r3 import FOLDER,PRIVATE
from cloud_t38_delivery_r2 import auth_context
from quick_generation_cloud import api_for_owner
from t38_submission import TRIAL,MODEL


def main():
    proof=read(FOLDER/'prepared.json');api=api_for_owner('davideferrante11')
    status=str(api.kernels_status(proof['slug']).status).split('.')[-1]
    if status!='COMPLETE':print(json.dumps(dict(status=status,entry_id=proof['entry_id'])));return 2
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest,ApiListKernelSessionOutputRequest
    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=proof['slug'].split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    digest=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    if digest!=proof['code']['sha256'] or not saved.metadata.is_private or saved.metadata.current_version_number!=1:
        raise ValueError('cloud uploader identity differs')
    req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=proof['slug'].split('/');req.page_size=100
    wanted={'upload_receipt.json','generation_manifest.json','packaging.json','manifest_48_package_prediction.json',
            'compact_diagnostics.json','generation_preflight.json','generation_stage45_manifest.json'}
    found={}
    while True:
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(req)
        for item in response.files or []:
            if item.file_name in wanted:found[item.file_name]=item.url
        if not response.next_page_token:break
        req.page_token=response.next_page_token
    if set(found)!=wanted:raise ValueError('upload evidence missing')
    dest=FOLDER/'completion_r1';dest.mkdir(exist_ok=False)
    for name,url in found.items():
        response=requests.get(url,timeout=60);response.raise_for_status();data=response.content
        if len(data)>2000000 or b'kaggleusercontent.com' in data or b'"upload_url"' in data:raise ValueError('sensitive/oversized receipt')
        json.loads(data)
        with (dest/name).open('xb') as out:out.write(data)
    from collect_t38_generation import verify_receipts
    manifest=verify_receipts(dest,proof);receipt=read(dest/'upload_receipt.json')
    if (receipt['entry_id']!=proof['entry_id'] or receipt['status']!='UPLOAD_VERIFIED'
            or not receipt['md5_verified'] or receipt['md5_local']!=receipt['md5_remote']
            or receipt['sha256']!=manifest['sha256'] or receipt['bytes_uploaded']!=manifest['bytes']):
        raise ValueError('cloud upload not verified')
    write_new(dest/'verification.json',dict(utc=now(),status='UPLOAD_VERIFIED',saved_code_matches=True,
        code_sha256=digest,job=proof['slug'],entry_id=receipt['entry_id'],product_sha256=manifest['sha256'],
        upload_finished_utc=receipt['utc_upload_verified'],product_downloaded_locally=False))
    for name in wanted:
        target=TRIAL/('t38_cloud_'+name)
        with target.open('xb') as out:out.write((dest/name).read_bytes())
    if (FOLDER/'scoring_launch.lock').exists() and (TRIAL/'submit_t38_cloud_result.json').exists():
        print(json.dumps(dict(status='FINAL_RECEIPTS_COLLECTED',entry_id=receipt['entry_id'],upload_finished_utc=receipt['utc_upload_verified'])))
        return 0
    # Server transitions are the same official CLI sequence, with no new entry.
    from vcc import api as vcc_api
    from vcc.lock import SubmitLock
    from vcc.config import config_dir
    auth,profile,endpoint,token=auth_context()
    created=read(PRIVATE/'created_private.json')
    if created['entry_id']!=receipt['entry_id']:raise ValueError('entry identity changed')
    lock=SubmitLock(config_dir()/'locks'/('submit-'+profile+'.lock'));lock.acquire()
    try:
        current=vcc_api.get_submission(endpoint,token,receipt['entry_id'])
        write_new(TRIAL/('status_'+receipt['entry_id']+'_before_launch.json'),current)
        if current.get('status') not in ('uploading','pending'):
            raise ValueError('entry already advanced; inspect before any scoring launch')
        with (FOLDER/'scoring_launch.lock').open('x') as f:f.write(now())
        transition=vcc_api.set_submission_status(endpoint,token,receipt['entry_id'],'launching')
        write_new(TRIAL/'t38_launching_response.json',transition)
        # Never mark failed on an ambiguous launch error or automatically retry.
        launched=vcc_api.launch_submission(endpoint,token,receipt['entry_id'],created['file_path'],nnz=receipt['nnz'])
        write_new(TRIAL/'t38_launch_response.json',launched)
        auth.clear_pending_upload(profile,receipt['entry_id'])
    finally:lock.release()
    result=dict(entry_id=receipt['entry_id'],file_path=created['file_path'],model_name=MODEL,
        is_final=created.get('is_final',False),bytes_uploaded=receipt['bytes_uploaded'],md5_verified=True,
        job_name=launched.get('job_name'),prepared_from=None,final_status=None,
        method='official CLI API functions and upload_file from private Kaggle runtime',
        upload_finished_utc=receipt['utc_upload_verified'])
    write_new(TRIAL/'submit_t38_cloud_result.json',result)
    write_new(TRIAL/('submit_'+receipt['entry_id']+'.json'),result)
    print(json.dumps(result));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('Cloud finalization failed: '+type(exc).__name__)
        raise SystemExit(1)
