"""Private derived-output sharing requested by the owner; no source ACL changes.

Prepare and hash locally, create a private dataset, grant reader access only to
the two configured accounts. Never publishes a dataset or changes notebook ACLs.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from cloud_campaign import call
from percorso import DATA,HERE,ROOT,now,pin,read,sha,write_new

REV='01a11c34-r4private';UNIT='xu2023';OWNER='davideferante'
REF='davideferante/dt-xu2023-private-01a11c34-r1'
READERS=['davideferrante11','davidmaisterx']
DEST=DATA/'processed/dati_transfer_2026-10-08_01a11c34/private_share_xu_r1'
EVIDENCE=HERE/'private_share_xu_r1'


def prepare():
    source=HERE/'alltargets'/REV/UNIT/'completion_r2_w000'
    verified=read(source/'verification.json');receipt=read(source/'effect_release.json')
    if sha(source/'effect_release.json')!=verified['receipt']['sha256']:raise ValueError('receipt changed')
    proof=read(source.parent/'prepared.json')
    EVIDENCE.mkdir(exist_ok=False);DEST.mkdir(parents=True,exist_ok=False)
    raw=DEST/'download';raw.mkdir()
    rc,body=call(OWNER,['kernels','output',proof['slug'],'-p',str(raw),'--file-pattern',r'\.npz$'])
    write_new(EVIDENCE/'retrieval.json',dict(utc=now(),returncode=rc,answer=body))
    if rc:raise ValueError('derived output download failed')
    pack=DEST/'dataset';pack.mkdir()
    pins={}
    for name,expected in receipt['outputs'].items():
        if not name.endswith('.npz'):continue
        hits=[p for p in raw.rglob('*') if p.is_file() and p.stat().st_size==expected['bytes'] and sha(p)==expected['sha256']]
        if not hits:raise ValueError('output hash missing: '+name)
        target=pack/Path(name).name;shutil.copyfile(hits[0],target);pins[target.name]=pin(target)
    for name in ('effect_release.json','complete.json'):
        shutil.copyfile(source/name,pack/name);pins[name]=pin(pack/name)
    for name in ('run.py','params.json'):
        shutil.copyfile(ROOT/proof['stage']/name,pack/name);pins[name]=pin(pack/name)
    shared=dict(utc=now(),private=True,producer=proof['slug'],producer_version=verified['remote_identity']['version'],
        readers=READERS,outputs_independently_rehashed=True,files=pins,source_datasets_visibility_changed=False,
        purpose='Private cross-account consumption of explicitly authorised derived effects and reproducibility code')
    write_new(pack/'SHARE_RECEIPT.json',shared)
    meta=dict(id=REF,title='dt-xu2023-private-01a11c34-r1',licenses=[dict(name='other')],
        isPrivate=True,description='Private reproducible Xu2023 effects for the authorised DATI-TRANSFER campaign. Partial research release, not a score or final candidate.',
        collaborators=[dict(username=u,role='reader') for u in READERS])
    write_new(pack/'dataset-metadata.json',meta)
    write_new(EVIDENCE/'prepared.json',dict(utc=now(),folder=str(pack),reference=REF,
        metadata=pin(pack/'dataset-metadata.json'),receipt=pin(pack/'SHARE_RECEIPT.json'),
        total_bytes=sum(p.stat().st_size for p in pack.iterdir())))
    print(json.dumps(read(EVIDENCE/'prepared.json')))


def connect():
    proof=read(EVIDENCE/'prepared.json');pack=Path(proof['folder'])
    for item in ('metadata','receipt'):
        if sha(proof[item]['path'])!=proof[item]['sha256']:raise ValueError('prepared sharing changed')
    with (EVIDENCE/'create.lock').open('x') as f:f.write(now())
    # Import only after the account environment is established (SDK module cache).
    from cloud_campaign import CONFIG
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[OWNER])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    result=api.dataset_create_new(str(pack),public=False,quiet=True,convert_to_csv=False)
    error=getattr(result,'error',None)
    write_new(EVIDENCE/'created.json',dict(utc=now(),reference=REF,error=error,status=str(getattr(result,'status',None)),private_requested=True))
    if error:raise ValueError(error)
    # Metadata includes isPrivate=True explicitly; omitting it would default public.
    api.dataset_metadata_update(REF,str(pack))
    write_new(EVIDENCE/'shared.json',dict(utc=now(),reference=REF,isPrivate=True,readers=READERS,
        metadata=pin(pack/'dataset-metadata.json'),verification_pending=True))
    print(REF+' created private; reader grants submitted')


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=['prepare','connect']);a=p.parse_args()
    prepare() if a.command=='prepare' else connect()
