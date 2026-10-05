"""Fetch only small archive manifests; inspect access in isolated account processes."""
import argparse,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import CONFIG,sha

DATASETS=['rlab-scp-ko','rlab-scp-tcells','rlab-scp-k562-hek','rlab-tian-norman',
 'rlab-hepg2-nadig','rlab-jurkat-nadig','rlab-h1-vcc2025-trainval','rlab-rpe1-r2',
 'rlab-k562-essential-r2','rlab-k562-gwps-r3','rlab-a549','rlab-hipsci-targeted19']

def worker(account,slug,out):
 from kaggle.api.kaggle_api_extended import KaggleApi
 api=KaggleApi();api.authenticate();ref='davidmaisterx/'+slug
 try:
  files=api.dataset_list_files(ref,page_size=200).files
  result={'account':account,'ref':ref,'access':True,'files':[{'name':f.name,'bytes':f.total_bytes} for f in files]}
  if account=='davidmaisterx':
   out.mkdir(parents=True,exist_ok=False)
   api.dataset_metadata(ref,str(out))
   for name in ['files.json','complete.json']:
    api.dataset_download_file(ref,name,str(out),quiet=True)
    if (out/(name+'.zip')).exists():
     import zipfile
     with zipfile.ZipFile(out/(name+'.zip')) as z:z.extract(name,out)
    if not (out/name).is_file():raise ValueError('metadata download incomplete')
   result['receipt_files']={p.name:sha(p) for p in out.iterdir() if p.suffix=='.json'}
  return result
 except Exception as e:
  return {'account':account,'ref':ref,'access':False,'error_type':type(e).__name__,
   'http_status':getattr(getattr(e,'response',None),'status_code',None)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 def one(pair):
  account,slug=pair
  r=subprocess.run([sys.executable,__file__,'--worker',account,slug,str(a.out/slug)],
   env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[account])},capture_output=True,text=True,timeout=100)
  if r.returncode:raise RuntimeError('metadata worker failed: '+r.stderr[-500:])
  return json.loads(r.stdout.strip().splitlines()[-1])
 rows=list(ThreadPoolExecutor(6).map(one,[(owner,slug) for owner in CONFIG for slug in DATASETS]))
 (a.out/'access.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'records':rows},indent=1))
 print(json.dumps({owner:[r['ref'].split('/')[1] for r in rows if r['account']==owner and r['access']] for owner in CONFIG}))

if __name__=='__main__':
 if sys.argv[1]=='--worker':print(json.dumps(worker(sys.argv[2],sys.argv[3],Path(sys.argv[4]))))
 else:main()
