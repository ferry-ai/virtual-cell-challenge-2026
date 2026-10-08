"""Bounded dispatch of the explicitly authorised 41+41 unit campaign.

No failed launch is retried. Third-account outputs stay private. One slot per
account remains unallocated by this worker. Every wave checks all three accounts.
"""
import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import time
from cloud_campaign import call, collect, launch,KINDS
from percorso import BANK,HERE,now,read,write_new


def main(name,max_waves,include_joint=False,plan=None):
    root=HERE/'dispatch'/name;root.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('canonical_dispatch',BANK/'percorso.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    tasks=[];production=[];target_fold=[]
    for revision in ['01a11c34-r3','01a11c34-r4private','01a11c34-tj1']:
        for unit,entry in read(HERE/'alltargets'/revision/'inventory.json')['units'].items():
            if entry['state']=='package_ready':
                (target_fold if revision.endswith('tj1') else production).append(('alltargets',revision,unit))
    joint_production=[];joint_fold=[]
    if include_joint:
        for item in read(HERE/'joint/inventory_r1.json')['packages']:
            revision=Path(item['stage']).parts[-3]
            (joint_production if item['regime']=='production' else joint_fold).append(('joint',revision,item['policy']))
    tasks=joint_production+production+joint_fold+target_fold
    visibility={}
    if plan is not None:
        tasks=[]
        for task in read(plan)['tasks']:
            key=(task['kind'],task['revision'],task['unit'])
            if key[0] not in KINDS or key in visibility:raise ValueError('invalid dispatch plan')
            if any('/' in part or '\\' in part or part in {'.','..'} for part in key):raise ValueError('invalid plan path')
            tasks.append(key);visibility[key]=task['public']
    known_active={};failures=[]
    # Restore previously observed active jobs across controller restarts.
    for history in sorted((HERE/'dispatch').glob('*/slots_*.json'),key=lambda p:p.stat().st_mtime):
        for r in read(history)['observed']:
            if r['returncode'] or any(s in r['status'] for s in ('RUNNING','QUEUED')):
                known_active[r['job']]=r['owner']
            else:known_active.pop(r['job'],None)
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
        for kind,revision,unit in tasks:
            dest=HERE/kind/revision/unit
            if any(dest.glob('completion_*/verification.json')):continue
            result=dest/'launch_result.json'
            proof=read(dest/'prepared.json');owner=proof['owner'];slug=proof['slug']
            if result.exists():
                if not read(result)['accepted']:continue
                status=observed.get(slug)
                if not status:
                    rc,body=call(owner,['kernels','status',slug]);status=dict(returncode=rc,status=body)
                if status['returncode'] or any(s in status['status'] for s in ('ERROR','CANCEL')):
                    if (kind,revision,unit) not in failures:
                        failures.append((kind,revision,unit));write_new(root/('failure_%s_%s.json'%(revision,unit)),status)
                    continue
                if 'COMPLETE' in status['status']:
                    collect(revision,unit,'%s_w%03d'%(name,wave),kind);continue
                remaining.append((kind,revision,unit,'running'));continue
            if (dest/'launch.lock').exists():
                failures.append((kind,revision,unit));continue
            remaining.append((kind,revision,unit,'unlaunched'))
        free={o:max(0,4-pre['active'].get(o,0)) for o in old.CONFIG}
        for kind,revision,unit,state in remaining:
            if state!='unlaunched':continue
            dest=HERE/kind/revision/unit;owner=read(dest/'prepared.json')['owner']
            if free[owner]<=0:continue
            # A failing save stops this worker for diagnosis, never reroutes an account.
            launch(revision,[unit],augmented,public=visibility.get((kind,revision,unit),owner!='davideferante'),kind=kind)
            free[owner]-=1
        write_new(root/('wave_%03d.json'%wave),dict(utc=now(),remaining=remaining,failures=failures,
            private_account='davideferante',reserved_slots_per_account=1))
        print('wave',wave,'remaining',len(remaining),'failures',len(failures),flush=True)
        if not remaining:break
        time.sleep(20)
    write_new(root/'finished.json',dict(utc=now(),failures=failures,waves=wave+1,
        all_successful_tasks_collected=not remaining,not_a_model_or_score=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('name');p.add_argument('--max-waves',type=int,default=20);p.add_argument('--include-joint',action='store_true')
    p.add_argument('--plan',type=Path)
    a=p.parse_args();main(a.name,a.max_waves,a.include_joint,a.plan)
