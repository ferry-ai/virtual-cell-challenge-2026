"""Separate Colab assignments and Kaggle stages; no implicit sharing or ingestion."""
import hashlib,json,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
from prepare_archive_derivatives import build
from pipeline_state import HERE,sha

COLAB=['rlab-scp-ko','rlab-scp-tcells','rlab-scp-k562-hek','rlab-tian-norman']
KAGGLE=[('davideferrante11',s) for s in ['rlab-hepg2-nadig','rlab-jurkat-nadig',
 'rlab-h1-vcc2025-trainval','rlab-rpe1-r2','rlab-k562-gwps-r3']]+[
 ('davidmaisterx','rlab-k562-essential-r2'),('davidmaisterx','rlab-a549')]

def cell(code):return {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[], 'source':code.splitlines(True)}

def main():
 out=HERE/'parallel_archives_r1';out.mkdir(exist_ok=False);assignments=[]
 for slot,slug in enumerate(COLAB,1):
  files,p,_,_=build(slug,slot=slot)
  zip_path=out/(f'colab_{slot}_'+slug+'.zip')
  with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
   for name,raw in files.items():z.writestr(name,raw)
  digest=sha(zip_path)
  setup=f'''# Mount the Drive holding vcc2026; shared accounts need its shortcut in MyDrive.
from google.colab import drive
drive.mount('/content/drive')
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
PROJECT=Path('/content/drive/MyDrive/vcc2026')
PACKAGE=PROJECT/'runs/parallel_archives_2026-10-05_r1/{zip_path.name}'
assert PACKAGE.is_file(), 'Share vcc2026 with this account and add its shortcut to MyDrive'
assert hashlib.sha256(PACKAGE.read_bytes()).hexdigest() == '{digest}', 'Package differs'
WORK=Path('/content/vcc_archive_{slot}')
WORK.mkdir(exist_ok=False)
with zipfile.ZipFile(PACKAGE) as z:z.extractall(WORK)
subprocess.run([sys.executable,'-m','pip','install','-q','h5py','pandas','scipy','psutil'],check=True)
print('Slot {slot}: {slug}; archive existing, new derivatives only')
'''
  run='''os.environ['VCC_ARCHIVE_DRIVE']=str(PROJECT)
os.environ['PYTHONUNBUFFERED']='1'
LOGDIR=PROJECT/'runs/parallel_archives_2026-10-05_r1/logs'
LOGDIR.mkdir(exist_ok=True)
log=LOGDIR/('slot_'+str('''+str(slot)+''')+'.log')
with log.open('x') as f:
 proc=subprocess.Popen([sys.executable,'archive_runtime.py'],cwd=WORK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
 for line in proc.stdout:
  print(line,end='',flush=True);f.write(line);f.flush()
 rc=proc.wait()
assert rc==0, 'Job failed: preserve outputs and report last error; do not restart ingestion'
print('BANK AND SAMPLES SAVED TO DRIVE')
'''
  for code in (setup,run):compile(code,'colab_cell','exec')
  nb={'nbformat':4,'nbformat_minor':5,'metadata':{'colab':{'name':f'VCC archive slot {slot}'},
   'kernelspec':{'display_name':'Python 3','name':'python3'}},'cells':[
   {'cell_type':'markdown','metadata':{},'source':[f'# VCC – slot {slot}: {slug}\n','CPU. Eseguire le due celle. Una sessione per notebook. Non avviare due volte.\n']},cell(setup),cell(run)]}
  notebook=out/f'colab_slot_{slot}.ipynb';notebook.write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')
  assignments.append({'provider':'colab','slot':slot,'slug':slug,'package':zip_path.name,
   'package_sha256':digest,'notebook':notebook.name,'state':'prepared_owner_start_required',
   'cells':sum(u['cells'] for u in p['units'])})
 access=json.loads((HERE/'archive_metadata_r1/access.json').read_text())['records']
 for owner,slug in KAGGLE:
  if not any(r['account']==owner and r['ref']=='davidmaisterx/'+slug and r['access'] for r in access):raise ValueError('input inaccessible')
  stage=out/('kaggle_'+slug)
  r=subprocess.run([sys.executable,str(HERE/'prepare_archive_derivatives.py'),'--slug',slug,'--owner',owner,'--out',str(stage)],capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stderr)
  assignments.append({'provider':'kaggle','owner':owner,'slug':slug,'stage':str(stage),'state':'prepared'})
 (out/'assignments.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'assignments':assignments,
  'no_duplicate_sources':len({r['slug'] for r in assignments})==len(assignments),
  'remaining':['rlab-hipsci-targeted19; stage when next accessible Kaggle slot is free',
   'davideferante has no access to the existing pilot archives; do not republish implicitly']},indent=1))
 print(json.dumps(assignments))

if __name__=='__main__':main()
