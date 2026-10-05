"""Place unlaunched partitions on two accounts, checking all private inputs first."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from launch_samples import call
from launch_samples_r2 import preflight
from pipeline_state import CONFIG

HERE = Path(__file__).resolve().parent


def identity(record):
    p = record['parameters']
    return p['bank_receipt_sha256'], p['unit'], p['part'], p['parts']


def main():
    cli = argparse.ArgumentParser(); cli.add_argument('--launch', action='store_true')
    cli.add_argument('--out', type=Path, required=True)
    cli.add_argument('--units', nargs='+', help='Only dispatch these frozen units')
    args=cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    log = HERE/'other_sample_launches.jsonl'
    prior = [json.loads(x) for x in log.read_text().splitlines()]
    attempted = {identity(r) for r in prior}
    owners = ['davidmaisterx','davideferante']; assigned = Counter(); plan=[]
    for source in sorted((HERE/'other_sample_stages').iterdir()):
        frozen = json.loads((source/'prepared.json').read_text())
        if args.units and frozen['parameters']['unit'] not in args.units: continue
        if identity(frozen) in attempted: continue
        code=(source/'run.py').read_text(encoding='utf-8')
        if hashlib.sha256(code.encode()).hexdigest()!=frozen['code_sha256']:
            raise ValueError('frozen code changed')
        owner=min(owners, key=lambda o:assigned[o]); assigned[owner]+=1
        slug=owner+'/'+frozen['metadata']['id'].split('/')[1]
        meta={**frozen['metadata'],'id':slug}
        stage=args.out/meta['title']; stage.mkdir()
        (stage/'run.py').write_text(code,encoding='utf-8')
        (stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
        plan.append({**frozen,'metadata':meta,'slug':slug,'stage':str(stage),
                     'original_stage':str(source)})
    (args.out/'plan.json').write_text(json.dumps(plan,indent=1))
    access = {owner:sorted({job for r in plan if r['slug'].split('/')[0]==owner
                           for job in r['metadata']['kernel_sources']}) for owner in owners}
    (args.out/'required_access.json').write_text(json.dumps(access,indent=1))
    print(json.dumps({'prepared':len(plan),'per_account':dict(assigned)}),flush=True)
    if not args.launch: return
    active=preflight(args.out/'preflight.json')
    observed={r['job'] for r in json.loads((args.out/'preflight.json').read_text())['observed']}
    for owner, jobs in access.items():
        if not jobs: continue
        r=subprocess.run([sys.executable,str(HERE/'probe_input_access.py'),'--account',owner,
                          '--jobs',*jobs,'--out',str(args.out/(owner+'_access.json'))],
                         capture_output=True,encoding='utf-8',errors='replace',timeout=180)
        if r.returncode: raise RuntimeError('access verification failed')
        checked=json.loads((args.out/(owner+'_access.json')).read_text())
        if not all(j['output_listing_access'] for j in checked['jobs']):
            raise ValueError('sharing not ready for '+owner)
    for record in plan:
        owner=record['slug'].split('/')[0]
        if record['slug'] in observed: raise ValueError('unreconciled existing remote job')
        if active[owner]>=5: continue
        # Re-read the common ledger immediately before each mutation.
        if identity(record) in {identity(json.loads(s)) for s in log.read_text().splitlines()}: continue
        rc,answer=call(owner,['kernels','push','-p',record['stage']])
        ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
        record.update(accepted=ok,answer=answer,utc=datetime.now(timezone.utc).isoformat())
        with log.open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
        print(json.dumps({'slug':record['slug'],'accepted':ok}),flush=True)
        if not ok:raise RuntimeError(answer)
        active[owner]+=1


if __name__=='__main__':main()
