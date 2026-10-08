"""Bounded dispatch of the explicitly authorised 41+41 unit campaign.

No failed launch is retried. Third-account outputs stay private. One slot per
account remains unallocated by this worker. Every wave checks all three accounts.
"""
import argparse
from collections import Counter
import importlib.util
import time
from cloud_campaign import call, collect, launch
from percorso import BANK,HERE,now,read,write_new


def main(name,max_waves):
    root=HERE/'dispatch'/name;root.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('canonical_dispatch',BANK/'percorso.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    tasks=[]
    for revision in ['01a11c34-r3','01a11c34-r4private','01a11c34-tj1']:
        for unit,entry in read(HERE/'alltargets'/revision/'inventory.json')['units'].items():
            if entry['state']=='package_ready':tasks.append((revision,unit))
    known_active={};failures=[]
    for wave in range(max_waves):
        prepath=root/('preflight_%03d.json'%wave);old.preflight(prepath);pre=read(prepath)
        observed={r['job']:r for r in pre['observed']}
        # Carry forward active jobs that fall outside the provider's latest-20 window.
        for job,owner in known_active.items():
            if job not in observed:
                rc,body=call(owner,['kernels','status',job])
                observed[job]=dict(owner=owner,job=job,returncode=rc,status=body)
        known_active={r['job']:r['owner'] for r in observed.values()
            if r['returncode'] or any(s in r['status'] for s in ('RUNNING','QUEUED'))}
        pre.update(utc=now(),observed=list(observed.values()),active=dict(Counter(known_active.values())),
            scope='latest 20 per account plus previously observed active jobs')
        augmented=root/('slots_%03d.json'%wave);write_new(augmented,pre)
        remaining=[]
        for revision,unit in tasks:
            dest=HERE/'alltargets'/revision/unit
            if any(dest.glob('completion_*/verification.json')):continue
            result=dest/'launch_result.json'
            proof=read(dest/'prepared.json');owner=proof['owner'];slug=proof['slug']
            if result.exists():
                if not read(result)['accepted']:continue
                status=observed.get(slug)
                if not status:
                    rc,body=call(owner,['kernels','status',slug]);status=dict(returncode=rc,status=body)
                if status['returncode'] or any(s in status['status'] for s in ('ERROR','CANCEL')):
                    if (revision,unit) not in failures:
                        failures.append((revision,unit));write_new(root/('failure_%s_%s.json'%(revision,unit)),status)
                    continue
                if 'COMPLETE' in status['status']:
                    collect(revision,unit,'%s_w%03d'%(name,wave));continue
                remaining.append((revision,unit,'running'));continue
            if (dest/'launch.lock').exists():
                failures.append((revision,unit));continue
            remaining.append((revision,unit,'unlaunched'))
        free={o:max(0,4-pre['active'].get(o,0)) for o in old.CONFIG}
        for revision,unit,state in remaining:
            if state!='unlaunched':continue
            dest=HERE/'alltargets'/revision/unit;owner=read(dest/'prepared.json')['owner']
            if free[owner]<=0:continue
            # A failing save stops this worker for diagnosis, never reroutes an account.
            launch(revision,[unit],augmented,public=owner!='davideferante')
            free[owner]-=1
        write_new(root/('wave_%03d.json'%wave),dict(utc=now(),remaining=remaining,failures=failures,
            private_account='davideferante',reserved_slots_per_account=1))
        print('wave',wave,'remaining',len(remaining),'failures',len(failures),flush=True)
        if not remaining:break
        time.sleep(20)
    write_new(root/'finished.json',dict(utc=now(),failures=failures,waves=wave+1,
        all_successful_tasks_collected=not remaining,not_a_model_or_score=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('name');p.add_argument('--max-waves',type=int,default=20)
    a=p.parse_args();main(a.name,a.max_waves)
