"""Generate exact T399 T3+ESM2 effects; never repeat the scientific fit."""
import csv
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import emission_support as support
import generate_contract as contract
import quick_generation_driver as emission

WORK=Path('/kaggle/working');TEMP=Path('/kaggle/temp')


def effect_arguments(effects):
    return [word for c in ('A','B','C') for word in ('--effects',c+'='+effects[c])]


def main():
    os.chdir(WORK);TEMP.mkdir(parents=True,exist_ok=True)
    os.environ['VCC2026_DATA_ROOT']=str(WORK/'data')
    os.environ['VCC2026_ARTIFACT_ROOT']=str(TEMP/'artifacts')
    sys.path.insert(0,str(WORK/'repo/src'))
    params=json.loads((WORK/'params.json').read_text())
    support._verify_embedded(params);support._check_axis(params)
    resources=support._guard_resources()
    support._write(WORK/'resource_preflight.json',resources)
    print(json.dumps(dict(stage='resources_checked',resources=resources)),flush=True)
    if resources['working']['disk_free_bytes']<17*1024**3:raise ValueError('insufficient disk')
    if support._sha256(WORK/'prediction_registered.json')!=params['prediction']['sha256']:
        raise ValueError('registered prediction changed')
    raw=WORK/'data/raw/controls'
    with (raw/'pert_counts.csv').open() as f:panel=[r['target_gene'] for r in csv.DictReader(f)]
    with (raw/'gene_names.csv').open() as f:genes=[r[0] for r in list(csv.reader(f))[1:]]
    for name,size in params['controls']['bytes'].items():
        source=emission.resolve(name,dict(bytes=size,sha256=params['controls']['sha256'][name]));os.symlink(source,raw/name)
    emission.mark('resolve_verified_T39_effects')
    expected=params['effects']['A']
    path=emission.resolve('T3_E2_fallback.npz',expected)
    if any(v['sha256']!=expected['sha256'] or v['bytes']!=expected['bytes'] for v in params['effects'].values()):
        raise ValueError('context effect identities differ')
    verified={c:dict(v,**emission.validate_effect(path,panel,genes)) for c,v in params['effects'].items()}
    effects={c:str(path) for c in ('A','B','C')}
    support._write(WORK/'generation_preflight.json',dict(utc=emission.stamp(),status='PASS',
        resources=resources,effects=verified,protocol=params['protocol'],prediction=params['prediction'],
        fit_receipt=params['fit_receipt'],source_job=params['source_job'],new_fit=False,
        effects_rehashed=True,amplitude_or_cis_reapplied=False,emitter_scale_applied_once=1.5))
    generated=TEMP/'t39_t3_stage45';sys.path.insert(0,str(WORK/'vendor'))
    emission.mark('generate_cells',shape=[360000,18533])
    support._run_script(WORK/'repo/scripts/45_generate_prediction.py',[
        '--run-id',params['job_id'],'--trial',contract.TRIAL,'--out',str(generated),
        '--controls-dir',str(raw),'--cells-per-pert','400','--seed','20260912',
        '--gene-dispersion','--gene-dispersion-scale','1.0','--effects-scale','1.5',
        '--reserve-gib',str(contract.STAGE45_RESERVE_GIB),*effect_arguments(effects)])
    compact=support._compact(json.loads((generated/'generation_diagnostics.json').read_text()));shape=compact['shape']
    if (compact['is_pilot'] or shape['n_perturbations']!=300 or shape['cells_per_pert']!=400
        or shape['n_cells']!=360000 or shape['contexts']!=['A','B','C']
        or compact['context_provenance_ok'] is not True or compact['seed']!=20260912):
        raise ValueError('full emission contract failed')
    support._write(WORK/'compact_diagnostics.json',compact)
    shutil.copy2(generated/'manifest_45_generate_prediction.json',WORK/'generation_stage45_manifest.json')
    emission.mark('package_and_verify')
    (TEMP/'t39_t3_packaged').mkdir(exist_ok=False)
    support._run_script(WORK/'repo/scripts/48_package_prediction.py',[
        '--run-id',params['job_id'],'--prediction',str(generated/'prediction.h5ad'),
        '--out',str(TEMP/'t39_t3_packaged'),'--vcc-name',params['product'],'--workdir',str(TEMP/'t39_t3_pack'),
        '--genes',str(raw/'gene_names.csv'),'--perts',str(raw/'pert_counts.csv'),
        '--contexts','A,B,C','--reserve-gib',str(contract.STAGE48_RESERVE_GIB)])
    for name in ('packaging.json','manifest_48_package_prediction.json'):
        shutil.copyfile(TEMP/'t39_t3_packaged'/name,WORK/name)
    product=WORK/params['product']
    source_product=TEMP/'t39_t3_packaged'/params['product']
    if source_product.stat().st_size+1024**3>shutil.disk_usage(WORK).free:raise ValueError('insufficient final output disk')
    shutil.copyfile(source_product,product)
    receipt=dict(utc=emission.stamp(),status='VCC_READY',candidate='T3-ESM2-fallback',product=params['product'],
        bytes=product.stat().st_size,sha256=support._sha256(product),
        protocol=params['protocol'],prediction=params['prediction'],fit_receipt=params['fit_receipt'],
        source_job=params['source_job'],effects=verified,emission=contract.emission(),
        packaging_sha256=support._sha256(WORK/'packaging.json'),code=params['embedded_sha256'],
        new_fit=False,submitted=False,scientific_promotion=False,claims_complete_D053=False)
    support._write(WORK/'generation_manifest.json',receipt)
    package=json.loads((WORK/'packaging.json').read_text())
    v=package['verification'];payload=v['payload_vs_input']
    if (package['exit_code']!=0 or v['official_container_validator']!='passed'
        or not payload['matches_input'] or not payload['x_arrays_bit_identical']
        or v['archive_sha256']!=receipt['sha256'] or v['archive_bytes']!=receipt['bytes']
        or (package['package']['n_obs'],package['package']['n_vars'])!=(360000,18533)):
        raise ValueError('package verification failed')
    cap=json.loads((WORK/'delivery_capability.json').read_text())
    from urllib.parse import urlparse
    host=urlparse(cap['upload_url'])
    if host.scheme!='https' or not (host.hostname=='storage.googleapis.com' or (host.hostname or '').endswith('.storage.googleapis.com')):
        raise ValueError('unexpected upload capability host')
    from vcc.upload import upload_file
    import time
    last=0
    def progress(done,total):
        nonlocal last
        if time.monotonic()-last>20 or done==total:
            emission.mark('uploading',bytes_done=done,total_bytes=total);last=time.monotonic()
    result=upload_file(cap['upload_url'],product,chunk_size=32*1024**2,progress=progress)
    if not result.verified:raise ValueError('upload MD5 unverified')
    upload=dict(status='UPLOAD_VERIFIED',utc_upload_verified=emission.stamp(),entry_id=cap['entry_id'],
        bytes_uploaded=result.bytes_sent,sha256=receipt['sha256'],md5_local=result.md5_local,
        md5_remote=result.md5_remote,md5_verified=result.verified,nnz=v['nnz_from_archive'],
        api_token_present=False,scoring_launched=False)
    support._write(WORK/'upload_receipt.json',upload)
    emission.mark('upload_verified',**upload)
    emission.mark('complete',bytes=receipt['bytes'],sha256=receipt['sha256'])


if __name__=='__main__':
    worker=threading.Thread(target=emission.heartbeat,daemon=True);worker.start()
    try:main()
    except BaseException as exc:
        # Retain expensive completed intermediates if a later wrapper/packaging step fails.
        checkpoint=TEMP/'t39_t3_stage45'
        for name in ('prediction.h5ad','generation_diagnostics.json','manifest_45_generate_prediction.json'):
            if (checkpoint/name).is_file():
                shutil.copyfile(checkpoint/name,WORK/('recovery_'+name))
        support._write(WORK/'failure.json',dict(utc=emission.stamp(),stage=emission.PHASE,error_type=type(exc).__name__))
        # ValueError messages here are fixed local invariant names, never remote URLs.
        reason=str(exc) if isinstance(exc,ValueError) and 'http' not in str(exc) else None
        print(json.dumps(dict(status='FAILED',stage=emission.PHASE,error_type=type(exc).__name__,reason=reason)),flush=True)
        raise SystemExit(1)
    finally:emission.STOP.set()
