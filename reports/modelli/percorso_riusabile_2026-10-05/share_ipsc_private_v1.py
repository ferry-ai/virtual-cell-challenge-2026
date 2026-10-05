"""Grant existing authorized trainer accounts read access; no public exposure/version upload."""
import json,os
from pathlib import Path
from datetime import datetime,timezone
from pipeline_state import HERE,CONFIG


def main():
    owner='davideferante';os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetDatasetMetadataRequest
    api=KaggleApi();api.authenticate();ref=owner+'/vcc-tian-ipsc-sample-input-r1'
    out=HERE/'ipsc_private_access_r1';out.mkdir(exist_ok=False)
    version=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if version!={'status':'ready','current_version_number':3}:raise ValueError('input version not expected')
    path=Path(api.dataset_metadata(ref,str(out)));metadata=json.loads(path.read_text());info=metadata.get('info',metadata)
    req=ApiGetDatasetMetadataRequest();req.owner_slug,req.dataset_slug=ref.split('/')
    with api.build_kaggle_client() as c:before=c.datasets.dataset_api_client.get_dataset_metadata(req)
    if not before.info.is_private:raise ValueError('input already public; inspect before changing access')
    members={r['username']:r for r in info.get('collaborators',[])}
    for username in ('davidmaisterx','davideferrante11'):members[username]={'username':username,'role':'READER'}
    info['isPrivate']=True;info['collaborators']=list(members.values());path.write_text(json.dumps(metadata))
    api.dataset_metadata_update(ref,str(out));verified=out/'verified';verified.mkdir()
    after_path=Path(api.dataset_metadata(ref,str(verified)));after=json.loads(after_path.read_text())
    with api.build_kaggle_client() as c:current=c.datasets.dataset_api_client.get_dataset_metadata(req)
    seen={r['username'] for r in after.get('info',after).get('collaborators',[])}
    if not current.info.is_private or not {'davidmaisterx','davideferrante11'}.issubset(seen):
        raise ValueError('private read access not confirmed')
    after_version=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if after_version!=version:raise ValueError('dataset version changed')
    proof={'utc':datetime.now(timezone.utc).isoformat(),'dataset':ref,'version':3,'private':True,
           'reader_accounts':sorted(seen),'metadata_only':True,'files_changed':False,
           'consumer_runtime_hashes_verified':False}
    (out/'access.json').open('x').write(json.dumps(proof,indent=1));print(json.dumps(proof))


if __name__=='__main__':main()
