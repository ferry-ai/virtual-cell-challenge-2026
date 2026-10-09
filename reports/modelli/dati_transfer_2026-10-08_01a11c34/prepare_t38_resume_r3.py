"""Prepare recovery of the existing VCC entry; never create a second submission."""
import argparse
import base64
import io
import json
from pathlib import Path
import re
import zipfile
import hashlib
from percorso import HERE,DATA,read,pin,sha,write_new,now
from prepare_extended_generation import unpack
import cloud_t38_delivery_r2 as base

FOLDER=HERE/'cloud_delivery/r3'
PRIVATE=DATA/'processed/dati_transfer_2026-10-08_01a11c34/cloud_delivery/r3'
SLUG='davideferrante11/dt-t3-package-upload-01a11c34-r3'


def prepare():
    base.verify_current_authorization()
    previous=read(HERE/'cloud_delivery/r2/prepared.json')
    if previous['entry_id']!='LJmnhqqh1WTrx1JcoRlr':raise ValueError('single entry differs')
    if sha(previous['code']['path'])!=previous['code']['sha256']:raise ValueError('previous package changed')
    members,params=unpack(previous['code']['path'])
    cap=json.loads(members['delivery_capability.json'])
    if cap['entry_id']!=previous['entry_id']:raise ValueError('upload capability differs')
    members.pop('params.json')
    members['private_download_v2.py']=(HERE/'private_download_t38_r3.py').read_bytes()
    params['job_id']=SLUG.split('/')[1]
    params['embedded_sha256']={n:hashlib.sha256(b).hexdigest() for n,b in members.items()}
    members['params.json']=(json.dumps(params,indent=1)+'\n').encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(members.items()):z.writestr(name,data)
    oldcode=Path(previous['code']['path']).read_text()
    encoded=base64.b64encode(buf.getvalue()).decode()
    code,n=re.subn(r"b64decode\('[A-Za-z0-9+/=]+'\)",lambda _:"b64decode('"+encoded+"')",oldcode)
    if n!=1:raise ValueError('ambiguous payload replacement')
    import ast
    ast.parse(code)
    PRIVATE.mkdir(parents=True,exist_ok=False);FOLDER.mkdir(parents=True,exist_ok=False)
    stage=PRIVATE/'package';stage.mkdir()
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    (stage/'extended_params.json').write_bytes(members['params.json'])
    metadata=read(previous['metadata']['path']);metadata['id']=SLUG;metadata['title']=SLUG.split('/')[1]
    write_new(stage/'kernel-metadata.json',metadata)
    created=read(DATA/'processed/dati_transfer_2026-10-08_01a11c34/cloud_delivery/r2/created_private.json')
    if created['entry_id']!=cap['entry_id']:raise ValueError('server entry differs')
    write_new(PRIVATE/'created_private.json',created)
    proof=dict(previous,utc=now(),slug=SLUG,stage=str(stage),code=pin(stage/'run.py'),
        params=pin(stage/'extended_params.json'),metadata=pin(stage/'kernel-metadata.json'),
        previous_attempt=pin(HERE/'cloud_delivery/r2/prepared.json'),new_entry_created=False,
        recovery_reason='Uninstrumented whole-response download identity failure; exact bounded ranges and explicit full hash',
        source_expected_sha256=params['input_product']['sha256'])
    write_new(FOLDER/'prepared.json',proof)
    print(json.dumps(dict(slug=SLUG,entry_id=cap['entry_id'],new_entry_created=False)))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=['prepare','launch']);p.add_argument('--slots',type=Path);a=p.parse_args()
    try:
        if a.command=='prepare':prepare()
        else:
            base.FOLDER=FOLDER;base.PRIVATE=PRIVATE;base.SLUG=SLUG;base.launch(a.slots)
    except Exception as exc:
        print('Existing-entry recovery failed: '+type(exc).__name__)
        raise SystemExit(1)
