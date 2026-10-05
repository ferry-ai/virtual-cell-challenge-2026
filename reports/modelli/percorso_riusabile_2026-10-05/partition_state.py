"""Verify persisted sample parts and full unions using small receipts only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from pipeline_state import CONFIG, REPO, command, sha

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'ibrido_esecuzione_2026-10-04'))
sys.path.insert(0,str(HERE.parent/'ibrido_pseudobulk_2026-10-04'))
from materialize_partition import verify_union


def validate(record,remote,bank):
    p=record['parameters']; unit=p['unit']
    if remote['saved_version']['saved_source_sha256']!=record['code_sha256']:
        raise ValueError('saved part code changed')
    received=remote['receipts'][unit]; s=received['value']
    parent=REPO/bank['receipt']
    if sha(parent)!=bank['receipt_sha256']:raise ValueError('parent receipt changed')
    original=json.loads(parent.read_text())
    if (not s['complete'] or s['complete_unit'] or s['unit']!=unit or s['genes']!=18533
        or s['bank_receipt_sha256']!=bank['receipt_sha256']
        or s['bank_receipt_sha256']!=p['bank_receipt_sha256']
        or s['source_verification']!=original['source_verification']
        or s['part']!=p['part'] or s['parts']!=p['parts']
        or s['partition_rule']!='source_index % parts'
        or s['total_sources']!=len(original['sources'])
        or s['source_indices']!=list(range(p['part'],len(original['sources']),p['parts']))
        or s['global_levels']['128']!=original['samples128']):
        raise ValueError('partition identity/coverage changed')
    levels=s['levels']
    if set(levels)!={'32','64','128'} or not 0 < levels['32'] <= levels['64'] <= levels['128'] <= s['global_levels']['128']:
        raise ValueError('invalid partition sample counts')
    for name,parent_name in [('bank_rows.csv','rows.csv'),('mask.npz','mask.npz')]:
        if s['files'][name]!=original['files'][parent_name]:raise ValueError('rows/mask changed')
    matrices={n:v for n,v in s['files'].items() if n.startswith('shard_') and n.endswith('.npz')}
    if sum(v['cells'] for v in matrices.values())!=levels['128']:raise ValueError('sample count mismatch')
    for name,info in s['files'].items():
        if Path(name).name!=name or 'samples/'+unit+'/'+name not in remote['files']:
            raise ValueError('sample output missing')
        if name in matrices:
            fi=int(name[6:-4])
            if fi not in s['source_indices'] or info['source_file']!=original['sources'][fi]['file']:
                raise ValueError('raw source partition mismatch')
            partner=s['files'][name[:-4]+'.jsonl.gz']
            if any(partner[k]!=info[k] for k in ('source_file','source_sha256','cells')):
                raise ValueError('matrix/metadata lineage mismatch')
    return {'state':'remote_complete_manifest_checked','kernel':record['slug'],
            'receipt':received['path'],'receipt_sha256':received['sha256'],
            'saved_version':remote['saved_version'],'part':s['part'],'parts':s['parts'],
            'levels':levels,'bytes':sum(v['bytes'] for v in s['files'].values()),
            'consumer_hashes_verified':False,'training_used':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--previous',type=Path);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    records=[r for r in map(json.loads,(HERE/'other_sample_launches.jsonl').read_text().splitlines()) if r['accepted']]
    keys=[(r['parameters']['unit'],r['parameters']['part']) for r in records]
    if len(set(keys))!=len(keys):raise ValueError('duplicate part across accounts')
    banks=json.loads((HERE/'snapshot_other_r2/state.json').read_text())['units']
    previous=json.loads(a.previous.read_text())['parts'] if a.previous else {}
    statuses=list(ThreadPoolExecutor(5).map(lambda r:command(r['slug'],['status']),records))
    parts={};units={}
    for record,status in zip(records,statuses):
        job=record['slug'];item={'kernel':job,'state':'not_complete','status':status}
        if job in previous and previous[job]['state']=='remote_complete_manifest_checked':
            old=previous[job]
            if sha(REPO/old['receipt'])!=old['receipt_sha256']:raise ValueError('previous receipt changed')
            item.update(old,reused_verification=True)
        elif status['returncode']==0 and 'KernelWorkerStatus.COMPLETE' in status['text']:
            owner=job.split('/')[0]
            r=subprocess.run([sys.executable,str(HERE/'sample_state.py'),'--fetch',job,str(out)],
                env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])},
                capture_output=True,encoding='utf-8',errors='replace',timeout=180)
            if r.returncode:raise RuntimeError('part receipt recovery failed: '+job)
            item.update(validate(record,json.loads(r.stdout),banks[record['parameters']['unit']]))
        parts[job]=item
    for unit in banks:
        accepted=[r for r in records if r['parameters']['unit']==unit]
        done=[parts[r['slug']] for r in accepted if parts[r['slug']]['state']=='remote_complete_manifest_checked']
        expected=next((r['parameters']['parts'] for r in accepted),None)
        entry={'expected_parts':expected,'launched_parts':len(accepted),'verified_parts':len(done),'state':'incomplete'}
        if expected and len(done)==expected:
            receipts=[json.loads((REPO/r['receipt']).read_text()) for r in done]
            entry.update(state='remote_complete_union_checked',levels=verify_union(receipts),bytes=sum(r['bytes'] for r in done))
        units[unit]=entry
    (out/'state.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'parts':parts,'units':units,'training_ready':False},indent=1))
    print(json.dumps(units))


if __name__=='__main__':main()
