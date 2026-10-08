"""Explicit one-shot private generation dispatch; no VCC submission operation."""
import argparse
import csv
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import re
import sys
from percorso import HERE,pin,read,sha,write_new,now
from cloud_campaign import CONFIG,call

FOLDER=HERE/'quick_generation/r1'


def api_for_owner(owner):
    for name in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):
        os.environ.pop(name,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    return api


def prepare_access(out):
    proof=read(FOLDER/'prepared.json');stage=Path(proof['stage'])
    for key,name in [('code','run.py'),('params','params.json'),('metadata','kernel-metadata.json')]:
        if sha(stage/name)!=proof[key]['sha256']:raise ValueError('frozen package changed')
    params=read(stage/'params.json');meta=read(stage/'kernel-metadata.json')
    if meta['is_private'] is not True or meta['enable_gpu'] or meta['enable_tpu']:
        raise ValueError('wrong runtime or visibility')
    if sha(proof['prediction']['path'])!=proof['prediction']['sha256']:
        raise ValueError('pre-registered prediction changed')
    api=api_for_owner(proof['owner'])
    listing=api.dataset_list_files(meta['dataset_sources'][0],page_size=100)
    if listing.error_message or listing.next_page_token:
        raise ValueError('unexpected controls dataset listing')
    files={f.name:f.total_bytes for f in listing.files}
    if any(files.get(n)!=b for n,b in params['controls']['bytes'].items()):
        raise ValueError('official controls not available with expected sizes')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    request=ApiGetKernelRequest();request.user_name,request.kernel_slug=meta['kernel_sources'][0].split('/')
    with api.build_kaggle_client() as client:
        kernel=client.kernels.kernels_api_client.get_kernel(request)
    receipt=dict(utc=now(),status='PASS',owner=proof['owner'],prepared=pin(FOLDER/'prepared.json'),
        controls_dataset=meta['dataset_sources'][0],controls_expected_bytes=params['controls']['bytes'],
        effects_kernel=meta['kernel_sources'][0],effects_kernel_private=kernel.metadata.is_private,
        effects_kernel_version=kernel.metadata.current_version_number,
        full_input_hashes='mandatory in the destination runtime before generation',
        resources='mandatory in the destination runtime before generation',new_compute_started=False)
    write_new(out,receipt);print(json.dumps(receipt))


def launch(preflight,access):
    if (FOLDER/'superseded_r1.json').exists():
        raise ValueError('T1 generation superseded by the human request for all usable sources; launch forbidden')
    proof=read(FOLDER/'prepared.json');stage=Path(proof['stage']);owner=proof['owner']
    for key,name in [('code','run.py'),('params','params.json'),('metadata','kernel-metadata.json')]:
        if sha(stage/name)!=proof[key]['sha256']:raise ValueError('frozen package changed')
    pre=read(preflight);access_doc=read(access)
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    if age>900 or pre['active'][owner]>=5:raise ValueError('fresh free slot required')
    if access_doc['status']!='PASS' or access_doc['prepared']['sha256']!=sha(FOLDER/'prepared.json'):
        raise ValueError('input access preflight differs')
    rc,body=call(owner,['kernels','list','--mine','--page-size','50','--sort-by','dateRun','--csv'])
    if rc:raise ValueError('dedup and current listing failed')
    refs={r['ref'] for r in csv.DictReader(io.StringIO(body)) if r.get('ref')}
    prior={r['job'] for r in pre['observed'] if r['owner']==owner}
    if proof['slug'] in refs or refs-prior:
        raise ValueError('new job appeared after slot snapshot; refresh before launch')
    with (FOLDER/'launch.lock').open('x',encoding='utf-8') as f:f.write(now())
    write_new(FOLDER/'launch_intent.json',dict(utc=now(),slug=proof['slug'],prepared=pin(FOLDER/'prepared.json'),
        preflight=pin(preflight),access=pin(access),
        owner_request='01a11d78-c711-7cb1-9f28-fdcf26fbffa2 in Lead chat, verified original human message',
        slot_policy='use the fifth CPU slot for the explicitly prioritized t37 delivery, within ceiling 5; no existing job stopped',
        submit=False,gpu=False,private=True))
    api=api_for_owner(owner)
    result=api.kernels_push(str(stage),None,None)
    error=getattr(result,'error',None)
    invalid_k=getattr(result,'invalidKernelSources',None)
    invalid_d=getattr(result,'invalidDatasetSources',None)
    safe_error=re.sub(r'https?://\S+','[URL REDACTED]',str(error))[:1200] if error else None
    accepted=bool(result is not None and not error and not invalid_k and not invalid_d)
    report=dict(utc=now(),slug=proof['slug'],accepted=accepted,error=safe_error,
        invalid_kernel_sources=invalid_k,invalid_dataset_sources=invalid_d,
        version=getattr(result,'versionNumber',None))
    write_new(FOLDER/'launch_result.json',report);print(json.dumps(report))
    if not accepted:raise RuntimeError('generation push rejected; never retry same revision')
    rc,body=call(owner,['kernels','status',proof['slug']])
    write_new(FOLDER/'status_after_push.json',dict(utc=now(),returncode=rc,answer=body))
    print(body)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('access');q.add_argument('out',type=Path)
    q=sub.add_parser('launch');q.add_argument('preflight',type=Path);q.add_argument('access',type=Path)
    a=p.parse_args()
    try:
        if a.cmd=='access':prepare_access(a.out)
        else:launch(a.preflight,a.access)
    except Exception as exc:
        print('Quick generation failed: '+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
