"""Consume verified existing shards, preserving every biological context and lineage."""
import gc,json,os,shutil,time
from pathlib import Path
import psutil
from bank import run_unit,sha
from materialize_samples import run as materialize

def main():
 p=json.loads(Path('params.json').read_text());started=time.time()
 colab=os.environ.get('VCC_ARCHIVE_DRIVE')
 env={'cpus':os.cpu_count(),'ram_available':psutil.virtual_memory().available,
  'disk_free':shutil.disk_usage('.').free,'provider':'colab' if colab else 'kaggle'}
 Path('environment.json').write_text(json.dumps(env));print(json.dumps(env),flush=True)
 if colab:
  project=Path(colab);root=project/'data/processed/corpus_cellulare_2026-09-30'/p['job_id']
  final=project/'data/processed/percorso_riusabile_2026-10-05'/('colab_'+p['slug']+'_r1')
  final.mkdir(parents=True,exist_ok=False)
 else:
  hits=[x for x in Path('/kaggle/input').rglob('files.json') if x.parent.name==p['slug']]
  if len(hits)!=1:raise ValueError('raw dataset mount not unique')
  root=hits[0].parent;final=Path.cwd()
 if sha(root/'complete.json')!=p['raw_complete_sha256']:raise ValueError('raw completion changed')
 # Drive has the original nested paths; Kaggle has the verified publication's flat layout.
 for spec in p['units']:
  if colab:
   spec={**spec,'files':[{**s,'file':s['unit']+'/'+s['file'].split('__',1)[1]} for s in spec['files']]}
  elif sha(root/'files.json')!=p['source_files_sha256']:raise ValueError('raw manifest changed')
  bank=final/'bank'/spec['name'];samples=final/'samples'/spec['name']
  run_unit(spec,root,bank);gc.collect()
  materialize({'unit':spec['name'],'bank_receipt_sha256':sha(bank/'complete.json'),
   'bank_input_path':str(bank),'spec':spec},root,samples)
  gc.collect()
  print(json.dumps({'unit':spec['name'],'bank_and_samples_complete':True}),flush=True)
 (final/'archive_derivatives_complete.json').write_text(json.dumps({'complete':True,'dataset':p['dataset'],
  'raw_files_sha256':p['source_files_sha256'],'raw_complete_sha256':p['raw_complete_sha256'],
  'axis_sha256':p['units'][0]['axis_sha256'],'units':{u['name']:{'bank_receipt_sha256':sha(final/'bank'/u['name']/'complete.json'),
   'sample_receipt_sha256':sha(final/'samples'/u['name']/'complete.json')} for u in p['units']},
  'training_used':False,'seconds':round(time.time()-started)},indent=1))

if __name__=='__main__':main()
