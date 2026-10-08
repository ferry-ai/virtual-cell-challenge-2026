"""Verify, stream-download and submit the one frozen t38 product on Windows.

Run as a persistent hidden process. No automatic new-entry retries or changes to
existing VCC endpoint/authentication. Raw CLI outputs remain private outside Git.
"""
import argparse
import ctypes
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import requests
from percorso import DATA,HERE,ROOT,pin,read,sha,write_new,now
from quick_generation_cloud import api_for_owner

PREDICTION=ROOT/'reports/invii/prediction_t38_2026-10-09/prediction.json'
TRIAL=ROOT/'reports/invii/trial_2026-10-09'
EXPECTED_EFFECT='b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6'
MODEL='t38 - transfer CRISPRi plus KO'
DESCRIPTION=('Exploratory T1 CRISPRi core plus seven usable KO bank units, twelve contexts and five study-lineage votes. '
 'KO effects versus matched controls, no panel centering, fixed 0.25 study weight and within-study reliability pooling. '
 'CRISPRi estimator, amplitude, cis and t36 generator unchanged. All 34 KO-supported panel targets used. '
 'CRISPRa and unresolved-source gaps remain explicit; no prior improvement or complete D-053 claim.')


def cli():
    path=Path(sys.executable).with_name('vcc.exe')
    if not path.is_file():raise ValueError('project vcc.exe unavailable')
    return str(path)


def preflight(label):
    folder=DATA/'processed/dati_transfer_2026-10-08_01a11c34/submission_t38'/label
    folder.mkdir(parents=True,exist_ok=False)
    result=subprocess.run([cli(),'whoami','--json'],capture_output=True,text=True,encoding='utf-8')
    (folder/'whoami_raw.json').write_text(result.stdout,encoding='utf-8')
    (folder/'whoami_stderr.txt').write_text(result.stderr,encoding='utf-8')
    if result.returncode:raise ValueError('VCC whoami failed')
    doc=json.loads(result.stdout)
    state=Path.home()/'.config/vcc/state.json'
    pending=read(state).get('pending_uploads',{}) if state.exists() else {}
    version=subprocess.run([cli(),'--version'],capture_output=True,text=True,encoding='utf-8')
    # Keep unknown whoami schema private; exact approved/can_submit fields are
    # extracted recursively and the full private document remains inspectable.
    def values(obj,key):
        if isinstance(obj,dict):
            return ([obj[key]] if key in obj else [])+[v for x in obj.values() for v in values(x,key)]
        if isinstance(obj,list):return [v for x in obj for v in values(x,key)]
        return []
    allowed=values(doc,'can_submit');approved=values(doc,'approved')
    report=dict(utc=now(),whoami_returncode=0,can_submit_values=allowed,approved_values=approved,
        pending_uploads=len(pending),disk_free_bytes=shutil.disk_usage(DATA).free,
        version=version.stdout.strip(),raw=pin(folder/'whoami_raw.json'),new_submission=False)
    write_new(TRIAL/('preflight_'+label+'.json'),report)
    print(json.dumps(report))
    if pending or True not in allowed:raise ValueError('new VCC submission not currently available')
    return report


def download_product(api,job,filename,path,expected_bytes,report):
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
    request=ApiListKernelSessionOutputRequest();request.user_name,request.kernel_slug=job.split('/');request.page_size=100
    found=[]
    while True:
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(request)
        found.extend(f for f in response.files or [] if f.file_name==filename)
        if not response.next_page_token:break
        request.page_token=response.next_page_token
    if len(found)!=1:raise ValueError('unique frozen product unavailable')
    url=found[0].url;start=time.monotonic();last=0
    if path.exists() and path.stat().st_size>expected_bytes:raise ValueError('oversized local product')
    while (path.stat().st_size if path.exists() else 0)<expected_bytes:
        offset=path.stat().st_size if path.exists() else 0;end=min(expected_bytes-1,offset+(64<<20)-1)
        with requests.get(url,headers={'Range':f'bytes={offset}-{end}'},stream=True,timeout=(30,120)) as response:
            if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {offset}-{end}/{expected_bytes}':
                raise ValueError('provider range identity differs')
            with path.open('ab') as out:
                for block in response.iter_content(chunk_size=1<<20):
                    if not block:continue
                    if out.tell()+len(block)>end+1:raise ValueError('oversized range')
                    out.write(block)
                    if time.monotonic()-last>10:
                        out.flush();report('downloading',downloaded_bytes=out.tell(),bytes=expected_bytes,
                            seconds=time.monotonic()-start);last=time.monotonic()
                out.flush();os.fsync(out.fileno())
        if path.stat().st_size!=end+1:raise ValueError('short range retained; inspect before resuming')


def submit(evidence,attempt):
    if os.name!='nt':raise ValueError('persistent Windows process required')
    proof=read(HERE/'generation_recovery/r1/prepared.json')
    from collect_t38_generation import verify_receipts
    verify_receipts(evidence,proof)
    if sha(PREDICTION)!=proof['prediction']['sha256']:raise ValueError('preregistered prediction changed')
    manifest=read(evidence/'generation_manifest.json');package_path=evidence/'packaging.json'
    package=read(package_path)['package']
    if manifest['status']!='VCC_READY' or manifest['candidate']!='T3-CRISPRi-KO':raise ValueError('not the ready T3 candidate')
    if manifest['prediction']['sha256']!=sha(PREDICTION) or manifest['protocol']!=proof['protocol']:
        raise ValueError('candidate registration differs')
    if manifest['packaging_sha256']!=sha(package_path):raise ValueError('packaging receipt changed')
    if any(manifest['effects'][c]['sha256']!=EXPECTED_EFFECT for c in ('A','B','C')):raise ValueError('wrong frozen effects')
    if not package['validation']['ok'] or package['validation']['failures']:raise ValueError('invalid package')
    if (package['n_obs'],package['n_vars'],package['archive_bytes'])!=(360000,18533,manifest['bytes']):
        raise ValueError('incomplete product')
    verified=read(evidence/'verification.json')
    if (not verified['saved_code_matches'] or verified['job']!=proof['slug']
            or verified['code_sha256']!=proof['code']['sha256']
            or verified['product_sha256']!=manifest['sha256']):raise ValueError('producer not verified')
    run=DATA/'processed/dati_transfer_2026-10-08_01a11c34/submission_t38'/attempt
    run.mkdir(parents=True,exist_ok=False)
    write_new(run/'started.json',dict(utc=now(),pid=os.getpid(),job=proof['slug']))
    def state(stage,**fields):
        (run/'state.json').write_text(json.dumps(dict(utc=now(),stage=stage,**fields),indent=2),encoding='utf-8')
    awake=ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    if not awake:raise ValueError('could not inhibit system sleep')
    try:
        preflight(attempt+'_before_download')
        if shutil.disk_usage(DATA).free<manifest['bytes']+5*1024**3:raise ValueError('insufficient local product disk')
        destination=DATA/'submissions/t38_crispri_ko_2026-10-09';destination.mkdir(parents=True,exist_ok=True)
        product=destination/manifest['product']
        state('downloading',bytes=manifest['bytes'])
        download_product(api_for_owner('davideferrante11'),proof['slug'],manifest['product'],product,manifest['bytes'],state)
        state('verifying_local_product')
        if product.stat().st_size!=manifest['bytes'] or sha(product)!=manifest['sha256']:raise ValueError('local product pin differs')
        write_new(TRIAL/'t38_local_product.json',dict(**pin(product),checksum_verified=True,source_job=proof['slug']))
        preflight(attempt+'_before_upload')
        # Atomic one-entry guard is never removed automatically, including on an uncertain failure.
        with (TRIAL/'submit_t38.lock').open('x') as f:f.write(now())
        write_new(TRIAL/'submit_t38_started.json',dict(utc=now(),pid=os.getpid(),model_name=MODEL,
            product_sha256=manifest['sha256'],prediction_sha256=sha(PREDICTION),system_sleep_inhibited=True))
        with (TRIAL/'submit_t38_started.txt').open('x',encoding='utf-8') as f:
            f.write(now()+' '+MODEL+'\nsha256='+manifest['sha256']+'\n')
        state('uploading',product_sha256=manifest['sha256'],bytes=manifest['bytes'])
        env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
        raw=run/'submit_raw.json';stderr=run/'submit_stderr.txt'
        with raw.open('x',encoding='utf-8') as out,stderr.open('x',encoding='utf-8') as err:
            result=subprocess.run([cli(),'submit',str(product),'-m',MODEL,'-d',DESCRIPTION,'--json'],env=env,stdout=out,stderr=err)
        finish=dict(utc=now(),returncode=result.returncode,raw=pin(raw),stderr=pin(stderr),automatic_retry=False)
        write_new(TRIAL/'submit_t38_finished.json',finish);write_new(run/'finished.json',finish)
        state('submit_returned' if result.returncode==0 else 'submit_failed_or_interrupted',returncode=result.returncode)
        return result.returncode
    except BaseException as exc:
        state('error',error_type=type(exc).__name__)
        return 1
    finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('preflight');s.add_argument('label')
    s=sub.add_parser('submit');s.add_argument('--evidence',type=Path,required=True);s.add_argument('--attempt',required=True)
    a=p.parse_args()
    try:
        if a.cmd=='preflight':preflight(a.label)
        else:raise SystemExit(submit(a.evidence,a.attempt))
    except Exception as exc:
        print('t38 operation failed: '+type(exc).__name__);raise SystemExit(1)
