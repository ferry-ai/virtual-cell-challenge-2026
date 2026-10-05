"""Reassign unstarted Colab work and HIPSCI after explicitly approved public access."""
import json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from launch_samples_r2 import preflight
from launch_samples import call

SLUGS=['rlab-scp-tcells','rlab-scp-k562-hek','rlab-tian-norman','rlab-hipsci-targeted19']

def probe(slug):
 from kaggle.api.kaggle_api_extended import KaggleApi
 a=KaggleApi();a.authenticate();files=a.dataset_list_files('davidmaisterx/'+slug,page_size=200).files
 return {'slug':slug,'access':True,'files':len(files)}

def main():
 out=HERE/'public_fallback_r1';out.mkdir(exist_ok=False)
 publication=[json.loads(x) for x in (HERE/'public_archives_r2/publication.jsonl').read_text().splitlines()]
 if not all(any(r['ref']=='davidmaisterx/'+s and r['public'] for r in publication) for s in SLUGS):raise ValueError('publication incomplete')
 active=preflight(out/'preflight.json');existing={x['job'] for x in json.loads((out/'preflight.json').read_text())['observed']}
 accesses=[];assignments=[]
 for slug in SLUGS:
  r=subprocess.run([sys.executable,__file__,'--probe',slug],env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG['davideferante'])},
   capture_output=True,text=True,timeout=45)
  if r.returncode:raise ValueError('public input inaccessible to third account')
  accesses.append(json.loads(r.stdout))
  owner=next((o for o in ['davideferante','davideferrante11','davidmaisterx'] if active.get(o,0)<5),None)
  if owner is None:
   assignments.append({'source':slug,'state':'ready_waiting_slot'});continue
  stage=out/slug
  r=subprocess.run([sys.executable,str(HERE/'prepare_archive_derivatives.py'),'--slug',slug,'--owner',owner,'--out',str(stage)],capture_output=True,text=True)
  if r.returncode:raise RuntimeError('stage preparation failed: '+r.stderr[-500:])
  meta=json.loads((stage/'kernel-metadata.json').read_text());frozen=json.loads((stage/'prepared.json').read_text())
  if meta['id'] in existing:raise ValueError('existing derivative; no duplicate launch')
  rc,answer=call(owner,['kernels','push','-p',str(stage)])
  ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
  record={'utc':datetime.now(timezone.utc).isoformat(),'source':slug,'slug':meta['id'],'accepted':ok,'answer':answer,
   'code_sha256':frozen['code_sha256'],'stage':str(stage),'replaces_unstarted_colab':slug!='rlab-hipsci-targeted19'}
  with (out/'launches.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
  print(json.dumps({'slug':meta['id'],'accepted':ok}),flush=True)
  if not ok:raise RuntimeError('push rejected; preserve ledger')
  active[owner]=active.get(owner,0)+1;assignments.append(record)
 (out/'access.json').write_text(json.dumps(accesses,indent=1));(out/'assignments.json').write_text(json.dumps(assignments,indent=1))

if __name__=='__main__':
 if sys.argv[1:2]==['--probe']:print(json.dumps(probe(sys.argv[2])))
 else:main()
