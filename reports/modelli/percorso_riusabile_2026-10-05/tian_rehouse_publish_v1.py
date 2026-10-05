"""Publish already recovered sample-input bytes; no second download after SDK argument error."""
import json,os
from pathlib import Path
from pipeline_state import HERE,REPO,CONFIG,sha


def main():
    owner='davideferante';os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    state=json.loads((HERE/'tian_partial_r1/state.json').read_text()); source=state['units']['tian2019_ipsc']['bank']
    r=json.loads((REPO/source['receipt']).read_text())
    root=Path('C:/Users/ferra/vcc2026-data/processed/percorso_riusabile_2026-10-05/tian_sample_input_r1/bank/tian2019_ipsc')
    if sha(root/'complete.json')!=source['receipt_sha256']:raise ValueError('saved receipt changed')
    for name in ('rows.csv','mask.npz','samples.jsonl.gz'):
        f=root/name
        if sha(f)!=r['files'][name]['sha256'] or f.stat().st_size!=r['files'][name]['bytes']:raise ValueError('input changed')
    slug='vcc-tian-ipsc-sample-input-r1';ref=owner+'/'+slug
    # The prior create raised TypeError before entering the SDK; no upload was
    # attempted. Create-new never replaces an existing dataset or adds a version.
    if (HERE/'tian_rehouse_r1.json').exists():raise ValueError('resolve prior creation first')
    (root/'dataset-metadata.json').write_text(json.dumps({'id':ref,'title':slug,'licenses':[{'name':'other'}],'isPrivate':True}))
    result=api.dataset_create_new(str(root),public=False,quiet=True,dir_mode='skip',convert_to_csv=False)
    proof={'dataset':ref,'private':True,'source':source,'bank_receipt_sha256':source['receipt_sha256'],
         'copied_files':{n:r['files'][n] for n in ('rows.csv','mask.npz','samples.jsonl.gz')},
         'layout':'flat sample-only inputs; full population arrays remain at saved producer',
         'reason':'failed saved notebook rejected as kernel_source','ready':'pending API verification'}
    (HERE/'tian_rehouse_r1.json').open('x').write(json.dumps(proof,indent=1))
    print(json.dumps({'dataset':ref,'submitted':True,'bytes':sum(v['bytes'] for v in proof['copied_files'].values())}))


if __name__=='__main__':main()
