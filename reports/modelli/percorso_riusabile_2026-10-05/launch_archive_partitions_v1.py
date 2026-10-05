"""Fill only free owner slots with disjoint HIPSCI output partitions; resumable ledger."""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from pipeline_state import HERE, sha
from launch_samples_r2 import preflight
from launch_samples import call
from archive_partition_v1 import prepare


def main():
    p=argparse.ArgumentParser(); p.add_argument('--snapshot', required=True); a=p.parse_args()
    out=HERE/'hipsci_partition_r1'; out.mkdir(exist_ok=True)
    for name in ('rlab-hipsci-gwfit','rlab-hipsci-gwnonfit'):
        target=out/name
        if not target.exists(): prepare(HERE/'remaining_archives_r1'/name,target,parts=12)
    ledger=out/'launches.jsonl'
    prior=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
    if any(not r['accepted'] for r in prior): raise ValueError('unresolved push outcome; inspect before resume')
    snapshot=out/('preflight_'+a.snapshot+'.json'); active=preflight(snapshot)
    observed={r['job'] for r in json.loads(snapshot.read_text())['observed']}
    already={r['slug'] for r in prior}; pending=[]; accepted=[]
    plans={n:json.loads((out/n/'plan.json').read_text()) for n in ('rlab-hipsci-gwfit','rlab-hipsci-gwnonfit')}
    # Alternate sources, so both failed units make progress.
    for i in range(12):
        for name,plan in plans.items():
            r=plan[i]
            if r['slug'] in already: continue
            if r['slug'] in observed: raise ValueError('remote identity without accepted ledger; inspect')
            if active.get('davidmaisterx',0)>=5: pending.append(r['slug']); continue
            stage=Path(r['stage'])
            if sha(stage/'run.py')!=r['code_sha256']: raise ValueError('frozen code changed')
            rc,answer=call('davidmaisterx',['kernels','push','-p',str(stage)])
            ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
            record={**r,'utc':datetime.now(timezone.utc).isoformat(),'accepted':ok,'answer':answer}
            with ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
            if not ok: raise RuntimeError('push failed; stop to inspect outcome')
            accepted.append(r['slug']); active['davidmaisterx']=active.get('davidmaisterx',0)+1
    (out/('dispatch_'+a.snapshot+'.json')).write_text(json.dumps({'accepted':accepted,'pending':pending},indent=1))
    print(json.dumps({'accepted':accepted,'pending':len(pending)}))


if __name__=='__main__': main()
