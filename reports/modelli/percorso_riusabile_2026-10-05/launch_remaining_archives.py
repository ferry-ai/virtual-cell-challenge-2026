"""Fill newly freed accessible slots with the remaining admitted archived source jobs."""
import json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG
from launch_samples_r2 import preflight
from launch_samples import call
from launch_public_fallback import probe

SLUGS=['rlab-kolf-small','rlab-kolf-strong','rlab-hipsci-gwfit','rlab-hipsci-gwnonfit']

def main():
 out=HERE/'remaining_archives_r1';out.mkdir(exist_ok=False);active=preflight(out/'preflight.json')
 existing={r['job'] for r in json.loads((out/'preflight.json').read_text())['observed']};access=[];pending=[]
 for slug in SLUGS:
  owner=None
  for candidate in ['davideferrante11','davidmaisterx','davideferante']:
   if active.get(candidate,0)>=5:continue
   r=subprocess.run([sys.executable,__file__,'--probe',slug],env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[candidate])},
    capture_output=True,text=True,timeout=45)
   access.append({'account':candidate,'source':slug,'access':r.returncode==0})
   if r.returncode==0:owner=candidate;break
  if owner is None:pending.append({'source':slug,'reason':'no accessible free slot'});continue
  stage=out/slug
  r=subprocess.run([sys.executable,str(HERE/'prepare_archive_derivatives.py'),'--slug',slug,'--owner',owner,'--out',str(stage)],capture_output=True,text=True)
  if r.returncode:raise RuntimeError('preparation failed: '+r.stderr[-500:])
  meta=json.loads((stage/'kernel-metadata.json').read_text());frozen=json.loads((stage/'prepared.json').read_text())
  if meta['id'] in existing:raise ValueError('duplicate derivative')
  rc,answer=call(owner,['kernels','push','-p',str(stage)])
  ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
  record={'utc':datetime.now(timezone.utc).isoformat(),'source':slug,'slug':meta['id'],'accepted':ok,'answer':answer,
   'code_sha256':frozen['code_sha256'],'stage':str(stage)}
  with (out/'launches.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
  print(json.dumps({'slug':meta['id'],'accepted':ok}),flush=True)
  if not ok:raise RuntimeError('push rejected; inspect ledger')
  active[owner]=active.get(owner,0)+1
 (out/'state.json').write_text(json.dumps({'access':access,'pending':pending,
  'not_queued':{'rlab-jurkat-gse249595':'guide/target calls absent; keep raw and reconcile legitimate training role before derivatives'}},indent=1))

if __name__=='__main__':
 if sys.argv[1:2]==['--probe']:print(json.dumps(probe(sys.argv[2])))
 else:main()
