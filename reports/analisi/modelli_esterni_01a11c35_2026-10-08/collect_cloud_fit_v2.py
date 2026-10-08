"""Fetch only explicitly whitelisted scientific outputs from a terminal private job."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main(prepared_path, out, receipt_path):
    prepared=json.loads(prepared_path.read_text())
    if out.exists() or receipt_path.exists():raise FileExistsError('new retrieval destination required')
    repo=Path(__file__).resolve().parents[3]
    if out.resolve().is_relative_to(repo):raise ValueError('large artifacts stay outside repository')
    slug=prepared['slug'];job=prepared['job_id']
    configs={'davideferrante11':'.kaggle-davideferrante11','davidmaisterx':'.kaggle','davideferante':'.kaggle-codex'}
    owner=slug.split('/')[0]
    if owner not in configs or not slug.startswith(owner+'/esm2-') or not prepared['private']:
        raise ValueError('private authorized job required')
    env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env.update(KAGGLE_CONFIG_DIR=str(Path.home()/configs[owner]),PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    cli=str(Path(sys.executable).with_name('kaggle.exe'))
    def call(args):
        return subprocess.run([cli,*args],env=env,capture_output=True,encoding='utf-8',errors='replace',timeout=600)
    status=call(['kernels','status',slug])
    if status.returncode or not any(s in status.stdout for s in ('KernelWorkerStatus.COMPLETE','KernelWorkerStatus.ERROR')):
        print(json.dumps(dict(terminal=False,status=status.stdout.strip(),returncode=status.returncode)));return
    names=['complete.json','resolution_receipt.json','package_preflight.json','chunk_preflight.json',
           'initial_resources.json','staging.json','real_smoke.json','fit/manifest.json','fit_manifest.json','store_manifest.json',
           'fit/ridge.npz','fit/native_predictions.npz','progress.jsonl','heartbeat.jsonl','failure.json']
    pattern='^'+re.escape(job)+'/('+'|'.join(re.escape(n) for n in names)+')$'
    # The SDK separately downloads the execution log; our job prints no locator values.
    result=call(['kernels','output',slug,'-p',str(out),'--file-pattern',pattern])
    actual=[str(p.relative_to(out)).replace('\\','/') for p in out.rglob('*') if p.is_file()]
    allowed={job+'/'+n for n in names}|{job+'.log'}
    if set(actual)-allowed:raise ValueError('provider returned an unexpected output; do not publish retrieval')
    report=dict(utc=datetime.now(timezone.utc).isoformat(),slug=slug,status=status.stdout.strip(),
                returncode=result.returncode,files=actual,out=str(out),whitelist=names,
                private_locators_requested=False,scientific_benefit='not_evaluated')
    with receipt_path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=1)
    print(json.dumps(report))
    if result.returncode:raise RuntimeError('whitelisted retrieval failed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args();main(a.prepared,a.out,a.receipt)
