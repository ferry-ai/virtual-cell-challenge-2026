"""One-shot, locked cloud dispatch and receipt retrieval for frozen derivations.

Explicit CLI launch only. No quota purchase, account creation, source visibility
change, fallback to newer data or automatic retry. New attempts need new names.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from percorso import HERE,ROOT,now,pin,read,sha,write_new
sys.path.insert(0,str(ROOT/'reports/modelli/percorso_riusabile_2026-10-05'))
from pipeline_state import CONFIG


def call(owner,args):
    env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner]);env['PYTHONIOENCODING']='utf-8'
    command=([sys.executable,str(HERE/'push_diagnostic.py'),args[3]] if args[:3]==['kernels','push','-p']
             else [str(Path(sys.executable).with_name('kaggle.exe')),*args])
    run=subprocess.run(command,env=env,
        capture_output=True,encoding='utf-8',errors='replace',timeout=300)
    return run.returncode,(run.stdout+run.stderr).strip()


def launch(revision,units,preflight,public=False):
    folder=HERE/'alltargets'/revision
    pre=read(preflight)
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    if age>900:raise ValueError('fresh preflight required')
    active=dict(pre['active'])
    # Count our own intents written after the snapshot, including uncertain pushes.
    for intent in (HERE/'alltargets').glob('*/*/launch_intent.json'):
        doc=read(intent)
        if datetime.fromisoformat(doc['utc'])>datetime.fromisoformat(pre['utc']):
            active[doc['owner']]=active.get(doc['owner'],0)+1
    for unit in units:
        dest=folder/unit;proof=read(dest/'prepared.json');owner=proof['owner']
        if active.get(owner,0)>=pre['slot_limit_per_account']:
            raise ValueError('no measured slot: '+owner)
        stage=ROOT/proof['stage']
        for key,name in [('code','run.py'),('params','params.json'),('metadata','kernel-metadata.json')]:
            if sha(stage/name)!=proof[key]['sha256']:raise ValueError('frozen package changed')
        rc,body=call(owner,['kernels','list','--mine','--search',proof['slug'].split('/')[1],'--csv'])
        if rc or proof['slug'] in body:raise ValueError('duplicate or dedup lookup failed: '+unit)
        # Atomic lock is never removed: a failed/uncertain launch requires a new revision.
        with (dest/'launch.lock').open('x',encoding='utf-8') as f:f.write(now()+'\n')
        if public:
            target=dest/'public_package';shutil.copytree(stage,target)
            meta=read(target/'kernel-metadata.json');meta['is_private']=False
            (target/'kernel-metadata.json').write_text(json.dumps(meta,indent=1)+'\n',encoding='utf-8')
            stage=target
        write_new(dest/'launch_intent.json',dict(utc=now(),owner=owner,slug=proof['slug'],
            preflight=pin(preflight),code=pin(stage/'run.py'),metadata=pin(stage/'kernel-metadata.json'),
            public=public,authorization='explicit owner consent in DATI-TRANSFER chat for frozen production and T/J campaigns'))
        rc,body=call(owner,['kernels','push','-p',str(stage)])
        accepted=rc==0 and 'successfully pushed' in body
        write_new(dest/'launch_result.json',dict(utc=now(),returncode=rc,answer=body,accepted=accepted))
        print(json.dumps(dict(unit=unit,slug=proof['slug'],accepted=accepted)),flush=True)
        if not accepted:raise ValueError('push failed; stop and diagnose: '+body)
        active[owner]=active.get(owner,0)+1
        rc,status=call(owner,['kernels','status',proof['slug']])
        write_new(dest/'status_after_push.json',dict(utc=now(),returncode=rc,answer=status))
        print(status,flush=True)


def collect(revision,unit,attempt):
    dest=HERE/'alltargets'/revision/unit;proof=read(dest/'prepared.json')
    owner=proof['owner'];rc,body=call(owner,['kernels','status',proof['slug']])
    if rc or 'COMPLETE' not in body:
        write_new(dest/('status_'+attempt+'.json'),dict(utc=now(),returncode=rc,answer=body))
        print(body);return
    out=dest/('completion_'+attempt);out.mkdir(exist_ok=False)
    rc,body=call(owner,['kernels','output',proof['slug'],'-p',str(out),'--file-pattern',
        '^complete.json$|^effect_release.json$|^resources.json$|^runtime_preflight.json$'])
    write_new(out/'retrieval.json',dict(utc=now(),returncode=rc,answer=body))
    if rc:raise ValueError('receipt retrieval failed')
    verify(revision,unit,out)


def verify(revision,unit,out):
    dest=HERE/'alltargets'/revision/unit;proof=read(dest/'prepared.json');owner=proof['owner']
    out=Path(out)
    params=read(ROOT/proof['stage']/'params.json');done=read(out/'complete.json');receipt=read(out/'effect_release.json')
    if sha(out/'effect_release.json')!=done['receipt_sha256'] or receipt['params_sha256']!=proof['params']['sha256']:
        raise ValueError('receipt identity differs')
    # Check every source and split against prepared pins, and query the saved code version.
    if receipt['bank']!=params['bank'] or receipt['split']!=params['split']:
        raise ValueError('input or split mismatch')
    # Kaggle's SDK caches configuration at module import. Isolate each identity
    # query so switching accounts cannot reuse the first account's credentials.
    identity=subprocess.run([sys.executable,str(HERE/'remote_identity.py'),owner,proof['slug'].split('/')[1]],
        capture_output=True,encoding='utf-8',errors='replace',timeout=120)
    if identity.returncode:raise ValueError('saved identity lookup failed: '+identity.stderr)
    saved=json.loads(identity.stdout)
    source=(ROOT/proof['stage']/'run.py').read_text(encoding='utf-8')
    import hashlib
    if saved['source_sha256']!=hashlib.sha256(source.replace('\r\n','\n').encode()).hexdigest():
        raise ValueError('cloud saved code differs')
    write_new(out/'verification.json',dict(utc=now(),saved_code_matches=True,params_matches=True,
        bank_and_split_match=True,receipt=pin(out/'effect_release.json'),done=done,
        remote_identity=saved,
        outputs_remain_on_cloud=True,output_arrays_independently_rehashed=False,
        model_fit=False,claims_complete_corpus=False))
    print(json.dumps(dict(unit=unit,targets=done['targets'],contexts=done['contexts'],
        seconds=receipt['seconds'],bank_cells=receipt['bank_cells'],target_cells=receipt['target_cells_contributing'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('launch');a.add_argument('revision');a.add_argument('preflight',type=Path);a.add_argument('units',nargs='+');a.add_argument('--public',action='store_true')
    a=sub.add_parser('collect');a.add_argument('revision');a.add_argument('unit');a.add_argument('attempt')
    a=sub.add_parser('verify');a.add_argument('revision');a.add_argument('unit');a.add_argument('out',type=Path)
    a=p.parse_args()
    if a.command=='launch':launch(a.revision,a.units,a.preflight,a.public)
    elif a.command=='collect':collect(a.revision,a.unit,a.attempt)
    else:verify(a.revision,a.unit,a.out)
