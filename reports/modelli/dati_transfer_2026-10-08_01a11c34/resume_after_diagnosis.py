"""Freeze the authorised corrected/private dispatch plan, without launching."""
from pathlib import Path
from percorso import HERE,ROOT,now,pin,read,write_new


def main():
    write_new(HERE/'joint/authorization_r2.json',dict(utc=now(),
        user_answer='Autorizzo i 9 rilanci privati',additional_attempts=9,
        remaining_unlaunched_from_first_authorization=3,
        scope=['01a11c34-j2p','01a11c34-j2t'],public=False,
        reason='Correct missing scratch parent; six-policy integration fixture passed',
        old_packages_retained=True))
    tasks=[]
    for item in read(HERE/'joint/inventory_r2.json')['packages']:
        tasks.append(dict(kind='joint',revision=Path(item['stage']).parts[-3],unit=item['policy'],public=False))
    replaced={u for u,e in read(HERE/'alltargets/01a11c34-tj2private/inventory.json')['units'].items() if e['state']=='package_ready'}
    for revision in ('01a11c34-r3','01a11c34-r4private','01a11c34-tj1','01a11c34-tj2private'):
        for unit,item in read(HERE/'alltargets'/revision/'inventory.json')['units'].items():
            if item['state']!='package_ready' or revision=='01a11c34-tj1' and unit in replaced:continue
            proof=read(HERE/'alltargets'/revision/unit/'prepared.json')
            tasks.append(dict(kind='alltargets',revision=revision,unit=unit,
                public=proof['owner']=='davidmaisterx'))
    write_new(HERE/'dispatch/plan_r5.json',dict(utc=now(),tasks=tasks,
        authorization=pin(HERE/'joint/authorization_r2.json'),
        existing_campaign_authorization='41 production plus 41 target-hidden units; no added unit compute',
        visibility='private on davideferrante11 and davideferante; public quota is not bypassed',
        public_limit_evidence=pin(HERE/'alltargets/01a11c34-tj1/D1_Rest/launch_result.json'),
        replaced_target_packages=sorted(replaced),retry_failed_launches=False))
    write_new(HERE/'dispatch/r3/controller_stopped.json',dict(utc=now(),local_process=13496,
        reason='Repeated scratch initialization error; stop new launches for diagnosis',cloud_jobs_cancelled=False))
    print(len(tasks),'explicit tasks; completed work will be skipped')


if __name__=='__main__':main()
