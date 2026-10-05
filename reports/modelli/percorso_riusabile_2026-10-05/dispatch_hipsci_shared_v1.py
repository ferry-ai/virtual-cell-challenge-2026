"""Dispatch disjoint pending partitions across accessible accounts, after public sharing."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from launch_samples import call
from launch_samples_r2 import preflight


def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);a=p.parse_args()
    out=HERE/'hipsci_shared_r1';out.mkdir(exist_ok=True);ledger=out/'launches.jsonl'
    previous=[]
    for path in (HERE/'hipsci_partition_r1/launches.jsonl',ledger):
        if path.exists():previous += [json.loads(x) for x in path.read_text().splitlines()]
    if any(not r['accepted'] for r in previous):raise ValueError('unresolved push outcome')
    used={(r['unit'],r['partition']['part']) for r in previous}
    if len(used)!=len(previous):raise ValueError('duplicate part across accounts')
    snap=out/('preflight_'+a.snapshot+'.json');active=preflight(snap)
    observed={r['job'] for r in json.loads(snap.read_text())['observed']}
    plans=[json.loads((HERE/'hipsci_partition_r1'/name/'plan.json').read_text()) for name in ('rlab-hipsci-gwfit','rlab-hipsci-gwnonfit')]
    access={};new=[];pending=[]
    for i in range(12):
        for plan in plans:
            r=plan[i];key=(r['unit'],r['partition']['part'])
            if key in used:continue
            owner=None;raw=json.loads((Path(r['stage'])/'kernel-metadata.json').read_text())['dataset_sources'][0]
            for candidate in ('davideferrante11','davideferante','davidmaisterx'):
                if active.get(candidate,0)>=5:continue
                pair=candidate+'|'+raw
                if pair not in access:
                    rc,answer=call(candidate,['datasets','files',raw,'--csv']);access[pair]=rc==0
                if access[pair]:owner=candidate;break
            if owner is None:pending.append(key);continue
            src=Path(r['stage']);dest=out/owner/(r['unit']+'_p'+str(i));dest.parent.mkdir(exist_ok=True)
            if dest.exists():raise ValueError('stage without accepted ledger; inspect before reuse')
            shutil.copytree(src,dest)
            meta=json.loads((dest/'kernel-metadata.json').read_text());meta['id']=owner+'/'+meta['id'].split('/')[1]
            if meta['id'] in observed:raise ValueError('unknown existing remote identity')
            (dest/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
            if sha(dest/'run.py')!=r['code_sha256']:raise ValueError('calculation code changed')
            rc,answer=call(owner,['kernels','push','-p',str(dest)])
            ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
            record={**r,'slug':meta['id'],'stage':str(dest.resolve()),'utc':datetime.now(timezone.utc).isoformat(),
                    'accepted':ok,'answer':answer,'original_planned_slug':r['slug']}
            with ledger.open('a') as f:f.write(json.dumps(record)+'\n')
            if not ok:raise RuntimeError('push rejected; inspect ledger')
            used.add(key);new.append(meta['id']);active[owner]=active.get(owner,0)+1
    (out/('dispatch_'+a.snapshot+'.json')).write_text(json.dumps({'accepted':new,'pending':pending,'access':access},indent=1))
    print(json.dumps({'accepted':new,'pending':len(pending)}))


if __name__=='__main__':main()
