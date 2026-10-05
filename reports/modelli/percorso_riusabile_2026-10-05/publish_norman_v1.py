"""Publish the explicitly authorized Norman bank/cells by metadata only."""
import json,os
from pathlib import Path
from pipeline_state import HERE,CONFIG
from share_archive_inputs import worker


def main():
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davideferante'])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate();ref='davideferante/vcc-norman-bank-samples-r1'
    version=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if version!={'status':'ready','current_version_number':1}:raise ValueError('wait for saved original copy')
    out=HERE/'public_norman_r1';out.mkdir(exist_ok=False)
    record=worker(ref,out/'metadata');record['version']=version
    record['authorization']='Owner explicitly authorized Norman samples/publication in chat after review rejection'
    (out/'publication.jsonl').open('x').write(json.dumps(record)+'\n')
    after=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if not record['public'] or after!=version:raise ValueError('public unchanged-version not verified')
    print(json.dumps({'ref':ref,'public':True,'version':1,'files_changed':False}))


if __name__=='__main__':main()
