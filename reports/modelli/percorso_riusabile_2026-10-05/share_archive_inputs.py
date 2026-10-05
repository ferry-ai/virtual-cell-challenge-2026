"""Apply the owner's public-sharing request to named raw archives; do not upload bytes."""
import argparse,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha

def worker(ref,out):
 from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetDatasetMetadataRequest
 a=KaggleApi();a.authenticate();out.mkdir(parents=True,exist_ok=False)
 metadata=Path(a.dataset_metadata(ref,str(out)))
 before=json.loads(metadata.read_text());after=json.loads(metadata.read_text())
 info=after.get('info',after);info['isPrivate']=False
 metadata.write_text(json.dumps(after))
 q=ApiGetDatasetMetadataRequest();q.owner_slug,q.dataset_slug=ref.split('/')
 with a.build_kaggle_client() as client:current=client.datasets.dataset_api_client.get_dataset_metadata(q)
 already_public=not current.info.is_private
 if not already_public:a.dataset_metadata_update(ref,str(out))
 verified=out/'verified';verified.mkdir()
 v=Path(a.dataset_metadata(ref,str(verified)));result=json.loads(v.read_text())
 with a.build_kaggle_client() as client:current=client.datasets.dataset_api_client.get_dataset_metadata(q)
 public=not current.info.is_private
 return {'ref':ref,'public':public,'already_public':already_public,'metadata_before':before,'metadata_after':result,
  'data_uploaded':False,'files_replaced':False,'utc':datetime.now(timezone.utc).isoformat()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--datasets',nargs='+',required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 for ref in a.datasets:
  if ref not in {r['dataset'] for r in json.loads((HERE/'archive_followup_r2/state.json').read_text())['archives']}:raise ValueError('not in pinned raw inventory')
  env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[ref.split('/')[0]])}
  r=subprocess.run([sys.executable,__file__,'--worker',ref,str(a.out/ref.split('/')[1])],env=env,capture_output=True,text=True,timeout=120)
  if r.returncode:raise RuntimeError('public sharing failed: '+r.stderr[-800:])
  record=json.loads(r.stdout.strip().splitlines()[-1])
  with (a.out/'publication.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
  print(json.dumps({'ref':ref,'public':record['public'],'data_uploaded':False}),flush=True)
  if not record['public']:raise ValueError('publication not confirmed')

if __name__=='__main__':
 if sys.argv[1]=='--worker':print(json.dumps(worker(sys.argv[2],Path(sys.argv[3]))))
 else:main()
