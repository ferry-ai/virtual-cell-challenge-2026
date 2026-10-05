"""Repair an ERROR producer's mount access once, retaining original verified bytes.

Flat aliases preserve gzip from Kaggle's automatic expansion. Original receipts,
file names, hashes and source versions remain in layout.json. No source recompute.
"""
import hashlib,json,os,re,shutil
from pathlib import Path
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,CONFIG,sha


def main():
    owner='davideferante';os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest
    api=KaggleApi();api.authenticate()
    info=json.loads((HERE/'tian_partial_r1/state.json').read_text())['units']['norman2019']
    job=info['bank']['kernel'];request=ApiGetKernelRequest()
    request.user_name=owner;request.kernel_slug=job.split('/')[1]
    def saved():
        with api.build_kaggle_client() as c: s=c.kernels.kernels_api_client.get_kernel(request)
        return {'version':s.metadata.current_version_number,
                'source_sha256':hashlib.sha256(s.blob.source.encode()).hexdigest()}
    before=saved();expected=info['bank']['saved_version']
    if before!={'version':expected['version'],'source_sha256':expected['saved_source_sha256']}:
        raise ValueError('saved source/version changed')
    proof=HERE/'norman_rehouse_private_r1.json'
    if proof.exists():raise ValueError('inspect existing upload outcome, never duplicate')
    cache=Path('C:/Users/ferra/vcc2026-data/processed/percorso_riusabile_2026-10-05/norman_rehouse_r1')
    output=cache/'dataset';output.mkdir(parents=True,exist_ok=True)
    source=cache/'source';source.mkdir(exist_ok=True)
    files=[];missing=[]
    for kind in ('bank','samples'):
        receipt=REPO/info[kind]['receipt']
        if sha(receipt)!=info[kind]['receipt_sha256']:raise ValueError('original receipt changed')
        value=json.loads(receipt.read_text())
        for name,meta in value['files'].items():
            relative=kind+'/norman2019/'+name;path=source/relative
            if not path.exists():missing.append(relative)
            files.append((relative,path,meta))
        files.append((kind+'/norman2019/complete.json',receipt,
                     {'bytes':receipt.stat().st_size,'sha256':sha(receipt)}))
    if missing:
        api.kernels_output(job,str(source),file_pattern='^('+'|'.join(re.escape(n) for n in missing)+')$')
    layout=[]
    for relative,path,meta in files:
        if path.stat().st_size!=meta['bytes'] or sha(path)!=meta['sha256']:raise ValueError('original bytes differ: '+relative)
        alias=relative.replace('/','__')+('.bin' if relative.endswith('.gz') else '')
        dest=output/alias
        if not dest.exists():os.link(path,dest)
        if sha(dest)!=meta['sha256']:raise ValueError('alias changed')
        layout.append({'original_path':relative,'alias':alias,'bytes':meta['bytes'],'sha256':meta['sha256']})
    if saved()!=before:raise ValueError('source changed during transfer')
    ref=owner+'/vcc-norman-bank-samples-r1'
    manifest={'schema':1,'dataset':ref,'expected_version':1,'source':info,
              'original_saved_version':before,'files':layout,'no_recompute':True}
    (output/'layout.json').write_text(json.dumps(manifest,indent=1),encoding='utf-8',newline='\n')
    (output/'dataset-metadata.json').write_text(json.dumps({'id':ref,'title':'vcc-norman-bank-samples-r1',
            'licenses':[{'name':'other'}],'isPrivate':True}))
    intent={'utc':datetime.now(timezone.utc).isoformat(),'dataset':ref,'expected_version':1,
        'public_requested':False,'layout_sha256':sha(output/'layout.json'),'source':info,
        'files':layout,'downloaded_bytes':sum(m['bytes'] for n,p,m in files if n in missing),
        'reason':'ERROR notebook refused as mount; preserve original successful bank and samples',
        'state':'upload_requested','consumer_runtime_hashes_verified':False}
    proof.open('x').write(json.dumps(intent,indent=1))
    api.dataset_create_new(str(output),public=False,quiet=True,dir_mode='skip',convert_to_csv=False)
    print(json.dumps({'dataset':ref,'downloaded_bytes':intent['downloaded_bytes'],'public_requested':False}))


if __name__=='__main__':main()
