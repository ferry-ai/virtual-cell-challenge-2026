"""Make the saved iPSC population mountable; transfer only missing verified arrays.

Kaggle rejects an ERROR producer as kernel_source. Preserve original bank bytes,
reuse cached locators, and retain all previous dataset versions. No bank recompute.
"""
import json, os, shutil
from datetime import datetime, timezone
from pathlib import Path
from pipeline_state import HERE, REPO, CONFIG, sha


def main():
    owner='davideferante'; os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi(); api.authenticate()
    ref=owner+'/vcc-tian-ipsc-sample-input-r1'
    proof=HERE/'tian_population_rehouse_r1.json'
    if proof.exists(): raise ValueError('inspect prior submission; never duplicate a version')
    before=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if before['current_version_number']!=2: raise ValueError('unexpected dataset version')
    state=json.loads((HERE/'tian_partial_r1/state.json').read_text())
    source=state['units']['tian2019_ipsc']['bank']
    receipt=json.loads((REPO/source['receipt']).read_text())
    root=Path('C:/Users/ferra/vcc2026-data/processed/percorso_riusabile_2026-10-05/tian_sample_input_r1/bank/tian2019_ipsc')
    if sha(root/'complete.json')!=source['receipt_sha256']: raise ValueError('receipt changed')
    transferred=[]
    for name, expected in receipt['files'].items():
        path=root/name
        if not path.exists():
            api.kernels_output(source['kernel'],str(root.parent.parent),
                               file_pattern='^bank/tian2019_ipsc/'+name.replace('.','\\.')+'$')
            transferred.append(name)
        if path.stat().st_size!=expected['bytes'] or sha(path)!=expected['sha256']:
            raise ValueError('original bank bytes differ: '+name)
    alias=root/'samples.jsonl.gz.bin'
    if not alias.exists(): shutil.copyfile(root/'samples.jsonl.gz',alias)
    if sha(alias)!=receipt['files']['samples.jsonl.gz']['sha256']: raise ValueError('gzip alias changed')
    intent={'utc':datetime.now(timezone.utc).isoformat(),'dataset':ref,'previous_version':2,
        'expected_version':3,'source':source,'files':receipt['files'],
        'transferred':transferred,'transferred_bytes':sum(receipt['files'][n]['bytes'] for n in transferred),
        'bank_receipt_sha256':source['receipt_sha256'],'old_versions_retained':True,
        'reason':'provider refuses saved ERROR notebook as kernel input; exact byte relocation',
        'state':'upload_requested','private':True,'consumer_runtime_hashes_verified':False}
    proof.open('x').write(json.dumps(intent,indent=1))
    api.dataset_create_version(str(root),'Full original iPSC bank statistics, hash verified; reuse v2 locators, no recomputation',
                               quiet=True,convert_to_csv=False,delete_old_versions=False,dir_mode='skip')
    print(json.dumps({'dataset':ref,'expected_version':3,'transferred_bytes':intent['transferred_bytes']}))


if __name__=='__main__': main()
