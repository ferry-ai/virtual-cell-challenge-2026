"""Finish the same VCC entry from an authenticated live cloud upload receipt."""
import argparse
import hashlib
import json
from pathlib import Path
from percorso import read,write_new,now
from cloud_t38_delivery import FOLDER,PRIVATE,auth_context
from quick_generation_cloud import api_for_owner
from t38_submission import TRIAL,MODEL


def main(stream):
    proof=read(FOLDER/'prepared.json')
    events=[]
    for raw in stream.read_text(encoding='utf-8').splitlines():
        event=json.loads(raw)
        for line in str(event.get('data','')).splitlines():
            try:record=json.loads(line)
            except (ValueError,TypeError):continue
            if isinstance(record,dict):events.append(record)
    receipts=[x for x in events if x.get('stage')=='upload_verified']
    packages=[x for x in events if x.get('stage')=='package_verified']
    if len(receipts)!=1 or len(packages)!=1:raise ValueError('unique live upload evidence required')
    receipt=receipts[0];package=packages[0]
    if (receipt['entry_id']!=proof['entry_id'] or receipt['status']!='UPLOAD_VERIFIED'
            or not receipt['md5_verified'] or receipt['md5_local']!=receipt['md5_remote']
            or receipt['sha256']!=package['sha256'] or receipt['bytes_uploaded']!=package['bytes']
            or receipt['nnz']!=2086912955):raise ValueError('live upload identity differs')
    api=api_for_owner('davideferrante11')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=proof['slug'].split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    digest=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    if digest!=proof['code']['sha256'] or not saved.metadata.is_private or saved.metadata.current_version_number!=1:
        raise ValueError('live producer identity differs')
    write_new(TRIAL/'t38_cloud_upload_receipt_live.json',dict(receipt,producer_code_sha256=digest,observed_utc=now()))
    from vcc import api as vcc_api
    from vcc.lock import SubmitLock
    from vcc.config import config_dir
    auth,profile,endpoint,token=auth_context();created=read(PRIVATE/'created_private.json')
    if created['entry_id']!=receipt['entry_id']:raise ValueError('wrong entry')
    lock=SubmitLock(config_dir()/'locks'/('submit-'+profile+'.lock'));lock.acquire()
    try:
        current=vcc_api.get_submission(endpoint,token,receipt['entry_id'])
        write_new(TRIAL/('status_'+receipt['entry_id']+'_before_launch.json'),current)
        if current.get('status') not in ('uploading','pending'):raise ValueError('entry already advanced')
        with (FOLDER/'scoring_launch.lock').open('x') as f:f.write(now())
        write_new(TRIAL/'t38_launching_response.json',vcc_api.set_submission_status(endpoint,token,receipt['entry_id'],'launching'))
        launched=vcc_api.launch_submission(endpoint,token,receipt['entry_id'],created['file_path'],nnz=receipt['nnz'])
        write_new(TRIAL/'t38_launch_response.json',launched)
        auth.clear_pending_upload(profile,receipt['entry_id'])
    finally:lock.release()
    result=dict(entry_id=receipt['entry_id'],file_path=created['file_path'],model_name=MODEL,
        is_final=created.get('is_final',False),bytes_uploaded=receipt['bytes_uploaded'],md5_verified=True,
        job_name=launched.get('job_name'),prepared_from=None,final_status=None,
        method='official CLI API functions; verified live cloud upload receipt',
        upload_finished_utc=receipt['utc_upload_verified'])
    write_new(TRIAL/'submit_t38_cloud_result.json',result)
    write_new(TRIAL/('submit_'+receipt['entry_id']+'.json'),result)
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stream',type=Path);a=p.parse_args()
    try:main(a.stream)
    except Exception as exc:
        print('Live finalization failed: '+type(exc).__name__);raise SystemExit(1)
