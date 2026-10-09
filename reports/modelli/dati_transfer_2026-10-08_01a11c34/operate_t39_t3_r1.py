"""Scoped T39 entry creation and one private CPU launch; never retry ambiguous mutations."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from percorso import HERE, DATA, ROOT, read, pin, sha, write_new, now
from prepare_t39_t3_runtime_r2 import FOLDER, PRIVATE, SLUG, TRIAL
from quick_generation_cloud import api_for_owner
from cloud_t38_delivery_r2 import auth_context


def consent():
    path=HERE/'t39_t3_private_egress_authorized_r1.json';a=read(path)
    if (not a['authorized'] or not a['original_human_response_read_directly']
            or a['source_user_message_id']!='01a122d7-66a2-7250-9855-8fb7eac55be2'
            or a['destination_job']!=SLUG
            or a['candidate_sha256']!='577a5a56a57df6a2ba07beead6217a7274ad639e85e8be780d942c1c7152094b'
            or not a['single_VCC_upload_capability_authorized']):
        raise ValueError('exact consent absent')
    return path


def fresh_slots():
    path=HERE/'t39_t3_slots_r2.json';s=read(path)
    if (datetime.now(timezone.utc)-datetime.fromisoformat(s['utc'])).total_seconds()>900:
        raise ValueError('slot snapshot stale')
    if s['active']['davideferrante11']>=4:raise ValueError('no unreserved CPU slot')
    return path,s


def create_entry():
    authorization=consent();slot_path,slots=fresh_slots()
    proof=read(FOLDER/'draft_prepared.json')
    for k in ('code','params','metadata','prediction','artifact_pin','submission_texts','candidate'):
        if sha(proof[k]['path'])!=proof[k]['sha256']:raise ValueError('draft input changed')
    if not read(HERE/'t39_t3_dataset_uploaded_r1.json')['accepted']:raise ValueError('input upload absent')
    api=api_for_owner('davideferrante11')
    from kaggle.api.kaggle_api_extended import ApiGetDatasetRequest
    params=read(proof['params']['path']);access=[]
    for source in read(proof['metadata']['path'])['dataset_sources']:
        req=ApiGetDatasetRequest();req.owner_slug,req.dataset_slug=source.split('/')
        with api.build_kaggle_client() as client:meta=client.datasets.dataset_api_client.get_dataset(req)
        listing=api.dataset_list_files(source,page_size=100)
        if listing.error_message or listing.next_page_token:raise ValueError('unexpected dataset listing')
        sizes={f.name:f.total_bytes for f in listing.files}
        if 't39-t3-e2' in source:
            if not meta.is_private or sizes.get('T3_E2_fallback.npz')!=19812145:
                raise ValueError('candidate private dataset differs')
        elif any(sizes.get(n)!=b for n,b in params['controls']['bytes'].items()):
            raise ValueError('official controls missing')
        access.append(dict(source=source,private=meta.is_private,version=meta.current_version_number,files=sizes))
    write_new(FOLDER/'access_preflight.json',dict(utc=now(),status='PASS_METADATA',sources=access,
        runtime_hashes_and_resources_required=True,slots=pin(slot_path)))
    from vcc import api as vcc_api
    from vcc.submit import check_no_inflight,_validated_resume
    from vcc.lock import SubmitLock
    from vcc.config import config_dir
    auth,profile,endpoint,token=auth_context()
    lock=SubmitLock(config_dir()/'locks'/('submit-'+profile+'.lock'));lock.acquire()
    try:
        check_no_inflight(endpoint,token,pending=auth.list_pending_uploads(profile))
        limits=vcc_api.get_limits(endpoint,token)
        if limits.get('limit_reached'):raise ValueError('VCC daily limit reached')
        write_new(FOLDER/'entry_create_intent.json',dict(utc=now(),authorization=pin(authorization),
            prediction=proof['prediction'],artifact_pin=proof['artifact_pin'],model_name=proof['model_name'],
            private_job=SLUG,one_entry_only=True))
        created=vcc_api.create_submission(endpoint,token,model_name=proof['model_name'],
            description=proof['description'],file_name='prediction_t39_T3_E2.vcc',file_type='application/x-tar')
        write_new(PRIVATE/'created_private.json',created)
        resume=dict(created,local_path=str(DATA/'submissions/t39_t3_e2_2026-10-10/prediction_t39_T3_E2.vcc'),
            model_name=proof['model_name'],prepared_from=None)
        _validated_resume(resume);auth.save_pending_upload(profile,created['entry_id'],resume)
    finally:lock.release()
    write_new(TRIAL/'submit_t39_t3_started.json',dict(utc=now(),entry_id=created['entry_id'],
        model_name=proof['model_name'],method='official VCC API and private cloud single-object uploader',
        candidate=proof['candidate'],authorization=pin(authorization),account_token_transferred=False))
    print(json.dumps(dict(entry_id=created['entry_id'],status='ENTRY_CREATED_UPLOAD_PENDING')))


def launch():
    authorization=consent();slot_path,slots=fresh_slots();proof=read(FOLDER/'prepared.json')
    if proof['draft'] or proof['entry_id']=='DRAFT_NOT_CREATED':raise ValueError('draft cannot launch')
    for k in ('code','params','metadata','prediction','artifact_pin','submission_texts','candidate'):
        if sha(proof[k]['path'])!=proof[k]['sha256']:raise ValueError('frozen package changed')
    meta=read(proof['metadata']['path'])
    if not meta['is_private'] or meta['enable_gpu'] or meta['enable_tpu'] or meta['id']!=SLUG:
        raise ValueError('wrong runtime')
    api=api_for_owner('davideferrante11')
    refs={k.ref for k in api.kernels_list(mine=True,page_size=50,sort_by='dateRun') if k.ref}
    prior={r['job'] for r in slots['observed'] if r['owner']=='davideferrante11' and r.get('job')}
    if SLUG in refs or refs-prior:raise ValueError('duplicate job or changed account inventory')
    write_new(FOLDER/'launch_intent.json',dict(utc=now(),prepared=pin(FOLDER/'prepared.json'),
        authorization=pin(authorization),slots=pin(slot_path),entry_id=proof['entry_id'],private=True,
        GPU=False,new_fit=False,account_token_transferred=False))
    result=api.kernels_push(proof['stage'],None,None)
    accepted=result is not None and not (getattr(result,'error',None) or getattr(result,'invalidKernelSources',None) or getattr(result,'invalidDatasetSources',None))
    report=dict(utc=now(),slug=SLUG,accepted=bool(accepted),version=getattr(result,'versionNumber',None),entry_id=proof['entry_id'])
    write_new(FOLDER/'launch_result.json',report);print(json.dumps(report))
    if not accepted:raise ValueError('push rejected; inspect existing entry, no blind retry')
    status=str(api.kernels_status(SLUG).status).split('.')[-1]
    write_new(FOLDER/'status_after_push.json',dict(utc=now(),status=status,slug=SLUG))
    print(json.dumps(dict(status=status,slug=SLUG)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['create-entry','launch']);a=p.parse_args()
    try:create_entry() if a.command=='create-entry' else launch()
    except Exception as exc:
        print('T39 scoped operation stopped: '+type(exc).__name__)
        raise SystemExit(1)
