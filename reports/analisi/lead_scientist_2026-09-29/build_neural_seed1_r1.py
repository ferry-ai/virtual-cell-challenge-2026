"""Prepare a private seed-1 replica before seed-0 results; never push or run training."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from build_neural_postgate import archive_bytes, members, R1_SHA, REPORT, HERE, REPO, save, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    original = (HERE/'kaggle_neural_r1/review/runtime_payload.tar.gz').read_bytes()
    if digest(original) != R1_SHA:
        raise ValueError('Seed-0 frozen source archive differs')
    files = members(original)
    files[f'{REPORT}/neural_reader/r1/read_neural_sources.py'] = files[f'{REPORT}/read_neural_sources.py']
    extras = ['read_neural_sources.py', 'read_neural_verified.py', 'verify_neural_runs.py',
              'EMENDAMENTO_LETTORE_NEURALE_01.md', 'EMENDAMENTO_NEURALE_SCHEDULING_01.md',
              'neural_external_validation/cluster_pds.py', 'neural_external_validation/test_cluster_pds.py',
              'neural_external_validation/PROTOCOLLO_DIAGNOSTICA.md', 'neural_seed1_runner_r1.py']
    for name in extras:
        files[f'{REPORT}/{name}'] = (HERE/name).read_bytes()
    if digest(files[f'{REPORT}/read_neural_sources.py']) != '21b936b387ec734e0aaeb4b85f982f127a465a84fb3a77dc89917190881a8243':
        raise ValueError('Mechanical reader correction changed')
    if digest(files[f'{REPORT}/neural_external_validation/cluster_pds.py']) != '4413ad2662b6315c9f08c396a766ba6d9d4fa066d22ad5661b06226eb416c1e9':
        raise ValueError('Reviewed cluster diagnostic changed')
    reference = json.loads((HERE/'kaggle_neural_r1/review/review_manifest.json').read_text())
    for entry in reference['code_allowlist']:
        if not entry['path'].endswith('/read_neural_sources.py') and digest(files[entry['path']]) != entry['sha256']:
            raise ValueError('Training source changed')
    if digest((args.data/'manifest.json').read_bytes()) != reference['dataset_manifest_sha256']:
        raise ValueError('Local data manifest differs from observed remote r2')
    input_files = {}
    for path in sorted(args.data.iterdir()):
        if path.is_file() and path.name != 'dataset-metadata.json':
            size = path.stat().st_size
            input_files[path.name] = {'bytes':size, 'sha256':digest(path.read_bytes()) if size<30_000_000 else None}
    if len(input_files) != 19:
        raise ValueError('Dataset file count differs from read-only remote listing')
    payload = archive_bytes(files)
    review = {'prepared_utc':datetime.now(timezone.utc).isoformat(),
              'kernel':'davidmaisterx/vcc-lead-neural-seed1-r1','private':True,
              'dataset':reference['dataset'], 'dataset_id':reference['dataset_id'],
              'dataset_manifest_sha256':reference['dataset_manifest_sha256'],
              'original_seed0_payload_sha256':R1_SHA, 'payload_sha256':digest(payload),'payload_bytes':len(payload),
              'code_allowlist':[{'path':name,'bytes':len(data),'sha256':digest(data)} for name,data in sorted(files.items())],
              'input_files':input_files, 'fold_order':reference['fold_order'], 'regime':'C','seed':1,
              'selection_seed':20260929,'same_original_training_code':True,
              'schedule_before_seed0_outcome':True,'requires_positive_seed0_for_scheduling':False,
              'read_all_folds_even_if_seed0_fails':True,'no_seed_cherry_picking':True,
              'production_still_requires_verified_positive_gate':True,
              'accelerator_requested':'NvidiaTeslaT4','cuda_visible_devices':'0',
              'quota_observed_hours_remaining':7.59,'concurrent_slot_availability':None,
              'new_data_uploaded':False,'network_or_package_install_in_runtime':False,'no_production_fit':True,
              'cross_family_requires_all_five':True,'cluster_changes_primary_verdict':False}
    runner = files[f'{REPORT}/neural_seed1_runner_r1.py'].decode()
    cell = runner+'\n\nmain('+repr(base64.b64encode(payload).decode())+', '+repr(review)+')\n'
    compile(cell, 'seed1_notebook', 'exec')
    notebook = {'nbformat':4,'nbformat_minor':5,
                'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},
                'cells':[{'cell_type':'code','id':'all-five-folds-seed1','metadata':{},'execution_count':None,
                          'outputs':[],'source':cell.splitlines(keepends=True)}]}
    metadata = {'id':review['kernel'],'title':'VCC Lead Neural Seed1 R1','code_file':'vcc-lead-neural-seed1-r1.ipynb',
                'language':'python','kernel_type':'notebook','is_private':True,'enable_gpu':True,'enable_tpu':False,
                'enable_internet':False,'machine_shape':'NvidiaTeslaT4','dataset_sources':[review['dataset']],
                'competition_sources':[],'kernel_sources':[],'model_sources':[]}
    args.out.mkdir(parents=True)
    save(args.out/metadata['code_file'],notebook)
    save(args.out/'kernel-metadata.json',metadata)
    save(args.out/'review_manifest.json',review)
    with (args.out/'runtime_payload.tar.gz').open('xb') as f:
        f.write(payload)
    save(args.out/'artifact_hashes.json',{p.name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
                                         for p in sorted(args.out.iterdir()) if p.is_file()})
    print(json.dumps({'review':str(args.out),'payload_sha256':digest(payload),'runtime_files':len(files),
                      'input_files':len(input_files),'small_input_hashes':sum(e['sha256'] is not None for e in input_files.values()),
                      'private':True,'pushed':False}))


if __name__ == '__main__':
    main()
