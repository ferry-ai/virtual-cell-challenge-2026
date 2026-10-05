"""Resolve provider identities and versions; metadata-only archival inventory."""
import argparse,json,os,re,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from launch_samples import call

EXTRA=['rlab-hipsci-gwfit','rlab-hipsci-gwnonfit','rlab-jurkat-gse249595','rlab-kolf-small','rlab-kolf-strong']

def worker(ref):
 from kaggle.api.kaggle_api_extended import KaggleApi
 a=KaggleApi();a.authenticate()
 return json.loads(a.dataset_status(ref,format='json(status,current_version_number)'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--previous-metadata',type=Path);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False)
 from archive_metadata import worker as metadata
 # Account isolation is essential: this process never imports Kaggle before worker mode.
 def extra(slug):
  if a.previous_metadata and (a.previous_metadata/slug/'files.json').is_file():
   return {'ref':'davidmaisterx/'+slug,'access':True,'reused_metadata':True}
  r=subprocess.run([sys.executable,str(HERE/'archive_metadata.py'),'--worker','davidmaisterx',slug,str(a.out/slug)],
   env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG['davidmaisterx'])},capture_output=True,text=True,timeout=90)
  if r.returncode:raise RuntimeError('metadata capture failed')
  return json.loads(r.stdout.strip().splitlines()[-1])
 extra_rows=list(ThreadPoolExecutor(5).map(extra,EXTRA))
 raws=[]
 for folder in [HERE/'archive_metadata_r1',a.previous_metadata or a.out]:
  for path in sorted(folder.iterdir()):
   if not path.is_dir() or not (path/'files.json').exists():continue
   raw=json.loads((path/'files.json').read_text());done=json.loads((path/'complete.json').read_text())
   ref='davidmaisterx/'+path.name
   r=subprocess.run([sys.executable,__file__,'--version',ref],env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG['davidmaisterx'])},
    capture_output=True,text=True,timeout=45)
   if r.returncode:raise RuntimeError('version check failed')
   version=json.loads(r.stdout)
   raws.append({'dataset':ref,'version':version['current_version_number'],'status':version['status'],
    'files_receipt':str((path/'files.json').resolve().relative_to(HERE.parents[2])).replace('\\','/'),
    'files_sha256':sha(path/'files.json'),'complete_sha256':sha(path/'complete.json'),
    'job_id':done['job_id'],'units':done['units'],'bytes':sum(x['bytes'] for x in raw),'cells':sum(x['cells'] for x in raw)})
 launches=[json.loads(x) for x in (HERE/'parallel_archives_r1/launches.jsonl').read_text().splitlines()]
 resolved=[]
 for launch in launches:
  actual=re.search(r'https://www.kaggle.com/code/([^\s]+)',launch['answer']).group(1)
  owner=actual.split('/')[0];rc,status=call(owner,['kernels','status',actual])
  resolved.append({**launch,'requested_slug':launch['slug'],'slug':actual,'status':status,'status_returncode':rc})
 (a.out/'state.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'archives':raws,
  'extra_access':extra_rows,'launches':resolved,'training_ready':False,'raw_bytes_sum':sum(x['bytes'] for x in raws),
  'raw_cells_sum':sum(x['cells'] for x in raws),'provider_slug_rewritten':True},indent=1))
 print(json.dumps({'archives':len(raws),'bytes':sum(x['bytes'] for x in raws),'cells':sum(x['cells'] for x in raws),
  'jobs':[{'slug':r['slug'],'status':r['status']} for r in resolved]}))

if __name__=='__main__':
 if sys.argv[1]=='--version':print(json.dumps(worker(sys.argv[2])))
 else:main()
