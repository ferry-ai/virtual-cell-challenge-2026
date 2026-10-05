import json,os,sys,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3]
S=R/'reports/modelli/percorso_riusabile_2026-10-05'
sys.path.insert(0,str(S))
from pipeline_state import CONFIG
from verify_public_cd4_v1 import CODE
env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davideferrante11'])
ref='davidmaisterx/vcc-prod-kolf-pan-genome-mask-r1'
p=subprocess.run([sys.executable,'-c',CODE,ref],env=env,capture_output=True,text=True,timeout=90)
assert p.returncode==0,'consumer metadata access failed'
r=json.loads(p.stdout)
assert r['version']==1 and r['is_private'] is False
proof=next(x for x in json.loads((S/'adapter_successors_r1/saved_code_verification.json').read_text()) if x['slug']==ref)
assert r['source_sha256']==proof['saved_source_sha256']
(S/'adapter_successors_r1/pan_consumer_access.json').open('x').write(json.dumps(r,indent=2))
print(json.dumps(r))
