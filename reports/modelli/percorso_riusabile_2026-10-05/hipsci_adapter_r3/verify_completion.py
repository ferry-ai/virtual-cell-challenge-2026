"""Retrieve only new small consumer receipts and verify the saved execution code."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from preflight_slots_fast_v1 import call
from pipeline_state import CONFIG

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    out = HERE / sys.argv[1]
    out.mkdir(exist_ok=False)
    launch = json.loads((HERE / 'launch.json').read_text())
    owner, slug = launch['slug'].split('/')
    rc, status = call(owner, ['kernels', 'status', launch['slug']])
    (out / 'provider_status.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),returncode=rc,status=status),indent=1))
    if rc or 'COMPLETE' not in status:
        raise ValueError('consumer not complete; do not fetch final receipts')
    rc, answer = call(owner, ['kernels','output',launch['slug'],'-p',str(out),'--file-pattern','fit_receipt.json|resources.json'])
    (out / 'retrieval.json').write_text(json.dumps(dict(returncode=rc,answer=answer),indent=1))
    if rc:
        raise ValueError('small receipt retrieval failed')
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):
        os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiGetKernelRequest
    api=KaggleApi();api.authenticate()
    request=ApiGetKernelRequest();request.user_name=owner;request.kernel_slug=slug
    with api.build_kaggle_client() as client:
        saved=client.kernels.kernels_api_client.get_kernel(request)
    code=Path(launch['stage'])/'run.py'
    assert sha(code)==launch['code_sha256'], 'local launched code changed'
    assert saved.blob.source.replace('\r\n','\n')==code.read_text(encoding='utf-8').replace('\r\n','\n'), 'saved code differs'
    params=Path(launch['stage'])/'params.json'
    assert sha(params)==launch['params_sha256']
    p=json.loads(params.read_text())
    receipt_path=out/'fit_receipt.json'
    if not receipt_path.exists():
        raise ValueError('COMPLETE without scientific receipt; inspect saved log before retry')
    proof=json.loads(receipt_path.read_text())
    assert proof['state']=='derived_production_fragment' and not proof['full_training']
    assert proof['not_heldout_validation'] and proof['production_hidden_targets']==[]
    assert proof['params_sha256']==launch['params_sha256']
    assert proof['input_hashes']==p['bank_files'] and proof['recipe']==p['recipe']
    assert proof['source']==p['producer'] and proof['panel_sha256']==p['panel']['panel_sha256']
    assert proof['axis_sha256']==p['embedded_inputs']['gene_names.csv']['sha256']
    assert proof['matrix_hash_verified_in_consumer'] and not proof['mixer_consumed']
    assert set(proof['targets'])<=set(p['panel']['targets'])
    record=dict(utc=datetime.now(timezone.utc).isoformat(),job=launch['slug'],version=saved.metadata.current_version_number,
        saved_code_matches=True,launched_code_sha256=sha(code),saved_code_sha256=hashlib.sha256(saved.blob.source.encode()).hexdigest(),
        params_sha256=sha(params),receipt_sha256=sha(receipt_path),receipt_bytes=receipt_path.stat().st_size,
        targets=proof['targets'],n_cells=proof['n_cells'],contexts=len(proof['contexts']),lineage=proof['lineage'],
        output=proof['output'],verified=True,full_training=False,mixer_consumed=False,
        verification_scope='Saved code and real runtime receipt; NPZ remains cloud, downstream consumer must verify its hash')
    (out/'verification.json').write_text(json.dumps(record,indent=1)+'\n')
    print(json.dumps({k:record[k] for k in ('job','version','targets','n_cells','contexts','output','verified','mixer_consumed')}))

if __name__=='__main__':main()
