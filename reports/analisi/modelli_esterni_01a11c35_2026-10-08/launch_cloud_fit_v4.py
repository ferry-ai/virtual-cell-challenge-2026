"""One-shot private dispatch with frozen package, fresh slots and a durable lock."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'))
from cloud_campaign import call, CONFIG


def write_new(path, data):
    with Path(path).open('x',encoding='utf-8') as f: json.dump(data,f,indent=1)


def main(prepared_path, preflight_path, access_path):
    prepared=json.loads(prepared_path.read_text())
    access=json.loads(access_path.read_text())
    if access['status'] != 'PASS' or access['prepared_sha256'] != sha256(prepared_path):
        raise ValueError('native sources inaccessible from destination')
    if not 0 <= (datetime.now(timezone.utc)-datetime.fromisoformat(access['utc'])).total_seconds() <= 900:
        raise ValueError('fresh destination source access required')
    pre=json.loads(preflight_path.read_text())
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    slug=prepared['slug'];owner=slug.split('/')[0];stage=Path(prepared['stage'])
    if owner not in CONFIG: raise ValueError('unconfigured destination')
    active = pre['active'][owner]
    # Include launches accepted or uncertain since the immutable snapshot.
    for lock_path in HERE.glob('esm2-*.launch.lock'):
        prior = json.loads(lock_path.read_text(encoding='utf-8'))
        if (prior['slug'].startswith(owner + '/') and
                datetime.fromisoformat(prior['utc']) > datetime.fromisoformat(pre['utc'])):
            active += 1
    if not 0 <= age <= 900 or active >= pre['slot_limit_per_account']-1:
        raise ValueError('fresh available slot required')
    if not slug.startswith(owner+'/esm2-') or not prepared['private']:
        raise ValueError('authorized private destination differs')
    for name,key in [('run.py','code_sha256'),('kernel-metadata.json','metadata_sha256')]:
        if sha256(stage/name)!=prepared[key]:raise ValueError('prepared artifact mutated')
    meta=json.loads((stage/'kernel-metadata.json').read_text())
    if meta['id']!=slug or meta['is_private'] is not True or meta['enable_gpu']:
        raise ValueError('private CPU metadata required')
    rc,lookup=call(owner,['kernels','list','--mine','--search',slug.split('/')[1],'--csv'])
    if rc or slug in lookup:raise ValueError('duplicate lookup failed or job already exists')
    # No uncertain push is retried under the same identity.
    lock=HERE/(prepared['job_id']+'.launch.lock')
    write_new(lock,dict(utc=datetime.now(timezone.utc).isoformat(),slug=slug,
        prepared_sha256=sha256(prepared_path),slots_sha256=sha256(preflight_path),
        human_fit_message='explicit C/J approval in this chat: call_19aa555691d3489b86f2cb1e6acd364e item 0',
        human_transfer_message='User explicitly requests other Kaggle accounts in this chat; private route chosen'))
    env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env.update(KAGGLE_CONFIG_DIR=str(Path.home()/CONFIG[owner]),PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    response=subprocess.run([sys.executable,str(HERE/'push_private_v2.py'),str(stage)],env=env,
        capture_output=True,encoding='utf-8',errors='replace',timeout=300)
    rc,answer=response.returncode,response.stdout
    accepted=rc==0 and 'successfully pushed' in answer
    # Do not persist provider error text: private source includes temporary locators.
    write_new(HERE/(prepared['job_id']+'.launch.json'),dict(slug=slug,returncode=rc,
        accepted=accepted,sanitized_answer=answer,utc=datetime.now(timezone.utc).isoformat()))
    print(answer,flush=True)
    print(json.dumps(dict(slug=slug,accepted=accepted,returncode=rc)),flush=True)
    if not accepted:raise RuntimeError('push not confirmed; inspect safe status before any new attempt')
    rc,status=call(owner,['kernels','status',slug])
    write_new(HERE/(prepared['job_id']+'.status_r1.json'),dict(returncode=rc,status=status,
        utc=datetime.now(timezone.utc).isoformat()))
    print(status,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--preflight',type=Path,required=True)
    p.add_argument('--source-preflight',type=Path,required=True)
    a=p.parse_args();main(a.prepared,a.preflight,a.source_preflight)
