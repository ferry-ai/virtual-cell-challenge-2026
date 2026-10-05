"""Share original iPSC-derived input when private collaborator access is blocked.

Raw Tian/Norman already public by explicit owner authorization; this dataset
contains only unchanged bank statistics/locators derived from that raw source.
No model, hidden challenge data, new computation or data-version upload.
"""
import json,os
from pathlib import Path
from pipeline_state import HERE,CONFIG
from share_archive_inputs import worker


def main():
    refs=[json.loads(line) for line in (HERE/'public_archives_r2/publication.jsonl').read_text().splitlines()]
    if not any(r['ref']=='davidmaisterx/rlab-tian-norman' and r['public'] for r in refs):
        raise ValueError('explicitly authorized public raw source not verified')
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davideferante'])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate();ref='davideferante/vcc-tian-ipsc-sample-input-r1'
    version=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if version!={'status':'ready','current_version_number':3}:raise ValueError('unexpected saved version')
    proof=json.loads((HERE/'tian_population_rehouse_r1.json').read_text())
    if proof['dataset']!=ref:raise ValueError('wrong original bank copy')
    out=HERE/'public_ipsc_input_r1';out.mkdir(exist_ok=False)
    record=worker(ref,out/'metadata');record['version']=version
    record.update(reason='Phone verification required for private collaborators; original source explicitly public',
                  authorization='Owner: publish pipeline inputs/outputs when access blocks, plus explicit public Tian/Norman raw approval')
    (out/'publication.jsonl').open('x').write(json.dumps(record)+'\n')
    after=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if not record['public'] or after!=version:raise ValueError('unchanged public saved version not verified')
    print(json.dumps({'ref':ref,'public':True,'version':3,'files_changed':False}))


if __name__=='__main__':main()
