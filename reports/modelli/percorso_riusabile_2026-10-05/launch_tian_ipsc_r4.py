"""Resume iPSC sampling with byte-preserving locator alias, no new bank fit."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from launch_samples_r2 import preflight
from launch_samples import call
from archive_partition_v1 import pack


def main():
    out=HERE/'tian_ipsc_r4';out.mkdir(exist_ok=False)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davideferante'])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate();ref='davideferante/vcc-tian-ipsc-sample-input-r1'
    version=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if version['current_version_number']!=2 or version['status'].lower()!='ready':raise ValueError('sample input v2 not ready')
    rc,status=call('davideferante',['kernels','status','davideferante/vcc-derivatives-tian2019-ipsc-resume-r3'])
    if rc or 'ERROR' not in status:raise ValueError('old resume not concluded')
    active=preflight(out/'preflight.json')
    if active.get('davideferante',0)>=5:raise ValueError('no owner slot')
    src=HERE/'tian_resume_r2/tian2019_ipsc';stage=out/'stage';stage.mkdir()
    files={n:(src/n).read_bytes() for n in ('bank.py','preparation.py','materialize_samples.py','params.json','raw_files.json','raw_complete.json')}
    runtime=(src/'archive_runtime.py').read_text()
    old="        bank=banks[0]; r=json.loads((bank/'complete.json').read_text())"
    new='''        mounted=banks[0];bank=Path('/kaggle/working/reused_bank')
        bank.mkdir(exist_ok=False)
        for name in ('complete.json','rows.csv','mask.npz','samples.jsonl.gz'):
            source=mounted/(name+'.bin') if name=='samples.jsonl.gz' else mounted/name
            shutil.copyfile(source,bank/name)
        r=json.loads((bank/'complete.json').read_text())'''
    if runtime.count(old)!=1:raise ValueError('frozen runtime differs')
    files['archive_runtime.py']=runtime.replace(old,new).encode()
    for name,raw in files.items():(stage/name).write_bytes(raw)
    code=pack(files);(stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    meta=json.loads((src/'kernel-metadata.json').read_text());slug='vcc-derivatives-tian2019-ipsc-resume-r4'
    meta.update(id='davideferante/'+slug,title=slug)
    (stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
    proof={'code_sha256':sha(stage/'run.py'),'input':{'dataset':ref,**version},'bank':json.loads(files['params.json'])['resume_bank']}
    (stage/'prepared.json').write_text(json.dumps(proof,indent=1))
    rc,answer=call('davideferante',['kernels','push','-p',str(stage)])
    ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
    record={'slug':meta['id'],'accepted':ok,'answer':answer,'utc':datetime.now(timezone.utc).isoformat(),
            'stage':str(stage.resolve()),**proof}
    (out/'launches.jsonl').write_text(json.dumps(record)+'\n')
    if not ok:raise RuntimeError('inspect rejected push')
    print(json.dumps({'accepted':meta['id'],'input_version':version['current_version_number']}))


if __name__=='__main__':main()
