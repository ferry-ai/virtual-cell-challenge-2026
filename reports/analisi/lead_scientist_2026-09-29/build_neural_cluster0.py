"""Prepare a private CPU-only diagnostic using existing kernel outputs; never push."""
import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
from build_neural_postgate import archive_bytes,members,digest,save,HERE,REPORT,R1_SHA


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    original=(HERE/'kaggle_neural_r1/review/runtime_payload.tar.gz').read_bytes()
    if digest(original)!=R1_SHA:
        raise ValueError('Original code differs')
    files=members(original)
    del files[f'{REPORT}/read_neural_sources.py']
    for name in ['verify_neural_runs.py','neural_cluster0_runner.py','neural_external_validation/cluster_pds.py',
                 'neural_external_validation/test_cluster_pds.py','neural_external_validation/PROTOCOLLO_DIAGNOSTICA.md']:
        files[f'{REPORT}/{name}']=(HERE/name).read_bytes()
    if digest(files[f'{REPORT}/neural_external_validation/cluster_pds.py'])!='4413ad2662b6315c9f08c396a766ba6d9d4fa066d22ad5661b06226eb416c1e9':
        raise ValueError('Frozen diagnostic changed')
    checked=json.loads((HERE/'kaggle_neural_r1/readout_verified_r1/provenance.json').read_text())
    verdict=json.loads((HERE/'kaggle_neural_r1/readout_verified_r1/verdict.json').read_text())
    if checked['verified'] is not True or verdict['training_seed']!=0:
        raise ValueError('Missing complete verified seed0 results')
    families=['k562','cd4','orion','ipsc','rpe1']
    evidence={}
    for family in families:
        folder=HERE/f'kaggle_neural_r1/results_small_r1/neural_sources_r1/folds/C_{family}_s0'
        evidence[family]={name:{'bytes':(folder/name).stat().st_size,'sha256':digest((folder/name).read_bytes())}
                          for name in ['manifest.json','per_target.csv','summary.json']}
    reference=json.loads((HERE/'kaggle_neural_r1/review/review_manifest.json').read_text())
    payload=archive_bytes(files)
    review={'prepared_utc':datetime.now(timezone.utc).isoformat(),'kernel':'davidmaisterx/vcc-lead-neural-cluster0-r1',
            'private':True,'dataset':reference['dataset'],'dataset_manifest_sha256':reference['dataset_manifest_sha256'],
            'kernel_source':'davidmaisterx/vcc-lead-neural-sources-r1/1','kernel_source_mount_confirmed':False,
            'payload_sha256':digest(payload),'code_allowlist':[{'path':name,'bytes':len(data),'sha256':digest(data)}
                                                               for name,data in sorted(files.items())],
            'fold_order':families,'fold_evidence':evidence,'gpu':False,'internet':False,'training':False,
            'new_data_upload':False,'seed0_original_verdict':verdict,'changes_primary_gate':False,
            'readout_sha256':digest((HERE/'kaggle_neural_r1/readout_verified_r1/verdict.json').read_bytes())}
    runner=files[f'{REPORT}/neural_cluster0_runner.py'].decode()
    cell=runner+'\n\nmain('+repr(base64.b64encode(payload).decode())+', '+repr(review)+')\n'
    compile(cell,'cluster_notebook','exec')
    for name,data in files.items():
        if name.endswith('.py'):
            compile(data,name,'exec')
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},
              'cells':[{'cell_type':'code','id':'diagnostic-only','metadata':{},'execution_count':None,
                        'outputs':[],'source':cell.splitlines(keepends=True)}]}
    metadata={'id':review['kernel'],'title':'VCC Lead Neural Cluster0 R1','code_file':'vcc-lead-neural-cluster0-r1.ipynb',
              'language':'python','kernel_type':'notebook','is_private':True,'enable_gpu':False,'enable_tpu':False,
              'enable_internet':False,'dataset_sources':[review['dataset']],'kernel_sources':[review['kernel_source']],
              'competition_sources':[],'model_sources':[]}
    args.out.mkdir(parents=True)
    save(args.out/metadata['code_file'],notebook);save(args.out/'kernel-metadata.json',metadata)
    save(args.out/'review_manifest.json',review)
    with (args.out/'runtime_payload.tar.gz').open('xb') as f:
        f.write(payload)
    save(args.out/'artifact_hashes.json',{p.name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
                                         for p in sorted(args.out.iterdir()) if p.is_file()})
    print(json.dumps({'out':str(args.out),'payload_sha256':digest(payload),'files':len(files),
                      'private':True,'gpu':False,'pushed':False}))


if __name__=='__main__':
    main()
