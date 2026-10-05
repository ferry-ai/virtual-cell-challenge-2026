"""Verify closed banks and samples with existing validators, downloading metadata only."""
import argparse,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,REPO,sha,command
from pipeline_state_r2 import isolated_receipts
from sample_state import validate

def main():
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False)
 frozen=json.loads((a.stage/'prepared.json').read_text());params=json.loads((a.stage/'params.json').read_text())
 status=command(a.job,['status'])
 if status['returncode'] or 'KernelWorkerStatus.COMPLETE' not in status['text']:raise ValueError('not complete; no fetch')
 owner=a.job.split('/')[0];receipts,files,version=isolated_receipts(owner,a.job,a.out/'bank_receipts')
 if version['saved_source_sha256']!=frozen['code_sha256'] or set(receipts)!={u['name'] for u in params['units']}:raise ValueError('saved producer identity differs')
 r=subprocess.run([sys.executable,str(HERE/'sample_state.py'),'--fetch',a.job,str(a.out)],
  env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])},capture_output=True,text=True,timeout=120)
 if r.returncode:raise RuntimeError('sample receipt retrieval failed: '+r.stderr[-500:])
 remote=json.loads(r.stdout);units={}
 if remote['saved_version']!=version:raise ValueError('saved version differs between bank/sample reads')
 for spec in params['units']:
  name=spec['name'];bank,path,digest=receipts[name]
  if not bank['complete'] or bank['cells_in']!=spec['cells'] or bank['cells_used']+bank['zero_depth_excluded']!=spec['cells'] or bank['source_verification']!=spec['receipt_sha256']:raise ValueError('population coverage or lineage differs')
  if not all('bank/'+name+'/'+n in files for n in bank['files']):raise ValueError('missing bank artefact')
  b={'state':'remote_complete_manifest_checked','kernel':a.job,'receipt':path,'receipt_sha256':digest,
   'saved_version':version,'files':bank['files'],'cells_used':bank['cells_used'],'contexts':bank['contexts'],'relative_path':'bank/'+name}
  s=validate({'parameters':{'unit':name,'bank_receipt_sha256':digest},'slug':a.job,
   'code_sha256':frozen['code_sha256']},remote,{'bank':b});s['relative_path']='samples/'+name
  units[name]={'bank':b,'samples':s,'trainer':{'state':'not_integrated','training_used':False}}
 result={'utc':datetime.now(timezone.utc).isoformat(),'kernel':a.job,'units':units,'training_ready':False}
 (a.out/'state.json').write_text(json.dumps(result,indent=1))
 print(json.dumps({n:{'contexts':v['bank']['contexts'],'sample_levels':v['samples']['levels']} for n,v in units.items()}))

if __name__=='__main__':main()
