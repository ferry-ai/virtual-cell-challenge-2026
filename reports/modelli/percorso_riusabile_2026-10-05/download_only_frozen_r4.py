"""Recover the one verified candidate and perform the explicitly authorized VCC upload.

Independent Windows process: preserves raw CLI outputs and prevents sleep.
No automatic retries, publication or replacement of an existing entry.
"""
import ctypes,hashlib,json,os,subprocess,sys,time,shutil
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
JOB='davideferrante11/vcc-generate-t28-frozen-bank-r1'
RUN=HERE/'generation_successors_r1/download_execution_r4'
TRIAL=REPO/'reports/invii/trial_2026-10-06'
DATA=Path('C:/Users/ferra/vcc2026-data/submissions/t31_frozen_bank_2026-10-06')
MODEL='t31 - transfer t28 banca estesa'
DESCRIPTION='Transfer t25 con emissione t28 invariata, banca estesa parziale congelata il 5 ottobre. K562 storico, CD4, Orion HCT116/HEK293T, H1 e quattro esperimenti KOLF. Invio esplorativo; nessun miglioramento presunto.'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def state(name,**fields):
 (RUN/'state.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'state':name,**fields},indent=2),encoding='utf-8')
def main():
 RUN.mkdir(exist_ok=True)
 with (RUN/'started.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),'job':JOB},f)
 ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
 env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
 env.update(KAGGLE_CONFIG_DIR=str(Path.home()/'.kaggle-davideferrante11'),PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
 os.environ.update(env)
 from kaggle.api.kaggle_api_extended import KaggleApi
 a=KaggleApi();a.authenticate()
 prior=HERE/'generation_successors_r1/upload_execution_r2/producer_verified.json'
 verified=json.loads(prior.read_text(encoding='utf-8'))
 assert verified['job']==JOB and verified['version']==1 and verified['matches_launched_code']
 shutil.copy2(prior,RUN/'producer_verified.json')
 evidence=HERE/'generation_successors_r1/completion_r1'
 m=json.loads((evidence/'generation_manifest.json').read_text());status=json.loads((evidence/'status.json').read_text())
 assert status['usable_export'] and status['sha256']==m['sha256']
 package=json.loads((evidence/'packaging.json').read_text())['package']
 assert package['validation']['ok'] and not package['validation']['failures']
 assert package['n_obs']==360000 and package['n_vars']==18533 and package['archive_bytes']==m['bytes']
 TRIAL.mkdir(exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
 for name in ('generation_manifest.json','packaging.json','compact_diagnostics.json','manifest_48_package_prediction.json','recipe_extbank.json'):
  shutil.copy2(evidence/name,TRIAL/('t31_'+name))
 assert (TRIAL/'submission_texts.md').read_text(encoding='utf-8')==MODEL+'\n\n'+DESCRIPTION+'\n'
 assert not (TRIAL/'submit_t31_raw.json').exists(),'inspect existing entry before any upload'
 state('downloading',expected_sha256=m['sha256'],bytes=m['bytes'],destination=str(DATA/'prediction.vcc'))
 from download_ranges_v1 import download
 download(a,JOB,DATA/'prediction.vcc',m['bytes'],state)
 product=DATA/'prediction.vcc'
 assert product.is_file() and product.stat().st_size==m['bytes'],'download incomplete; no upload'
 digest=sha(product);assert digest==m['sha256'],'download checksum differs; no upload'
 (TRIAL/'t31_local_product.json').write_text(json.dumps({'path':str(product),'sha256':digest,'bytes':product.stat().st_size,'download_method':'HTTP ranges; bounded streaming','checksum_verified':True}),encoding='utf-8')
 state('download_verified_awaiting_submission_approval',sha256=digest,bytes=product.stat().st_size,product=str(product))
if __name__=='__main__':
 try:main()
 except BaseException as e:
  if RUN.exists():state('error',error=str(e),error_type=type(e).__name__)
  raise
 finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
