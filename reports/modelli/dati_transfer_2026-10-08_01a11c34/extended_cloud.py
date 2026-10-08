"""Read-only preflight and one-shot private T3 dispatch; never submits to VCC."""
import argparse
import csv
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import re
from percorso import HERE,pin,read,sha,write_new,now
from cloud_campaign import call
from quick_generation_cloud import api_for_owner

FOLDER=HERE/'extended_transfer/r1'


def prepared():
    proof=read(FOLDER/'prepared.json');stage=Path(proof['stage'])
    for k,n in [('code','run.py'),('params','extended_params.json'),('metadata','kernel-metadata.json')]:
        if sha(stage/n)!=proof[k]['sha256']:raise ValueError('frozen T3 package differs')
    for k in ('protocol','prediction'):
        if sha(proof[k]['path'])!=proof[k]['sha256']:raise ValueError('frozen scientific registration differs')
    metadata=read(stage/'kernel-metadata.json')
    if metadata['id']!=proof['slug'] or not metadata['is_private'] or metadata['enable_gpu'] or not metadata['enable_internet']:
        raise ValueError('T3 runtime identity differs')
    return proof,stage,metadata


def access(out):
    proof,stage,meta=prepared();params=read(stage/'extended_params.json')
    api=api_for_owner(proof['owner'])
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    sources=[]
    for slug in meta['kernel_sources']:
        req=ApiGetKernelRequest();req.user_name,req.kernel_slug=slug.split('/')
        with api.build_kaggle_client() as client:value=client.kernels.kernels_api_client.get_kernel(req)
        sources.append(dict(source=slug,version=value.metadata.current_version_number,private=value.metadata.is_private))
    datasets=[]
    for slug in meta['dataset_sources']:
        listing=api.dataset_list_files(slug,page_size=100)
        if listing.error_message or listing.next_page_token:raise ValueError('dataset listing incomplete')
        files={f.name:f.total_bytes for f in listing.files}
        if slug=='davideferrante11/vcc-official-controls-r1':
            if any(files.get(n)!=size for n,size in params['controls']['bytes'].items()):
                raise ValueError('official controls unavailable')
        datasets.append(dict(source=slug,files=len(files)))
    report=dict(utc=now(),status='PASS',prepared=pin(FOLDER/'prepared.json'),owner=proof['owner'],
        kernels=sources,datasets=datasets,private_ko_authorization=pin(HERE/'extended_transfer/r1/private_transfer_authorization.json'),
        full_hashes_and_resources='required by runtime before fit/generation',new_compute=False)
    write_new(out,report);print(json.dumps(dict(status='PASS',kernels=len(sources),datasets=len(datasets))))


def launch(slots,access_path):
    if (FOLDER/'NOT_LAUNCHED_r1.json').exists():
        raise ValueError('this defensive package is explicitly superseded; do not launch')
    proof,stage,meta=prepared();pre=read(slots);access_doc=read(access_path);owner=proof['owner']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    if age>900 or pre['active'][owner]>=5:raise ValueError('fresh free CPU slot required')
    if access_doc['status']!='PASS' or access_doc['prepared']['sha256']!=sha(FOLDER/'prepared.json'):
        raise ValueError('access preflight differs')
    rc,body=call(owner,['kernels','list','--mine','--page-size','50','--sort-by','dateRun','--csv'])
    if rc:raise ValueError('dedup listing failed')
    refs={r['ref'] for r in csv.DictReader(io.StringIO(body)) if r.get('ref')}
    prior={r['job'] for r in pre['observed'] if r['owner']==owner}
    if proof['slug'] in refs or refs-prior:raise ValueError('new job since slots snapshot')
    with (FOLDER/'launch.lock').open('x') as f:f.write(now())
    write_new(FOLDER/'launch_intent.json',dict(utc=now(),slug=proof['slug'],prepared=pin(FOLDER/'prepared.json'),
        slots=pin(slots),access=pin(access_path),private=True,gpu=False,
        scope='single full-compatible-source refit and generation under verified human mandate; no VCC upload in kernel',
        no_T1_fallback=True,no_ESM2_interruption=True))
    result=api_for_owner(owner).kernels_push(str(stage),None,None)
    error=getattr(result,'error',None);invalid_k=getattr(result,'invalidKernelSources',None);invalid_d=getattr(result,'invalidDatasetSources',None)
    accepted=bool(result is not None and not error and not invalid_k and not invalid_d)
    report=dict(utc=now(),slug=proof['slug'],accepted=accepted,
        error=re.sub(r'https?://\S+','[REDACTED]',str(error))[:800] if error else None,
        invalid_kernel_sources=invalid_k,invalid_dataset_sources=invalid_d,version=getattr(result,'versionNumber',None))
    write_new(FOLDER/'launch_result.json',report);print(json.dumps(report))
    if not accepted:raise RuntimeError('T3 launch rejected; no automatic retry')
    rc,body=call(owner,['kernels','status',proof['slug']])
    write_new(FOLDER/'status_after_push.json',dict(utc=now(),returncode=rc,answer=body));print(body)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path);sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('access');s.add_argument('out',type=Path)
    s=sub.add_parser('launch');s.add_argument('slots',type=Path);s.add_argument('access',type=Path)
    a=p.parse_args()
    if a.folder:
        FOLDER=a.folder.resolve()
        if not FOLDER.is_relative_to(HERE):raise ValueError('report folder outside owned area')
    try:
        if a.cmd=='access':access(a.out)
        else:launch(a.slots,a.access)
    except Exception as exc:
        print('T3 cloud operation failed: '+type(exc).__name__)
        raise SystemExit(1)
