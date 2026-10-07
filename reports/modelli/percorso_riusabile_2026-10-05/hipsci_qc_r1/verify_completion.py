"""Retrieve the small QC receipts of the concluded diagnostic and verify the saved code."""
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
    (out / 'provider_status.json').write_text(json.dumps(dict(
        utc=datetime.now(timezone.utc).isoformat(), returncode=rc, status=status), indent=1))
    if rc or 'COMPLETE' not in status:
        raise ValueError('diagnostic not complete; do not fetch receipts')
    rc, answer = call(owner, ['kernels', 'output', launch['slug'], '-p', str(out), '--file-pattern',
                              'qc_receipt.json|resources.json|own_gene_records.jsonl'])
    (out / 'retrieval.json').write_text(json.dumps(dict(returncode=rc, answer=answer), indent=1))
    if rc:
        raise ValueError('receipt retrieval failed')
    for key in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN'):
        os.environ.pop(key, None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiGetKernelRequest
    api = KaggleApi()
    api.authenticate()
    request = ApiGetKernelRequest()
    request.user_name = owner
    request.kernel_slug = slug
    with api.build_kaggle_client() as client:
        saved = client.kernels.kernels_api_client.get_kernel(request)
    code = Path(launch['stage']) / 'run.py'
    params = Path(launch['stage']) / 'params.json'
    assert sha(code) == launch['code_sha256'], 'local launched code changed'
    assert sha(params) == launch['params_sha256'], 'local launched params changed'
    assert saved.blob.source.replace('\r\n', '\n') == code.read_text(encoding='utf-8').replace('\r\n', '\n'), 'saved code differs'
    p = json.loads(params.read_text())
    receipt_path = out / 'qc_receipt.json'
    records_path = out / 'own_gene_records.jsonl'
    if not receipt_path.exists() or not records_path.exists():
        raise ValueError('COMPLETE without diagnostic receipt; inspect saved log before retry')
    proof = json.loads(receipt_path.read_text())
    assert proof['state'] == 'diagnostic_complete_not_automatic_admission'
    assert proof['params_sha256'] == launch['params_sha256']
    assert proof['input_hashes'] == p['bank_files'] and proof['recipe'] == p['recipe']
    assert proof['source'] == p['producer'] and proof['panel_sha256'] == p['panel']['panel_sha256']
    assert proof['axis_sha256'] == p['embedded_inputs']['gene_names.csv']['sha256']
    assert proof['no_reingestion'] and proof['no_context_exclusion'] and proof['no_weights_changed']
    assert len(proof['contexts']) == 19
    assert proof['output']['bytes'] == records_path.stat().st_size and proof['output']['sha256'] == sha(records_path)
    record = dict(utc=datetime.now(timezone.utc).isoformat(), job=launch['slug'],
                  version=saved.metadata.current_version_number, saved_code_matches=True,
                  launched_code_sha256=sha(code), params_sha256=sha(params),
                  receipt_sha256=sha(receipt_path), receipt_bytes=receipt_path.stat().st_size,
                  records=proof['output'], clones=len(proof['contexts']), verified=True,
                  automatic_admission=False,
                  verification_scope='Saved code and real runtime receipt of the diagnostic; admission is a separate recorded decision')
    (out / 'verification.json').write_text(json.dumps(record, indent=1) + '\n')
    print(json.dumps({k: record[k] for k in ('job', 'version', 'clones', 'records', 'verified')}))


if __name__ == '__main__':
    main()
