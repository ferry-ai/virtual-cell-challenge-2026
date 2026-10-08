"""Private T3 fit, unchanged t36 generation, and verified VCC packaging."""
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
from extended_transfer_runtime import fit

WORK=Path('/kaggle/working')
TEMP=Path('/kaggle/temp')


def main():
    os.chdir(WORK);TEMP.mkdir(exist_ok=True,parents=True)
    params=json.loads((WORK/'extended_params.json').read_text())
    support._verify_embedded(params)
    support._check_axis(params)
    resources=support._guard_resources()
    if resources['working']['disk_free_bytes']<17*1024**3:
        raise ValueError('less than 17 GiB output disk')
    if support._sha256(WORK/'prediction_registered.json')!=params['prediction']['sha256']:
        raise ValueError('prediction registration changed')
    raw=WORK/'data/raw/controls'
    for name,size in params['controls']['bytes'].items():
        source=emission.resolve(name,dict(bytes=size,sha256=params['controls']['sha256'][name]))
        os.symlink(source,raw/name)
    with (raw/'pert_counts.csv').open() as f: panel=[r['target_gene'] for r in csv.DictReader(f)]
    with (raw/'gene_names.csv').open() as f: genes=[r[0] for r in list(csv.reader(f))[1:]]
    support._write(WORK/'extended_runtime_preflight.json',dict(utc=emission.stamp(),resources=resources,
        protocol=params['protocol'],prediction=params['prediction'],code=params['embedded_sha256'],
        controls=params['controls'],private=True,gpu=False))
    effects=fit(emission.mark)
    verified={c:dict(spec,**emission.validate_effect(spec['path'],panel,genes)) for c,spec in effects.items()}
    support._write(WORK/'generation_preflight.json',dict(utc=emission.stamp(),status='PASS',
        effects=verified,emission=contract.emission(),protocol=params['protocol'],prediction=params['prediction'],
        T1_null_reproduced=True,amplitude_or_cis_reapplied=False,emitter_effects_scale_applied_once=1.5))
    sys.path.insert(0,str(WORK/'vendor'))
    generated=TEMP/'t3_stage45'
    emission.mark('generate_cells',shape=[360000,18533])
    support._run_script(WORK/'repo/scripts/45_generate_prediction.py',[
        '--run-id',params['job_id'],'--trial',contract.TRIAL,'--out',str(generated),
        '--controls-dir',str(raw),'--cells-per-pert','400','--seed','20260912',
        '--gene-dispersion','--gene-dispersion-scale','1.0','--effects-scale','1.5',
        '--reserve-gib',str(contract.STAGE45_RESERVE_GIB),
        '--effects',*[c+'='+effects[c]['path'] for c in ('A','B','C')]])
    compact=support._compact(json.loads((generated/'generation_diagnostics.json').read_text()))
    shape=compact['shape']
    if (compact['is_pilot'] or shape['n_perturbations']!=300 or shape['cells_per_pert']!=400
        or shape['n_cells']!=360000 or shape['contexts']!=['A','B','C']
        or compact['context_provenance_ok'] is not True or compact['seed']!=20260912):
        raise ValueError('emission dimensions or provenance mismatch')
    support._write(WORK/'compact_diagnostics.json',compact)
    shutil.copy2(generated/'manifest.json',WORK/'generation_stage45_manifest.json')
    emission.mark('package_and_verify')
    support._run_script(WORK/'repo/scripts/48_package_prediction.py',[
        '--run-id',params['job_id'],'--prediction',str(generated/'prediction.h5ad'),
        '--out',str(WORK),'--vcc-name',params['product'],'--workdir',str(TEMP/'t3_pack'),
        '--genes',str(raw/'gene_names.csv'),'--perts',str(raw/'pert_counts.csv'),
        '--contexts','A,B,C','--reserve-gib',str(contract.STAGE48_RESERVE_GIB)])
    product=WORK/params['product']
    receipt=dict(utc=emission.stamp(),status='VCC_READY',product=params['product'],
        bytes=product.stat().st_size,sha256=support._sha256(product),candidate='T3-CRISPRi-KO',
        protocol=params['protocol'],prediction=params['prediction'],effects=verified,
        consumption_sha256=support._sha256(WORK/'t3_consumption.json'),
        packaging_sha256=support._sha256(WORK/'packaging.json'),
        emission=contract.emission(),code=params['embedded_sha256'],submitted=False,
        scientific_promotion=False,claims_complete_D053=False)
    support._write(WORK/'generation_manifest.json',receipt)
    emission.mark('complete',bytes=receipt['bytes'],sha256=receipt['sha256'])


if __name__=='__main__':
    worker=threading.Thread(target=emission.heartbeat,daemon=True);worker.start()
    try:main()
    except BaseException as exc:
        support._write(WORK/'failure.json',dict(utc=emission.stamp(),stage=emission.PHASE,error_type=type(exc).__name__))
        # Never print an exception message or traceback which may contain a bearer URL.
        print(json.dumps(dict(status='FAILED',stage=emission.PHASE,error_type=type(exc).__name__)),flush=True)
        raise SystemExit(1)
    finally:emission.STOP.set()
