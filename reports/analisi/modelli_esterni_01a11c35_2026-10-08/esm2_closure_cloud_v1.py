"""Explicit private upload/launch lifecycle for the frozen ESM2 closure bank."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from ammi_inputs_v3 import checked
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREPARED=HERE/'esm2_closure_bank_prepared_r1.json'
OWNER='davideferrante11'


def now():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def api():
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle-davideferrante11')
    from kaggle.api.kaggle_api_extended import KaggleApi
    service=KaggleApi();service.authenticate();return service
def compact_error(error):
    return dict(type=type(error).__name__,http_status=getattr(getattr(error,'response',None),'status_code',None))


def upload(out):
    prepared=read(PREPARED);stage=Path(prepared['stage'])
    if set(p.name for p in stage.iterdir())!=set(prepared['files'])|{'dataset-metadata.json'}:
        raise ValueError('dataset file allowlist differs')
    for name,pin in prepared['files'].items():checked(dict(pin,path=str(stage/name)))
    if sha256(stage/'dataset-metadata.json')!=prepared['dataset_metadata_sha256']:
        raise ValueError('dataset metadata differs')
    service=api()
    write(Path(out).with_suffix('.intent.json'),dict(utc=now(),dataset=prepared['dataset'],private=True,
        files=prepared['files'],human_approval_question_id='call_22929f7d56f042d9ae9d8a67944ae138',
        human_answer='Sì, autorizzo il caricamento privato',
        scope='126 MB of derived ESM2 predictions to private davideferrante11/vcc-esm2-closure-01a11c35-r1; no raw RNA'))
    result=service.dataset_create_new(str(stage),public=False,quiet=True,dir_mode='skip')
    error=getattr(result,'error',None)
    report=dict(utc=now(),dataset=prepared['dataset'],private=True,provider_error=str(error) if error else None)
    write(out,report);print(json.dumps(report))
    if error:raise RuntimeError('private dataset creation failed')


def dataset_status(out):
    prepared=read(PREPARED);service=api()
    state=service.dataset_status(prepared['dataset'])
    # Provider response is compacted deliberately; no upload locators are persisted.
    status=getattr(state,'status',state)
    report=dict(utc=now(),dataset=prepared['dataset'],status=str(status))
    write(out,report);print(json.dumps(report))


def preflight(out):
    prepared=read(PREPARED);bank=read(prepared['bank_prepared'])
    stage=ROOT/bank['stage'];meta=stage/'kernel-metadata.json'
    bridge=Path(out).with_suffix('.input.json')
    write(bridge,dict(jobs=[dict(slug=bank['slug'],metadata=dict(path=str(meta),bytes=meta.stat().st_size,sha256=sha256(meta)))]))
    cmd=[sys.executable,str(ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34/preflight_neural_inputs.py'),
         '--prepared',str(bridge),'--out',str(out)]
    subprocess.run(cmd,check=True)


def launch(preflight_path,out):
    prepared=read(PREPARED);bank=read(prepared['bank_prepared']);pre=read(preflight_path)
    if (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()>900:
        raise ValueError('fresh preflight required')
    owner=next(x for x in pre['accounts'] if x['owner']==OWNER)
    if (owner['active_or_unknown']>=pre['slot_limit_per_account']
            or any(not r['native_admissible'] for r in owner['sources'])):
        raise ValueError('owner runtime or input access unavailable')
    stage=ROOT/bank['stage']
    for name,key in [('run.py','code'),('params.json','params')]:checked(dict(bank[key],path=str(stage/name)))
    metadata=read(stage/'kernel-metadata.json')
    if metadata!=bank['metadata'] or not metadata['is_private'] or metadata['enable_gpu']:
        raise ValueError('frozen private CPU metadata differs')
    service=api();slug=bank['slug']
    existing=[k.ref for k in service.kernels_list(mine=True,search=slug.split('/')[1],page_size=100) if k.ref]
    if slug in existing:raise ValueError('job already exists; status lookup required, no duplicate push')
    lock=Path(out).with_suffix('.lock')
    with lock.open('x') as stream:stream.write(slug)
    write(Path(out).with_suffix('.intent.json'),dict(utc=now(),slug=slug,code_sha256=bank['code']['sha256'],
        preflight_sha256=sha256(preflight_path),private=True,gpu=False,
        human_message_id='01a1213f-11e7-73a0-8712-a848c64f8c4d',
        scope='existing ESM2 C/J frozen readout; unchanged independent metrics; MODELLI execution'))
    try:
        response=service.kernels_push(str(stage))
        error=getattr(response,'error',None)
        report=dict(utc=now(),slug=slug,accepted=not bool(error),provider_error=str(error) if error else None)
        if not error:report['status']=str(service.kernels_status(slug).status).split('.')[-1]
    except Exception as error:
        report=dict(utc=now(),slug=slug,accepted='unknown',error=compact_error(error),
            action='check exact remote state before any retry')
    write(out,report);print(json.dumps(report))


def status(out):
    prepared=read(PREPARED);bank=read(prepared['bank_prepared']);service=api()
    report=dict(utc=now(),slug=bank['slug'],status=str(service.kernels_status(bank['slug']).status).split('.')[-1])
    write(out,report);print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('action',choices=['upload','dataset-status','preflight','launch','status'])
    p.add_argument('--out',required=True);p.add_argument('--preflight');a=p.parse_args()
    if a.action=='launch':launch(a.preflight,a.out)
    else:{'upload':upload,'dataset-status':dataset_status,'preflight':preflight,'status':status}[a.action](a.out)
