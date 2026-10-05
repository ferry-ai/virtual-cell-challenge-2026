"""Launch one private CPU integration consumer of existing immutable outputs."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from launch_samples_r2 import preflight
from launch_samples import call

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True)
    p.add_argument('--unit',required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    item=json.loads(args.state.read_text())['units'][args.unit]
    if item['state']!='remote_complete_manifest_checked':
        raise ValueError('sample output not verified')
    launches=list(map(json.loads,(HERE/'sample_launches.jsonl').read_text().splitlines()))
    source=next(r for r in launches if r['slug']==item['kernel'] and r['accepted'])
    owner=item['kernel'].split('/')[0];slug=owner+'/vcc-reader-'+args.unit.lower().replace('_','-')+'-r1'
    active=preflight(out/'preflight.json')
    observed=json.loads((out/'preflight.json').read_text())['observed']
    if any(r['job']==slug for r in observed) or active[owner]>=5:
        raise ValueError('existing consumer or no available committed CPU slot')
    params={'unit':args.unit,'bank_sha256':item['bank_receipt_sha256'],'sample_sha256':item['receipt_sha256']}
    payload={}
    for name in ('sample_reader.py','population_reader.py','consumer_probe.py'):
        b=(HERE/name).read_bytes();payload[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
    b=json.dumps(params).encode();payload['params.json']={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
    code='import os,sys,base64,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
    code+='for n,v in P.items():\n b=base64.b64decode(v["data"]);assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
    code+='runpy.run_path("consumer_probe.py",run_name="__main__")\n'
    compile(code,'run.py','exec')
    stage=out/'stage';stage.mkdir();(stage/'run.py').write_text(code,encoding='utf-8')
    meta={'id':slug,'title':slug.split('/')[1],'code_file':'run.py','language':'python','kernel_type':'script',
          'is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
          'dataset_sources':[],'kernel_sources':[item['kernel'],source['metadata']['kernel_sources'][0]],'competition_sources':[]}
    (stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
    rc,answer=call(owner,['kernels','push','-p',str(stage)])
    ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
    (out/'launch.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'slug':slug,
        'accepted':ok,'answer':answer,'params':params,'metadata':meta,'code_sha256':hashlib.sha256(code.encode()).hexdigest()},indent=1))
    print(json.dumps({'slug':slug,'accepted':ok,'answer':answer}))
    if not ok:
        raise RuntimeError('consumer launch not accepted')


if __name__=='__main__':
    main()
