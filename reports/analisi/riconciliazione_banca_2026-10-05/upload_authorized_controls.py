"""Upload only the three specifically authorized private competition controls.

Authorization: human answered 'Sì, autorizzo entrambi' to the named files/destinations.
The previous review rejection is preserved; this is not an implicit/public upload.
"""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[3]
S=R/'reports/modelli/percorso_riusabile_2026-10-05'
OUT=S/'generation_controls_r2'
def main():
    OUT.mkdir(exist_ok=False)
    stage=R/'data/cloud_inputs/vcc-official-controls-r1'
    old=json.loads((S/'generation_controls_r1/launch.json').read_text())
    assert set(p.name for p in stage.iterdir())==set(old['files'])|{'dataset-metadata.json'}
    for name,pin in old['files'].items():
        p=stage/name;assert p.stat().st_size==pin['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256']
    auth={'human_reply':'Sì, autorizzo entrambi','private_destinations':['davideferrante11/vcc-k562-t25-cache-r1','davideferrante11/vcc-official-controls-r1'],
      'controls_files':old['files'],'utc':datetime.now(timezone.utc).isoformat(),'previous_auto_review_rejection_preserved':True}
    (OUT/'authorization.json').write_text(json.dumps(auth,indent=2))
    env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle-davideferrante11')
    result=subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')),'datasets','create','-p',str(stage),'-q'],env=env,capture_output=True,text=True,timeout=600)
    receipt={**auth,'ref':old['ref'],'returncode':result.returncode,'text':(result.stdout+result.stderr).strip(),'accepted':result.returncode==0,'private':True}
    (OUT/'launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'accepted':receipt['accepted'],'ref':old['ref']}))
    if result.returncode:raise SystemExit('upload outcome not confirmed; inspect receipt before retry')
if __name__=='__main__':main()
