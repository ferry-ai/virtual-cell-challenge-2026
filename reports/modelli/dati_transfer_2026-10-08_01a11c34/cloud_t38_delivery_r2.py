"""Prepare scoped private cloud upload, keeping the VCC account token local."""
import argparse
import ast
import base64
import hashlib
import io
import json
from datetime import datetime,timezone
from pathlib import Path
import requests
import re
import zipfile
import os
os.environ['PYTHONUTF8']='1'
from percorso import DATA,HERE,ROOT,pin,read,sha,write_new,now
from quick_generation_cloud import api_for_owner
from prepare_extended_generation import unpack
from t38_submission import MODEL,DESCRIPTION,preflight,TRIAL

FOLDER=HERE/'cloud_delivery/r2'
PRIVATE=DATA/'processed/dati_transfer_2026-10-08_01a11c34/cloud_delivery/r2'
SOURCE=HERE/'generation_recovery/r4/prepared.json'
SLUG='davideferrante11/dt-t3-package-upload-01a11c34-r2'


def verify_current_authorization():
    auth=read(HERE/'t38_resume_authorization_r1.json')
    if not auth['original_human_response_read_directly'] or auth['source_user_message_id']!='01a121b0-f69e-7642-9cf0-94ca32eb6173':
        raise ValueError('current human authorization absent')


def source():
    verify_current_authorization()
    proof=read(SOURCE);api=api_for_owner(proof['owner'])
    status=str(api.kernels_status(proof['slug']).status).split('.')[-1]
    if status not in ('COMPLETE','ERROR'):print(json.dumps(dict(source_status=status)));return 2
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest,ApiListKernelSessionOutputRequest
    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=proof['slug'].split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    code_sha=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    if code_sha!=proof['code']['sha256'] or saved.metadata.current_version_number!=1 or not saved.metadata.is_private:
        raise ValueError('source producer identity differs')
    req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=proof['slug'].split('/');req.page_size=100
    files={}
    while True:
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(req)
        for f in response.files or []:files[f.file_name]=f.url
        if not response.next_page_token:break
        req.page_token=response.next_page_token
    wanted={'compact_diagnostics.json','generation_preflight.json','generation_stage45_manifest.json'}
    mode='upload' if 'generation_manifest.json' in files else 'package'
    if mode=='upload':wanted|={'generation_manifest.json','packaging.json','manifest_48_package_prediction.json'}
    elif 'recovery_prediction.h5ad' not in files:raise ValueError('no recoverable generated cells')
    if not wanted.issubset(files):raise ValueError('source receipts missing')
    dest=FOLDER/'source';dest.mkdir(parents=True,exist_ok=False)
    for name in wanted:
        response=requests.get(files[name],timeout=60);response.raise_for_status();data=response.content
        if len(data)>2_000_000 or b'kaggleusercontent.com' in data or b'"url"' in data:raise ValueError('unsafe receipt')
        json.loads(data)
        with (dest/name).open('xb') as out:out.write(data)
    diag=read(dest/'compact_diagnostics.json');pre=read(dest/'generation_preflight.json')
    if diag['shape']!={'n_perturbations':300,'cells_per_pert':400,'contexts':['A','B','C'],'n_cells':360000,'n_genes':18533}:
        # Accept additional diagnostic keys, but never a missing/full-shape mismatch.
        shape=diag['shape']
        if (shape['n_perturbations'],shape['cells_per_pert'],shape['contexts'],shape['n_cells'])!=(300,400,['A','B','C'],360000):
            raise ValueError('incomplete generated shape')
    if diag['is_pilot'] or diag['context_provenance_ok'] is not True or diag['seed']!=20260912:raise ValueError('wrong generation')
    for key in ('protocol','prediction','fit_receipt'):
        if pre[key]!=proof[key] or sha(proof[key]['path'])!=proof[key]['sha256']:raise ValueError('scientific pins changed')
    if any(v['sha256']!='b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6' for v in pre['effects'].values()):
        raise ValueError('wrong T3 effects')
    if mode=='package':
        input_product=read(dest/'generation_stage45_manifest.json')['outputs']['prediction']
        raw_log=api.kernels_logs(proof['slug'])
        log_path=PRIVATE.parent/'source_r5_log_r2.json';log_path.parent.mkdir(parents=True,exist_ok=True)
        with log_path.open('x',encoding='utf-8') as f:f.write(raw_log)
        try:lines='\n'.join(str(e.get('data','')) for e in json.loads(raw_log))
        except (ValueError,TypeError):lines=raw_log
        full_hashes=re.findall(r'^\s*sha256\s*:\s*([0-9a-f]{64})',lines,re.M)
        if len(full_hashes)!=1:raise ValueError('unique full stage48 input hash unavailable')
        input_product=dict(input_product,sha256=full_hashes[0],sha256_mode='full',full_hash_origin='stage48 streamed input hash before resource guard')
    else:
        from collect_t38_generation import verify_receipts
        manifest=verify_receipts(dest,proof)
        input_product={k:manifest[k] for k in ('bytes','sha256')}
    report=dict(utc=now(),status='SOURCE_VERIFIED',mode=mode,job=proof['slug'],source_status=status,
        source_saved_code_sha256=code_sha,version=1,source_receipts={n:pin(dest/n) for n in wanted},
        input_product=input_product,source=pin(SOURCE),arrays_downloaded=False)
    write_new(FOLDER/'source_verified.json',report)
    product_name='recovery_prediction.h5ad' if mode=='package' else 'prediction_t38_T3.vcc'
    write_new(PRIVATE.parent/'source_access_r2.json',{name:files[name] for name in wanted|{product_name}})
    print(json.dumps({k:report[k] for k in ('status','mode','job','input_product')}));return 0


def auth_context():
    from vcc import auth,config
    profile=config.resolve_profile(None);state=auth.read_profile_state(profile)
    endpoint=config.resolve_endpoint(None,state.get('endpoint'))
    if endpoint!='https://virtualcellchallenge.org':raise ValueError('unexpected VCC endpoint')
    return auth,profile,endpoint,auth.resolve_token(profile).token


def prepare():
    verify_current_authorization()
    evidence=read(FOLDER/'source_verified.json');proof=read(SOURCE)
    if evidence['status']!='SOURCE_VERIFIED':raise ValueError('source not verified')
    # Freeze code before any external entry creation. No VCC account key is bundled.
    members,old=unpack(ROOT/'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package/run.py')
    members['emission_support.py']=members.pop('driver.py')
    members['driver.py']=(HERE/'package_upload_t38_r2.py').read_bytes();members.pop('params.json')
    helper=ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08/private_download_v2.py'
    if sha(helper)!='ea9345e7f5913b39c80d7917dc766342ab880d8ad184746a5a5c4f95113a78c0':raise ValueError('download helper changed')
    members['private_download_v2.py']=helper.read_bytes()
    members['source_locators.json']=(PRIVATE.parent/'source_access_r2.json').read_bytes()
    ast.parse(members['driver.py'])
    if sha(SOURCE)!=evidence['source']['sha256']:raise ValueError('source proof changed')
    PRIVATE.mkdir(parents=True,exist_ok=False)
    preflight('cloud_delivery_r2')
    from vcc import api
    from vcc.submit import check_no_inflight,_validated_resume
    from vcc.lock import SubmitLock
    from vcc.config import config_dir
    auth,profile,endpoint,token=auth_context()
    lock=SubmitLock(config_dir()/'locks'/('submit-'+profile+'.lock'));lock.acquire()
    try:
        check_no_inflight(endpoint,token,pending=auth.list_pending_uploads(profile))
        limits=api.get_limits(endpoint,token)
        if limits.get('limit_reached'):raise ValueError('VCC daily limit reached')
        with (TRIAL/'submit_t38.lock').open('x') as f:f.write(now())
        created=api.create_submission(endpoint,token,model_name=MODEL,description=DESCRIPTION,
            file_name='prediction_t38_T3.vcc',file_type='application/x-tar')
        write_new(PRIVATE/'created_private.json',created)
        resume=dict(created,local_path=str(DATA/'submissions/t38_crispri_ko_2026-10-09/prediction_t38_T3.vcc'),model_name=MODEL,prepared_from=None)
        _validated_resume(resume)
        auth.save_pending_upload(profile,created['entry_id'],resume)
    finally:lock.release()
    members['delivery_capability.json']=(json.dumps({k:created[k] for k in ('entry_id','upload_url')})+'\n').encode()
    params=dict(job_id=SLUG.split('/')[1],product='prediction_t38_T3.vcc',mode=evidence['mode'],
        input_generation_job=proof['slug'],source_job=proof['source_job'],input_product=evidence['input_product'],
        source_receipts=evidence['source_receipts'],protocol=proof['protocol'],prediction=proof['prediction'],
        fit_receipt=proof['fit_receipt'],controls=old['controls'],axis=old['axis'],
        embedded_sha256={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
    members['params.json']=(json.dumps(params,indent=1)+'\n').encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(members.items()):z.writestr(name,data)
    payload=base64.b64encode(buf.getvalue()).decode()
    code='import os,sys,base64,io,zipfile,runpy\nfrom pathlib import Path,PurePosixPath\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\n'
    code+='with zipfile.ZipFile(io.BytesIO(base64.b64decode('+repr(payload)+'))) as z:\n for n in z.namelist():\n  p=PurePosixPath(n);assert not p.is_absolute() and ".." not in p.parts;q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(n))\n'
    code+='import subprocess,importlib.metadata as md\ncore={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\nPath("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\nsubprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0","httpx==0.28.1"])\nassert {n:md.version(n) for n in core}==core\nrunpy.run_path("driver.py",run_name="__main__")\n'
    ast.parse(code)
    stage=PRIVATE/'package';stage.mkdir()
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    (stage/'extended_params.json').write_bytes(members['params.json'])
    write_new(stage/'kernel-metadata.json',dict(id=SLUG,title=SLUG.split('/')[1],code_file='run.py',language='python',
        kernel_type='script',is_private=True,enable_internet=True,enable_gpu=False,enable_tpu=False,
        dataset_sources=[],kernel_sources=[],competition_sources=[]))
    prepared=dict(utc=now(),slug=SLUG,owner='davideferrante11',stage=str(stage),private=True,
        authorization=pin(HERE/'t38_resume_authorization_r1.json'),
        recovery_fixture=pin(HERE/'t38_recovery_fixture_r3.json'),
        code=pin(stage/'run.py'),params=pin(stage/'extended_params.json'),metadata=pin(stage/'kernel-metadata.json'),
        protocol=proof['protocol'],prediction=proof['prediction'],fit_receipt=proof['fit_receipt'],
        source_job=proof['source_job'],entry_id=created['entry_id'],mode=evidence['mode'],VCC_account_token_transferred=False)
    write_new(FOLDER/'prepared.json',prepared)
    write_new(TRIAL/'submit_t38_started.json',dict(utc=now(),entry_id=created['entry_id'],model_name=MODEL,
        method='official CLI API + scoped cloud uploader; token remains local',source_verified=pin(FOLDER/'source_verified.json')))
    print(json.dumps({k:prepared[k] for k in ('slug','entry_id','mode','VCC_account_token_transferred')}))


def launch(slots):
    verify_current_authorization()
    proof=read(FOLDER/'prepared.json');stage=Path(proof['stage']);snapshot=read(slots)
    if (datetime.now(timezone.utc)-datetime.fromisoformat(snapshot['utc'])).total_seconds()>900:
        raise ValueError('slot check too old')
    if snapshot['active']['davideferrante11']>=5:raise ValueError('no free CPU slot')
    for key,name in [('code','run.py'),('params','extended_params.json'),('metadata','kernel-metadata.json')]:
        if sha(stage/name)!=proof[key]['sha256']:raise ValueError('prepared package changed')
    meta=read(stage/'kernel-metadata.json')
    if not meta['is_private'] or meta['enable_gpu'] or not meta['enable_internet']:raise ValueError('wrong runtime visibility')
    api=api_for_owner('davideferrante11')
    refs={k.ref for k in api.kernels_list(mine=True,page_size=50,sort_by='dateRun') if k.ref}
    prior={r['job'] for r in snapshot['observed'] if r['owner']=='davideferrante11' and r.get('job')}
    if proof['slug'] in refs or refs-prior:raise ValueError('job inventory changed')
    source_status=str(api.kernels_status(read(SOURCE)['slug']).status).split('.')[-1]
    if source_status not in ('COMPLETE','ERROR'):raise ValueError('source still running')
    with (FOLDER/'launch.lock').open('x') as f:f.write(now())
    write_new(FOLDER/'launch_intent.json',dict(utc=now(),prepared=pin(FOLDER/'prepared.json'),slots=pin(slots),
        entry_id=proof['entry_id'],private=True,CPU=True,uploads_only_this_VCC_entry=True,
        account_token_transferred=False,capability='single official GCS resumable object; outside Git and logs'))
    result=api.kernels_push(str(stage),None,None)
    accepted=not(getattr(result,'error',None) or getattr(result,'invalidKernelSources',None) or getattr(result,'invalidDatasetSources',None))
    record=dict(utc=now(),slug=proof['slug'],accepted=accepted,version=getattr(result,'versionNumber',None))
    write_new(FOLDER/'launch_result.json',record);print(json.dumps(record))
    if not accepted:raise ValueError('cloud upload launch rejected; inspect, do not recreate VCC entry')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['source','prepare','launch']);parser.add_argument('--slots',type=Path);args=parser.parse_args()
    try:
        if args.command=='source':raise SystemExit(source())
        elif args.command=='prepare':prepare()
        else:launch(args.slots)
    except Exception as exc:
        print('Cloud delivery operation failed: '+type(exc).__name__)
        raise SystemExit(1)
