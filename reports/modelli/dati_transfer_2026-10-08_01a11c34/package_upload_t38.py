"""Package an existing T3 generation if needed, then upload one scoped VCC object.

The VCC account token is never present in this private runtime. Only the official
single-object resumable capability is supplied. Scoring is launched locally.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
import shutil
import sys
import time
from urllib.parse import urlparse
import emission_support as support
import generate_contract as contract

WORK=Path('/kaggle/working');TEMP=Path('/kaggle/temp');INPUT=Path('/kaggle/input')


def mark(stage,**fields):
    print(json.dumps(dict(stage=stage,**fields)),flush=True)


def locate(name,spec):
    found=[p for p in INPUT.rglob(name) if p.is_file() and p.stat().st_size==spec['bytes']]
    if not found:
        from private_download_v2 import download_verified
        locators=json.loads((WORK/'source_locators.json').read_text())
        path=TEMP/'source_inputs'/name;path.parent.mkdir(parents=True,exist_ok=True)
        if spec.get('sha256_mode','full')!='full':raise ValueError('full input hash required for remote transfer')
        mark('fetch_source',file=name,bytes=spec['bytes'])
        download_verified(locators[name],path,spec['bytes'],spec['sha256'])
        # The downloader already hashes every byte and checks size before rename.
        # Stage 48 independently hashes the generated input again before packaging.
        return path
    elif len(found)==1:path=found[0]
    else:raise ValueError('unique pinned input unavailable: '+name)
    if spec.get('sha256_mode','full')=='full':digest=support._sha256(path)
    else:
        from vcc2026.manifest import file_fingerprint
        digest=file_fingerprint(path)['sha256']
    if digest!=spec['sha256']:raise ValueError('input hash differs: '+name)
    return path


def main():
    params=json.loads((WORK/'params.json').read_text())
    support._verify_embedded(params)
    resources=support._guard_resources()
    cap=json.loads((WORK/'delivery_capability.json').read_text())
    parsed=urlparse(cap['upload_url'])
    if parsed.scheme!='https' or not (parsed.hostname=='storage.googleapis.com' or (parsed.hostname or '').endswith('.storage.googleapis.com')):
        raise ValueError('not an official GCS upload capability')
    sys.path.insert(0,str(WORK/'repo/src'));sys.path.insert(0,str(WORK/'vendor'))
    for name,spec in params['source_receipts'].items():
        shutil.copyfile(locate(name,spec),WORK/name)
    diag=json.loads((WORK/'compact_diagnostics.json').read_text())
    shape=diag['shape']
    if (shape['n_cells'],shape['n_perturbations'],shape['cells_per_pert'],shape['contexts'])!=(360000,300,400,['A','B','C']):
        raise ValueError('incomplete generation')
    if diag['is_pilot'] or diag['context_provenance_ok'] is not True or diag['seed']!=20260912:
        raise ValueError('generation identity differs')
    pre=json.loads((WORK/'generation_preflight.json').read_text())
    for key in ('protocol','prediction','fit_receipt'):
        if pre[key]!=params[key]:raise ValueError('source scientific evidence differs')
    if any(x['sha256']!='b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6' for x in pre['effects'].values()):
        raise ValueError('T3 effect identity differs')
    product=WORK/params['product']
    if params['mode']=='package':
        source=locate('recovery_prediction.h5ad',params['input_product'])
        pack=TEMP/'t38_packaged';pack.mkdir(parents=True,exist_ok=False)
        mark('package_existing_cells',bytes=source.stat().st_size)
        raw=WORK/'data/raw/controls'
        support._run_script(WORK/'repo/scripts/48_package_prediction.py',[
            '--run-id',params['job_id'],'--prediction',str(source),'--out',str(pack),
            '--expect-sha256',params['input_product']['sha256'],
            '--vcc-name',params['product'],'--workdir',str(TEMP/'t38_payload'),
            '--genes',str(raw/'gene_names.csv'),'--perts',str(raw/'pert_counts.csv'),
            '--contexts','A,B,C','--reserve-gib',str(contract.STAGE48_RESERVE_GIB)])
        for name in ('packaging.json','manifest_48_package_prediction.json'):
            shutil.copyfile(pack/name,WORK/name)
        if (pack/params['product']).stat().st_size+1024**3>shutil.disk_usage(WORK).free:
            raise ValueError('insufficient final output disk')
        shutil.copyfile(pack/params['product'],product)
    else:
        shutil.copyfile(locate(params['product'],params['input_product']),product)
    package=json.loads((WORK/'packaging.json').read_text())
    validation=package['verification'];payload=validation['payload_vs_input']
    digest=support._sha256(product)
    if (package['exit_code']!=0 or validation['official_container_validator']!='passed'
            or not payload['matches_input'] or not payload['x_arrays_bit_identical']
            or validation['archive_sha256']!=digest or validation['archive_bytes']!=product.stat().st_size
            or (package['package']['n_obs'],package['package']['n_vars'])!=(360000,18533)):
        raise ValueError('package verification failed')
    generation=dict(status='VCC_READY',candidate='T3-CRISPRi-KO',product=params['product'],
        bytes=product.stat().st_size,sha256=digest,protocol=params['protocol'],prediction=params['prediction'],
        fit_receipt=params['fit_receipt'],source_job=params['source_job'],effects=pre['effects'],
        emission=contract.emission(),packaging_sha256=support._sha256(WORK/'packaging.json'),
        code=params['embedded_sha256'],new_fit=False,input_generation_job=params['input_generation_job'],
        scientific_promotion=False,claims_complete_D053=False)
    support._write(WORK/'generation_manifest.json',generation)
    mark('package_verified',sha256=digest,bytes=product.stat().st_size)
    from vcc.upload import upload_file
    last=0
    def progress(done,total):
        nonlocal last
        if time.monotonic()-last>10 or done==total:
            mark('uploading',bytes_done=done,total_bytes=total);last=time.monotonic()
    result=upload_file(cap['upload_url'],product,chunk_size=32*1024**2,progress=progress)
    if not result.verified:raise ValueError('GCS MD5 verification absent')
    receipt=dict(status='UPLOAD_VERIFIED',utc_upload_verified=datetime.now(timezone.utc).isoformat(),entry_id=cap['entry_id'],bytes_uploaded=result.bytes_sent,
        sha256=digest,md5_local=result.md5_local,md5_remote=result.md5_remote,md5_verified=result.verified,
        nnz=package['verification']['nnz_from_archive'],api_token_present=False,scoring_launched=False)
    support._write(WORK/'upload_receipt.json',receipt)
    mark('upload_verified',**receipt)


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        support._write(WORK/'delivery_failure.json',dict(error_type=type(exc).__name__))
        mark('delivery_failed',error_type=type(exc).__name__)
        raise SystemExit(1)
