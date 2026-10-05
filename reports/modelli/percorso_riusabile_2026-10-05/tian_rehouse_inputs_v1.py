"""Rehouse only the 3 sample-consumed files: failed notebook cannot be a kernel input.

Full population arrays remain in the saved producer; do not claim this is a full
bank copy. This bounded transfer is an access repair, not ingestion or recompute.
"""
import json,os,sys
from pathlib import Path
from pipeline_state import HERE,REPO,sha,CONFIG


def main():
    owner='davideferante';os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    a=KaggleApi();a.authenticate()
    state=json.loads((HERE/'tian_partial_r1/state.json').read_text())
    source=state['units']['tian2019_ipsc']['bank']; receipt=json.loads((REPO/source['receipt']).read_text())
    root=Path('C:/Users/ferra/vcc2026-data/processed/percorso_riusabile_2026-10-05/tian_sample_input_r1')
    if root.exists():raise ValueError('inspect existing transfer before retry')
    root.mkdir(parents=True)
    a.kernels_output(state['kernel'],str(root),file_pattern=r'^bank/tian2019_ipsc/(complete\.json|rows\.csv|mask\.npz|samples\.jsonl\.gz)$')
    bank=root/'bank/tian2019_ipsc'
    if sha(bank/'complete.json')!=source['receipt_sha256']:raise ValueError('completion changed')
    records={}
    for name in ('rows.csv','mask.npz','samples.jsonl.gz'):
        f=bank/name; expected=receipt['files'][name]
        if f.stat().st_size!=expected['bytes'] or sha(f)!=expected['sha256']:raise ValueError('copied input differs')
        records[name]=expected
    slug='vcc-tian-ipsc-sample-input-r1'
    (root/'dataset-metadata.json').write_text(json.dumps({'id':owner+'/'+slug,'title':slug,
              'licenses':[{'name':'other'}],'isPrivate':True}))
    # Only a private derivative input dataset; the raw release is unchanged.
    result=a.dataset_create_new(str(root),public=False,quiet=True,dir_mode='zip',keep_tabular=True)
    proof={'dataset':owner+'/'+slug,'private':True,'source':source,'copied_files':records,
           'bank_receipt_sha256':source['receipt_sha256'],'reason':'failed saved notebook rejected as kernel_source',
           'role':'sample-only input, population arrays remain at saved producer','ready':'pending API verification'}
    (HERE/'tian_rehouse_r1.json').open('x').write(json.dumps(proof,indent=1))
    print(json.dumps({'dataset':proof['dataset'],'bytes':sum(r['bytes'] for r in records.values()),'submitted':True}))


if __name__=='__main__':main()
