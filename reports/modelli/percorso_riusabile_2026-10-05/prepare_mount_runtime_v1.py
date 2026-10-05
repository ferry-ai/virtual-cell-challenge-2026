"""Package one independent cross-account mount/reader prerequisite; no push."""
import base64,json,hashlib
from pipeline_state import HERE,REPO,sha


def main():
    stage=HERE/'access_runtime_r1';stage.mkdir(exist_ok=False)
    catalog=HERE/'cloud_catalog_r10/manifest.json';c=json.loads(catalog.read_text())
    n=c['units']['norman2019'];ip=c['units']['tian2019_ipsc']['bank']
    params={'storage_sha256':sha(catalog),'kind':'runtime_access_and_reader_verification',
        'norman':{'dataset':n['bank']['mountable_copy']['dataset'],
                  'layout_sha256':n['bank']['mountable_copy']['layout_sha256'],
                  'bank_receipt_sha256':n['bank']['receipt_sha256'],
                  'sample_receipt_sha256':n['samples']['receipt_sha256']},
        'ipsc':{'dataset':ip['mountable_copy']['dataset'],'receipt_sha256':ip['receipt_sha256'],
                'files':ip['files']}}
    sources={name:(HERE/name).read_bytes() for name in
             ('mount_runtime_v1.py','sample_reader.py','population_reader.py','restore_bank_aliases_v1.py')}
    sources['params.json']=json.dumps(params).encode()
    payload={k:{'data':base64.b64encode(v).decode(),'sha256':hashlib.sha256(v).hexdigest()} for k,v in sources.items()}
    code='import base64,hashlib,runpy,sys,os\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\nfor n,v in P.items():\n b=base64.b64decode(v["data"]);assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\nrunpy.run_path("mount_runtime_v1.py",run_name="__main__")\n'
    compile(code,'run.py','exec');(stage/'run.py').write_text(code)
    metadata={'id':'davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1',
        'title':'vcc-reuse-runtime-norman-ipsc-r1','code_file':'run.py','language':'python','kernel_type':'script',
        'is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
        'dataset_sources':[params['norman']['dataset'],params['ipsc']['dataset']],
        'kernel_sources':[],'competition_sources':[]}
    (stage/'kernel-metadata.json').write_text(json.dumps(metadata,indent=1))
    (stage/'prepared.json').write_text(json.dumps({'params':params,'code_sha256':sha(stage/'run.py'),
        'sources':{k:v['sha256'] for k,v in payload.items()},'fit_admitted':False},indent=1))
    print(json.dumps({'stage':stage.relative_to(REPO).as_posix(),'code_sha256':sha(stage/'run.py')}))


if __name__=='__main__':main()
