"""Verify public pipeline references from the consuming account, without outputs."""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG

REFS=['davidmaisterx/vcc-bank-cd4-4-4-'+s+'-r2' for s in ('rest','stim8hr','stim48hr')]+['davidmaisterx/vcc-effects-k562-essential-r4']
CODE='''import json,hashlib,sys
from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest
a=KaggleApi();a.authenticate();r=ApiGetKernelRequest();r.user_name,r.kernel_slug=sys.argv[1].split('/')
with a.build_kaggle_client() as c:s=c.kernels.kernels_api_client.get_kernel(r)
print(json.dumps({'job':sys.argv[1],'version':s.metadata.current_version_number,'source_sha256':hashlib.sha256(s.blob.source.encode()).hexdigest(),'is_private':getattr(s.metadata,'is_private',None),'accessible':True}))
'''
def main():
    dest=HERE/'public_cd4_fragments_r1'
    env={k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davideferrante11'])
    records=[]
    for ref in REFS:
        p=subprocess.run([sys.executable,'-c',CODE,ref],env=env,capture_output=True,text=True,timeout=90)
        if p.returncode:raise RuntimeError('Consumer metadata access failed: '+ref)
        records.append(json.loads(p.stdout))
    assert all(r['version']==1 for r in records),'publication changed version'
    payload={'utc':datetime.now(timezone.utc).isoformat(),'consumer':'davideferrante11','authorization':'human explicitly authorized public pipeline banks and required fragments','no_compute_repeated':True,'jobs':records}
    (dest/'consumer_verified.json').open('x').write(json.dumps(payload,indent=1))
    print(json.dumps(records))
if __name__=='__main__':main()
