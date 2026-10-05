"""Push the independent mount/reader proof only after fresh slot/input checks."""
import json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from preflight_slots_fast_v1 import call


def main():
    stage=HERE/'access_runtime_r1';ledger=stage/'launch.json'
    if ledger.exists():raise ValueError('inspect prior launch, never duplicate')
    pre=json.loads((stage/'preflight.json').read_text())
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()
    if age>600 or pre['active'].get('davidmaisterx',0)>=5:raise ValueError('preflight stale or no slot')
    metadata=json.loads((stage/'kernel-metadata.json').read_text())
    if any(x['job']==metadata['id'] for x in pre['observed']):raise ValueError('job already exists')
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davidmaisterx'])
    for key in ('KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetDatasetMetadataRequest
    api=KaggleApi();api.authenticate()
    versions={}
    for ref in metadata['dataset_sources']:
        request=ApiGetDatasetMetadataRequest();request.owner_slug,request.dataset_slug=ref.split('/')
        with api.build_kaggle_client() as client:
            info=client.datasets.dataset_api_client.get_dataset_metadata(request).info
        if info.is_private:raise ValueError('public input not accessible to consumer')
        # Status endpoint returned 404 from consumer, metadata GET succeeds.
        # Verify saved version as owner, separately from actual consumer access.
        env={k:v for k,v in os.environ.items() if k not in
             ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
        env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[ref.split('/')[0]])
        code="import json,sys;from kaggle.api.kaggle_api_extended import KaggleApi;a=KaggleApi();a.authenticate();print(a.dataset_status(sys.argv[1],format='json(status,current_version_number)'))"
        result=subprocess.run([sys.executable,'-c',code,ref],env=env,capture_output=True,text=True,timeout=45)
        result.check_returncode();versions[ref]=json.loads(result.stdout)
    if sorted((v['status'],v['current_version_number']) for v in versions.values())!=[('ready',1),('ready',3)]:
        raise ValueError('input dataset version/access differs')
    prepared=json.loads((stage/'prepared.json').read_text())
    if sha(stage/'run.py')!=prepared['code_sha256']:raise ValueError('package changed')
    intent={'utc':datetime.now(timezone.utc).isoformat(),'job':metadata['id'],'inputs':versions,
            'code_sha256':prepared['code_sha256'],'accepted':False,'state':'push_requested',
            'preflight_sha256':sha(stage/'preflight.json'),'training_used':False}
    ledger.open('x').write(json.dumps(intent,indent=1))
    rc,answer=call('davidmaisterx',['kernels','push','-p',str(stage)])
    intent.update(returncode=rc,answer=answer,accepted=rc==0 and 'successfully pushed' in answer,
                  state='push_returned')
    ledger.write_text(json.dumps(intent,indent=1))
    print(json.dumps({'job':metadata['id'],'accepted':intent['accepted'],'returncode':rc}))
    if not intent['accepted']:raise RuntimeError('push failed; inspect receipt before retry')


if __name__=='__main__':main()
