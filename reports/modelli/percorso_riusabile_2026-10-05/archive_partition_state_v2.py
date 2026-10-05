"""Copy the frozen validator, resolving parts by unit/index across both account ledgers."""
from pathlib import Path


if __name__=='__main__':
    source=Path(__file__).with_name('archive_partition_state_v1.py').read_text()
    old="    records=[r for r in map(json.loads,ledger.read_text().splitlines()) if r['accepted']]"
    new="""    ledgers=[ledger,HERE/'hipsci_shared_r1/launches.jsonl']
    records=[r for log in ledgers if log.exists() for r in map(json.loads,log.read_text().splitlines()) if r['accepted']]
    assigned={(r['unit'],r['partition']['part']):r['slug'] for r in records}
    if len(assigned)!=len(records):raise ValueError('duplicate part across accounts')"""
    if source.count(old)!=1:raise ValueError('frozen validator differs')
    source=source.replace(old,new)
    old="        done=[jobs[r['slug']] for r in plan if jobs.get(r['slug'],{}).get('state')=='remote_complete_manifest_checked']"
    new="        done=[jobs[assigned[(r['unit'],r['partition']['part'])]] for r in plan if jobs.get(assigned.get((r['unit'],r['partition']['part']),''),{}).get('state')=='remote_complete_manifest_checked']"
    if source.count(old)!=1:raise ValueError('frozen union resolver differs')
    source=source.replace(old,new)
    exec(compile(source,'archive_partition_state_v2.py','exec'),{'__name__':'__main__','__file__':__file__})
