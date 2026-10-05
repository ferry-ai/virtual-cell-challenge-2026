"""Upload the pinned historical K562 source and dispatch one effects-only refit.

No competition-control files are uploaded. An intent prevents a blind second launch.
"""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
OUT=REPO/'reports/modelli/percorso_riusabile_2026-10-05/k562_reuse_r1'
def write(p,x):p.open('x',encoding='utf-8').write(json.dumps(x,indent=2))
def call(args):
    env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle-davideferrante11')
    r=subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')),*args],env=env,capture_output=True,text=True,timeout=300)
    return {'returncode':r.returncode,'text':(r.stdout+r.stderr).strip()}
def main():
    pre=json.loads((AUDIT/'preflight_k562_reuse_r1.json').read_text())
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()<1800
    assert pre['active'].get('davideferrante11',0)<5
    ready=json.loads((OUT/'ready_r3.json').read_text());pkg=Path(ready['package'])
    assert hashlib.sha256((pkg/'run.py').read_bytes()).hexdigest()==ready['code_sha256']
    stage=REPO/'data/cloud_inputs/vcc-k562-t25-cache-r1'
    assert set(p.name for p in stage.iterdir())=={'k562.npz.bin','lineage.json','dataset-metadata.json','gene_coordinates_gencode_v50.tsv'}
    write(OUT/'dispatch_intent_r1.json',{'utc':datetime.now(timezone.utc).isoformat(),'ref':ready['metadata']['id'],'private_dataset':True,'no_official_control_h5ad':True})
    result=call(['datasets','create','-p',str(stage),'-q']);write(OUT/'dataset_create_r1.json',result)
    if result['returncode']:raise SystemExit('dataset upload not confirmed; inspect receipt, never retry blindly')
    result=call(['kernels','push','-p',str(pkg)]);write(OUT/'launch_r1.json',{**result,'utc':datetime.now(timezone.utc).isoformat(),'slug':ready['metadata']['id'],'accepted':result['returncode']==0,'code_sha256':ready['code_sha256'],'params_sha256':ready['params_sha256'],'kind':'effects_only_historical_k562_reuse'})
    if result['returncode']:raise SystemExit('push not confirmed; inspect receipt')
    print(json.dumps({'dataset_uploaded':True,'refit_accepted':True,'slug':ready['metadata']['id']}))
if __name__=='__main__':main()
