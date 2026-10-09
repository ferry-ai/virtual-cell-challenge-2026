"""One-shot private CPU launch: exact package, fresh access, immutable intent/lock."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from cloud_campaign import call
from percorso import HERE, read, write_new, now, pin, sha


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ('prepared','preflight','authorization','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--slug',required=True);a=p.parse_args()
    prepared,pre,authorization=read(a.prepared),read(a.preflight),read(a.authorization)
    if a.slug not in authorization['jobs']:raise ValueError('job not in scoped authorization record')
    if authorization['paid_services'] or authorization['public_outputs']:raise ValueError('private CPU scope only')
    if sha(a.prepared)!=pre['prepared']['sha256']:raise ValueError('preflight package differs')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    if not 0<=age<900:raise ValueError('fresh preflight required')
    job=next(j for j in prepared['jobs'] if j['slug']==a.slug);owner=a.slug.split('/')[0]
    account=next(x for x in pre['accounts'] if x['owner']==owner)
    if account.get('error') or account.get('list_error'):raise ValueError('account preflight failed')
    meta=read(job['metadata']['path'])
    if not meta['is_private'] or meta['enable_gpu'] or meta['enable_tpu']:raise ValueError('private CPU required')
    checks={(x['kind'],x['ref']):x for x in account['sources']}
    for kind,field in [('kernel','kernel_sources'),('dataset','dataset_sources')]:
        for ref in meta[field]:
            if not checks[(kind,ref)]['native_admissible']:raise ValueError('source access rejected')
    active=account['active_or_unknown']
    for intent in (HERE/'neural_launches').glob('*/*/launch_intent.json'):
        saved=read(intent)
        if saved['owner']==owner and saved['utc']>pre['utc']:active+=1
    if active>=pre['slot_limit_per_account']-pre['reserve_slots']:raise ValueError('no observed slot')
    for field in ('code','metadata'):
        if sha(job[field]['path'])!=job[field]['sha256']:raise ValueError('package changed')
    rc,body=call(owner,['kernels','list','--mine','--search',a.slug.split('/')[1],'--csv'])
    if rc or a.slug in body:raise ValueError('duplicate or dedup lookup failed')
    a.out.mkdir(parents=True,exist_ok=False)
    with (a.out/'launch.lock').open('x') as f:f.write(now())
    write_new(a.out/'launch_intent.json',dict(utc=now(),owner=owner,slug=a.slug,
        prepared=pin(a.prepared),preflight=pin(a.preflight),authorization=pin(a.authorization),
        code=job['code'],metadata=job['metadata']))
    rc,body=call(owner,['kernels','push','-p',job['stage']])
    accepted=rc==0 and 'successfully pushed' in body
    write_new(a.out/'launch_result.json',dict(utc=now(),returncode=rc,answer=body,accepted=accepted))
    print(json.dumps(dict(slug=a.slug,accepted=accepted)),flush=True)
    if not accepted:raise RuntimeError('push not accepted; inspect saved receipt before another attempt')
    rc,state=call(owner,['kernels','status',a.slug])
    write_new(a.out/'status_after_push.json',dict(utc=now(),returncode=rc,answer=state))
    print(state,flush=True)


if __name__=='__main__':main()
