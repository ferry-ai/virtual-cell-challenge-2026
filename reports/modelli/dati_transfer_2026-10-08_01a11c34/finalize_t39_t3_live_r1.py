"""Finalize the already-created T39 entry from authenticated upload+complete events."""
import argparse
import hashlib
import json
from pathlib import Path
from percorso import HERE, read, write_new, pin, now
from prepare_t39_t3_runtime_r2 import FOLDER, PRIVATE, TRIAL
from operate_t39_t3_r1 import consent
from cloud_t38_delivery_r2 import auth_context
from quick_generation_cloud import api_for_owner


def extract(stream,proof):
    report=read(stream)
    if report['source']!=proof['slug'] or report.get('http_status')!=200:
        raise ValueError('wrong authenticated stream source')
    records=[]
    for event in report['events']:
        for line in str(event.get('data','')).splitlines():
            try:record=json.loads(line)
            except (ValueError,TypeError):continue
            if isinstance(record,dict):records.append(record)
    receipts=[r for r in records if r.get('stage')=='upload_verified']
    completed=[r for r in records if r.get('stage')=='complete']
    if len(receipts)!=1 or len(completed)!=1:raise ValueError('unique verified upload and completion required')
    r,c=receipts[0],completed[0]
    if (r['entry_id']!=proof['entry_id'] or r['status']!='UPLOAD_VERIFIED'
        or not r['md5_verified'] or not r['md5_local'] or r['md5_local']!=r['md5_remote']
        or r['sha256']!=c['sha256'] or r['bytes_uploaded']!=c['bytes']
        or r['bytes_uploaded']<=0 or not 0<r['nnz']<=360000*18533
        or r['api_token_present'] or r['scoring_launched']):
        raise ValueError('upload evidence inconsistent')
    return r


def main(stream):
    consent();proof=read(FOLDER/'prepared.json');r=extract(stream,proof)
    api=api_for_owner('davideferrante11')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=proof['slug'].split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    digest=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    if digest!=proof['code']['sha256'] or not saved.metadata.is_private or saved.metadata.current_version_number!=1:
        raise ValueError('producer identity changed')
    write_new(TRIAL/'t39_t3_upload_receipt_live.json',dict(r,observed_utc=now(),
        producer_code_sha256=digest,stream=pin(stream),candidate=proof['candidate']))
    from vcc import api as vcc_api
    from vcc.lock import SubmitLock
    from vcc.config import config_dir
    auth,profile,endpoint,token=auth_context();created=read(PRIVATE/'created_private.json')
    if created['entry_id']!=r['entry_id']:raise ValueError('entry differs')
    lock=SubmitLock(config_dir()/'locks'/('submit-'+profile+'.lock'));lock.acquire()
    try:
        current=vcc_api.get_submission(endpoint,token,r['entry_id'])
        write_new(TRIAL/('status_'+r['entry_id']+'_before_launch.json'),current)
        if current.get('status') not in ('uploading','pending'):
            raise ValueError('entry already advanced; inspect without duplicate launch')
        with (FOLDER/'scoring_launch.lock').open('x') as f:f.write(now())
        transition=vcc_api.set_submission_status(endpoint,token,r['entry_id'],'launching')
        write_new(TRIAL/'t39_t3_launching_response.json',transition)
        launched=vcc_api.launch_submission(endpoint,token,r['entry_id'],created['file_path'],nnz=r['nnz'])
        write_new(TRIAL/'t39_t3_launch_response.json',launched)
        auth.clear_pending_upload(profile,r['entry_id'])
    finally:lock.release()
    result=dict(entry_id=r['entry_id'],file_path=created['file_path'],model_name=proof['model_name'],
        is_final=created.get('is_final',False),bytes_uploaded=r['bytes_uploaded'],md5_verified=True,
        sha256=r['sha256'],job_name=launched.get('job_name'),prepared_from=None,final_status=None,
        method='official CLI API functions and authenticated private cloud upload receipt',
        upload_finished_utc=r['utc_upload_verified'])
    write_new(TRIAL/'submit_t39_t3_cloud_result.json',result)
    write_new(TRIAL/('submit_'+r['entry_id']+'.json'),result)
    server=vcc_api.get_submission(endpoint,token,r['entry_id'])
    write_new(TRIAL/('status_'+r['entry_id']+'_after_launch.json'),server)
    write_new(FOLDER/'server_receipt_obtained.json',dict(utc=now(),status='SERVER_RECEIPT_OBTAINED',
        entry_id=r['entry_id'],server_status=server.get('status'),submission=pin(TRIAL/'submit_t39_t3_cloud_result.json'),
        receipt=pin(TRIAL/('status_'+r['entry_id']+'_after_launch.json'))))
    print(json.dumps(dict(entry_id=r['entry_id'],server_status=server.get('status'),bytes_uploaded=r['bytes_uploaded'],sha256=r['sha256'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stream',type=Path);a=p.parse_args()
    try:main(a.stream)
    except Exception as exc:
        print('T39 finalization stopped: '+type(exc).__name__)
        raise SystemExit(1)
