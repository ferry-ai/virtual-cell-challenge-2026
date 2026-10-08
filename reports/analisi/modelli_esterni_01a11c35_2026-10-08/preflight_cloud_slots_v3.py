"""Account-isolated SDK inventory; unknown states reserve capacity conservatively."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from source_access_preflight import CONFIG


def account(owner):
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    refs=[k.ref for k in api.kernels_list(mine=True,page_size=50,sort_by='dateRun')]
    def status(slug):
        try:
            state=str(api.kernels_status(slug).status).split('.')[-1]
            return dict(owner=owner,job=slug,status=state,returncode=0)
        except Exception as exc:
            return dict(owner=owner,job=slug,status='UNKNOWN',returncode=1,error_type=type(exc).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(status,refs))


def snapshot(out):
    if out.exists():raise FileExistsError(out)
    def child(owner):
        env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
        env.update(KAGGLE_CONFIG_DIR=str(Path.home()/CONFIG[owner]),PYTHONUTF8='1')
        r=subprocess.run([sys.executable,__file__,'--owner',owner],env=env,capture_output=True,text=True,timeout=600)
        if r.returncode:
            return [dict(owner=owner,job=None,status='UNKNOWN_LIST',returncode=1,reserved_slots=5)]
        return json.loads(r.stdout)
    with ThreadPoolExecutor(max_workers=3) as pool:
        observed=[x for rows in pool.map(child,CONFIG) for x in rows]
    active={owner:sum(r.get('reserved_slots',1) for r in observed if r['owner']==owner and
                     (r['returncode'] or r['status'] not in ('COMPLETE','ERROR','CANCELLED'))) for owner in CONFIG}
    unknown=[r for r in observed if r['returncode'] or r['status'] not in ('COMPLETE','ERROR','CANCELLED','RUNNING','QUEUED')]
    dispatcher=Path('G:/Il mio Drive/vcc2026/runs/jobs/dispatcher.log')
    colab=dict(accessible=dispatcher.is_file(),live_verified=False)
    if dispatcher.is_file():colab['file_mtime_utc']=datetime.fromtimestamp(dispatcher.stat().st_mtime,timezone.utc).isoformat()
    result=dict(utc=datetime.now(timezone.utc).isoformat(),scope='50 most recently run per account',
        observed=observed,active=active,unknown_reserved_as_active=unknown,slot_limit_per_account=5,
        slot_policy='existing campaign ceiling; keep one slot free; unknowns consume capacity',
        quota_remaining='not exposed by this check',colab=colab)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=1)
    print(json.dumps(dict(utc=result['utc'],active=active,unknown_count=len(unknown),colab=colab)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--owner',choices=list(CONFIG));p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.owner:
        try:print(json.dumps(account(a.owner)))
        except Exception as exc:print(json.dumps(dict(error_type=type(exc).__name__)));raise SystemExit(1)
    else:snapshot(a.out)
