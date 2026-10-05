"""Validate saved disjoint bank/sample parts and certify the complete union only."""
import argparse,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pipeline_state import HERE,REPO,CONFIG,command,sha
from pipeline_state_r2 import isolated_receipts
from sample_state import validate


def union(items):
    if not items:raise ValueError('no parts')
    proofs=[r['bank_value']['partition'] for r in items]
    count=proofs[0]['parts']; rows=proofs[0]['global_rows']; cells=proofs[0]['global_cells']
    if len(items)!=count or {r['part'] for r in proofs}!=set(range(count)):
        raise ValueError('incomplete or duplicated parts')
    for key in ('all_keys_sha256','global_rows','global_cells','parts','method'):
        if len({r[key] for r in proofs})!=1:raise ValueError('global population identity differs')
    if len({r['bank_value']['source_verification'] for r in items})!=1:raise ValueError('source changed')
    if any(r['bank_value']['rows']!=len(range(r['bank_value']['partition']['part'],rows,count)) for r in items):
        raise ValueError('partition row coverage differs')
    if sum(r['bank_value']['rows'] for r in items)!=rows or sum(r['bank_value']['cells_in'] for r in items)!=cells:
        raise ValueError('union population coverage differs')
    return {'state':'remote_complete_union_checked','rows':rows,'cells_in':cells,
            'all_keys_sha256':proofs[0]['all_keys_sha256'],'training_used':False,
            'consumer_hashes_verified':False,'cross_part_control_lookup_required':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--previous',type=Path)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False)
    ledger=HERE/'hipsci_partition_r1/launches.jsonl'
    records=[r for r in map(json.loads,ledger.read_text().splitlines()) if r['accepted']]
    if len({r['slug'] for r in records})!=len(records):raise ValueError('duplicate accepted identity')
    previous=json.loads(a.previous.read_text())['jobs'] if a.previous else {}
    def inspect(r):
        job=r['slug']
        if previous.get(job,{}).get('state')=='remote_complete_manifest_checked':
            old=previous[job]
            for obj in (old['bank'],old['samples']):
                if sha(REPO/obj['receipt'])!=obj['receipt_sha256']:raise ValueError('previous metadata changed')
            return job,old
        status=command(job,['status']);item={'state':'not_complete','status':status}
        if status['returncode'] or 'COMPLETE' not in status['text']:return job,item
        owner=job.split('/')[0]; receipts,files,version=isolated_receipts(owner,job,a.out/'bank_receipts')
        bank,path,digest=receipts[r['unit']]; part=bank['partition']
        if version['saved_source_sha256']!=r['code_sha256'] or any(part[k]!=r['partition'][k] for k in r['partition']):
            raise ValueError('partition code or identity differs')
        if (not bank['complete'] or part['global_cells']!=r['global_cells']
            or bank['cells_in']!=part['selected_cells'] or bank['cells_used']+bank['zero_depth_excluded']!=bank['cells_in']
            or bank['source_verification']!=r['raw_files_sha256']
            or not all('bank/'+r['unit']+'/'+n in files for n in bank['files'])):raise ValueError('bank coverage/lineage differs')
        b={'kernel':job,'receipt':path,'receipt_sha256':digest,'saved_version':version,
           'relative_path':'bank/'+r['unit'],'files':bank['files']}
        q=subprocess.run([sys.executable,str(HERE/'sample_state.py'),'--fetch',job,str(a.out)],
             env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])},capture_output=True,text=True,timeout=180)
        if q.returncode:raise RuntimeError('sample metadata retrieval failed')
        remote=json.loads(q.stdout)
        if remote['saved_version']!=version:raise ValueError('producer changed')
        s=validate({'parameters':{'unit':r['unit'],'bank_receipt_sha256':digest},'slug':job,
                    'code_sha256':r['code_sha256']},remote,{'bank':b});s['relative_path']='samples/'+r['unit']
        return job,{'state':'remote_complete_manifest_checked','bank':b,'bank_value':bank,'samples':s,'unit':r['unit']}
    with ThreadPoolExecutor(3) as pool: jobs=dict(pool.map(inspect,records))
    units={}
    for name in ('rlab-hipsci-gwfit','rlab-hipsci-gwnonfit'):
        plan=json.loads((HERE/'hipsci_partition_r1'/name/'plan.json').read_text())
        done=[jobs[r['slug']] for r in plan if jobs.get(r['slug'],{}).get('state')=='remote_complete_manifest_checked']
        units[plan[0]['unit']]={'expected_parts':len(plan),'verified_parts':len(done),'state':'incomplete'}
        if len(done)==len(plan):units[plan[0]['unit']].update(union(done))
    (a.out/'state.json').write_text(json.dumps({'jobs':jobs,'units':units,'training_ready':False},indent=1))
    print(json.dumps(units))


if __name__=='__main__':main()
