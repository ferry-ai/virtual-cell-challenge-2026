"""Launch distinct prepared archive derivatives once, with a shared capacity snapshot."""
import json
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from launch_samples_r2 import preflight
from launch_samples import call

def main():
 plan=HERE/'parallel_archives_r1';ledger=plan/'launches.jsonl'
 if ledger.exists():raise ValueError('launch ledger exists; inspect it and resume only missing identities')
 active=preflight(plan/'preflight_launch.json');observed=json.loads((plan/'preflight_launch.json').read_text())['observed']
 jobs=[r for r in json.loads((plan/'assignments.json').read_text())['assignments'] if r['provider']=='kaggle']
 prepared=[]
 for job in jobs:
  stage=Path(job['stage']);frozen=json.loads((stage/'prepared.json').read_text());meta=json.loads((stage/'kernel-metadata.json').read_text())
  if sha(stage/'run.py')!=frozen['code_sha256'] or sha(stage/'kernel-metadata.json')!=frozen['metadata_sha256']:raise ValueError('stage changed')
  if any(r['job']==meta['id'] for r in observed):raise ValueError('existing job: '+meta['id'])
  prepared.append((job,stage,frozen,meta))
 for job,stage,frozen,meta in prepared:
  owner=job['owner']
  if active.get(owner,0)>=5:raise ValueError('CPU slots full: '+owner)
  rc,answer=call(owner,['kernels','push','-p',str(stage)])
  ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
  record={'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'accepted':ok,
   'answer':answer,'stage':str(stage),'code_sha256':frozen['code_sha256'],'source':job['slug']}
  with ledger.open('a') as f:f.write(json.dumps(record)+'\n')
  print(json.dumps(record),flush=True)
  if not ok:raise RuntimeError('push rejected; inspect ledger before any retry')
  active[owner]=active.get(owner,0)+1

if __name__=='__main__':main()
