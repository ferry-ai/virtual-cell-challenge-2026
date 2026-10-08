"""Generate and package frozen T1 effects with the unchanged t36 emission.

No stage-100 refit, training, scoring, authentication or VCC submission occurs.
"""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time
import numpy as np
import emission_support as support
import generate_contract as contract

WORK = Path('/kaggle/working')
INPUT = Path('/kaggle/input')
TEMP = Path('/kaggle/temp')
PHASE = 'preflight'
STOP = threading.Event()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def mark(phase, **fields):
    global PHASE
    PHASE = phase
    event = dict(utc=stamp(), stage=phase, **fields)
    with (WORK/'progress.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(event)+'\n')
    print(json.dumps(event), flush=True)


def heartbeat():
    while not STOP.wait(20):
        support._write(WORK/'heartbeat.json', dict(utc=stamp(), stage=PHASE))


def resolve(filename, spec):
    matches = [p for p in INPUT.rglob(filename) if p.is_file()
               and p.stat().st_size == spec['bytes'] and support._sha256(p) == spec['sha256']]
    if len(matches) != 1:
        raise ValueError('expected exactly one matching frozen input: '+filename)
    return matches[0]


def validate_effect(path, panel, genes):
    with np.load(path, allow_pickle=False) as z:
        if z['targets'].astype(str).tolist() != panel or z['genes'].astype(str).tolist() != genes:
            raise ValueError('frozen effect axes differ')
        effect, mask = z['lfc'], z['observed']
        if effect.shape != (300,18533) or effect.dtype != np.float32 or mask.dtype != bool or mask.shape != effect.shape:
            raise ValueError('frozen effect shape or dtype differs')
        if not np.isfinite(effect).all() or np.any(effect[~mask] != 0):
            raise ValueError('frozen effect values or missingness differ')
        return dict(shape=list(effect.shape), observed=int(mask.sum()), all_values_finite=True)


def main():
    os.chdir(WORK)
    params = json.loads((WORK/'params.json').read_text())
    support._verify_embedded(params)
    support._check_axis(params)
    resources = support._guard_resources()
    # Stage 45/48 also enforce their own disk reserves before the heavy steps.
    if resources['working']['disk_free_bytes'] < 17*1024**3:
        raise ValueError('less than 17 GiB output disk')
    if support._sha256(WORK/'recipe_t1.json') != params['recipe']['sha256']:
        raise ValueError('T1 recipe identity differs')
    if support._sha256(WORK/'prediction_registered.json') != params['prediction']['sha256']:
        raise ValueError('pre-generation prediction registration differs')
    raw = WORK/'data/raw/controls'
    with (raw/'pert_counts.csv').open() as f:
        panel = [r['target_gene'] for r in csv.DictReader(f)]
    with (raw/'gene_names.csv').open() as f:
        rows = list(csv.reader(f)); genes = [r[0] for r in rows[1:]]
    if len(panel) != 300 or len(set(panel)) != 300 or len(genes) != 18533 or len(set(genes)) != 18533:
        raise ValueError('official axes are not unique/full')
    effects = TEMP/'t1_effects'; effects.mkdir(parents=True, exist_ok=False)
    verified = {}
    for context, spec in params['effects'].items():
        name = 'effects_'+context+'.npz'; source = resolve(name, spec)
        verified[context] = dict(spec, resolved_path=str(source), **validate_effect(source,panel,genes))
        os.symlink(source, effects/name)
    for name, size in params['controls']['bytes'].items():
        source = resolve(name, dict(bytes=size, sha256=params['controls']['sha256'][name]))
        os.symlink(source, raw/name)
    support._write(WORK/'generation_preflight.json', dict(utc=stamp(), status='PASS',
        resources=resources, effects=verified, controls=params['controls'], emission=contract.emission(),
        code=params['embedded_sha256'], candidate=params['candidate'], recipe=params['recipe'],
        prediction=params['prediction'], stage100_rerun=False, new_training=False,
        amplitude_or_cis_reapplied=False, emitter_effects_scale_applied_once=1.5))
    sys.path.insert(0,str(WORK/'vendor'))
    generated = TEMP/'t1_stage45'; run_id=params['job_id']
    mark('generate_cells', shape=[360000,18533])
    support._run_script(WORK/'repo/scripts/45_generate_prediction.py', [
        '--run-id',run_id,'--trial',contract.TRIAL,'--out',str(generated),
        '--controls-dir',str(raw),'--cells-per-pert','400','--seed','20260912',
        '--gene-dispersion','--gene-dispersion-scale','1.0','--effects-scale','1.5',
        '--reserve-gib',str(contract.STAGE45_RESERVE_GIB),
        '--effects','A='+str(effects/'effects_A.npz'),
        '--effects','B='+str(effects/'effects_B.npz'),
        '--effects','C='+str(effects/'effects_C.npz')])
    diagnostics=json.loads((generated/'generation_diagnostics.json').read_text())
    compact=support._compact(diagnostics); shape=compact['shape']
    if (compact['is_pilot'] or shape['n_perturbations']!=300 or shape['cells_per_pert']!=400
            or shape['n_cells']!=360000 or shape['contexts']!=['A','B','C']
            or compact['context_provenance_ok'] is not True or compact['seed']!=20260912):
        raise ValueError('generated dimensions, seed or context provenance differ')
    support._write(WORK/'compact_diagnostics.json',compact)
    shutil.copy2(generated/'manifest.json',WORK/'generation_stage45_manifest.json')
    mark('package_and_verify')
    support._run_script(WORK/'repo/scripts/48_package_prediction.py', [
        '--run-id',run_id,'--prediction',str(generated/'prediction.h5ad'),
        '--out',str(WORK),'--vcc-name',params['product'],'--workdir',str(TEMP/'t1_pack'),
        '--genes',str(raw/'gene_names.csv'),'--perts',str(raw/'pert_counts.csv'),
        '--contexts','A,B,C','--reserve-gib',str(contract.STAGE48_RESERVE_GIB)])
    product=WORK/params['product']
    manifest=dict(utc=stamp(), status='VCC_READY', product=params['product'],
        bytes=product.stat().st_size, sha256=support._sha256(product),
        candidate=params['candidate'], recipe=params['recipe'], prediction=params['prediction'],
        effects=verified, emission=contract.emission(), code=params['embedded_sha256'],
        preflight_sha256=support._sha256(WORK/'generation_preflight.json'),
        packaging_sha256=support._sha256(WORK/'packaging.json'),
        stage100_rerun=False, new_training=False, submitted=False, submitter='Lead only',
        scientific_promotion=False, claims_complete_D053=False)
    support._write(WORK/'generation_manifest.json',manifest)
    mark('complete',bytes=manifest['bytes'],sha256=manifest['sha256'])


if __name__=='__main__':
    worker=threading.Thread(target=heartbeat,daemon=True);worker.start()
    try:
        main()
    except BaseException as exc:
        support._write(WORK/'failure.json',dict(utc=stamp(),stage=PHASE,error_type=type(exc).__name__))
        raise
    finally:
        STOP.set()
