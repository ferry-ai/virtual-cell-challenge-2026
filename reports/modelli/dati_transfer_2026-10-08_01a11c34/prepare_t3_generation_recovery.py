"""Prepare generation-only recovery from the verified T3 effect, within df11."""
import ast
import base64
import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile
from percorso import DATA,HERE,ROOT,pin,read,sha,write_new,now
from prepare_extended_generation import unpack
from quick_generation_cloud import api_for_owner


def main(revision=1):
    fit_folder=HERE/'extended_transfer/r1';fit_path=fit_folder/'fit_completion_r1/t3_consumption.json'
    fit=read(fit_path);verified=read(fit_path.with_name('verification.json'))
    if not verified['T1_null_parity'] or verified['required_chunks_verified']!=22:raise ValueError('fit not verified')
    original=ROOT/'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package'
    members,old=unpack(original/'run.py')
    if sha(original/'run.py')!='4a49bc7880dc9b877d71a9dd3b3bfc01ea4e584214ea0355fc98fd3c1293b021':raise ValueError('original runtime changed')
    members['emission_support.py']=members.pop('driver.py')
    drivers={1:'generate_t3_existing.py',2:'generate_t3_existing_v2.py',3:'generate_t3_existing_v3.py',4:'generate_t3_existing_v4.py'}
    members['driver.py']=(HERE/drivers[revision]).read_bytes()
    if revision in (3,4):
        name='repo/src/vcc2026/submission.py'
        before=members[name].decode()
        old_default='compression: str | None = "gzip",'
        if before.count(old_default)!=1:raise ValueError('unexpected frozen storage constructor')
        after=before.replace(old_default,('compression: str | None = None,' if revision==3 else 'compression: str | None = "lzf",'))
        if revision==4:
            if after.count('compression_opts: int | None = 4,')!=1:raise ValueError('unexpected filter options')
            after=after.replace('compression_opts: int | None = 4,','compression_opts: int | None = None,')
        members[name]=after.encode()
    members['quick_generation_driver.py']=(HERE/'quick_generation_driver.py').read_bytes()
    helper=ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08/private_download_v2.py'
    if sha(helper)!='ea9345e7f5913b39c80d7917dc766342ab880d8ad184746a5a5c4f95113a78c0':raise ValueError('transport helper changed')
    members['private_download_v2.py']=helper.read_bytes()
    prediction=ROOT/'reports/invii/prediction_t38_2026-10-09/prediction.json'
    members['prediction_registered.json']=prediction.read_bytes()
    members['t3_consumption.json']=fit_path.read_bytes()
    protocol=fit_folder/'protocol.json';members['extended_protocol.json']=protocol.read_bytes()
    source=read(fit_folder/'prepared.json')['slug']
    # An owner-private final effect stays within the same account and runtime purpose.
    api=api_for_owner('davideferrante11')
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
    req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=source.split('/');req.page_size=100
    found=[]
    while True:
        with api.build_kaggle_client() as client:value=client.kernels.kernels_api_client.list_kernel_session_output(req)
        found.extend(x for x in value.files or [] if x.file_name=='effects/effects_A.npz')
        if not value.next_page_token:break
        req.page_token=value.next_page_token
    if len(found)!=1:raise ValueError('unique frozen T3 effect unavailable')
    members['effect_locator.json']=(json.dumps(dict(url=found[0].url,**fit['effects']['A']))+'\n').encode()
    members.pop('params.json')
    params=dict(job_id='dt-t3-generate-01a11c34-r'+str(revision+1),product='prediction_t38_T3.vcc',
        protocol=pin(protocol),prediction=pin(prediction),fit_receipt=pin(fit_path),source_job=source,
        effects=fit['effects'],controls=old['controls'],axis=old['axis'],
        emission=read(prediction)['generator'],new_fit=False,
        incident_ids=['E-20260929-003','E-20260929-004','E-20260929-005'],
        embedded_sha256={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
    members['params.json']=(json.dumps(params,indent=1)+'\n').encode()
    for n,b in members.items():
        p=PurePosixPath(n)
        if p.is_absolute() or '..' in p.parts or '\\' in n:raise ValueError('invalid bundle path')
        if n.endswith('.py'):ast.parse(b,filename=n)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(members.items()):z.writestr(n,b)
    payload=base64.b64encode(buf.getvalue()).decode()
    code='import os,sys,base64,io,zipfile,hashlib,runpy\nfrom pathlib import Path,PurePosixPath\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\n'
    code+='archive=base64.b64decode('+repr(payload)+')\nassert hashlib.sha256(archive).hexdigest()=='+repr(hashlib.sha256(buf.getvalue()).hexdigest())+'\n'
    code+='with zipfile.ZipFile(io.BytesIO(archive)) as z:\n for n in z.namelist():\n  p=PurePosixPath(n);assert not p.is_absolute() and ".." not in p.parts and chr(92) not in n;q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(n))\n'
    code+='import subprocess,importlib.metadata as md,json\ncore={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\nPath("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\n'
    code+='subprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0"])\nassert {n:md.version(n) for n in core}==core\nrunpy.run_path("driver.py",run_name="__main__")\n'
    ast.parse(code)
    if len(code)>900000:raise ValueError('provider source limit')
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/generation_recovery'/('r'+str(revision))/'package';stage.mkdir(parents=True,exist_ok=False)
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    (stage/'extended_params.json').write_bytes(members['params.json'])
    meta=dict(id='davideferrante11/'+params['job_id'],title=params['job_id'],code_file='run.py',language='python',
        kernel_type='script',is_private=True,enable_internet=True,enable_gpu=False,enable_tpu=False,
        dataset_sources=['davideferrante11/vcc-official-controls-r1'],kernel_sources=[],competition_sources=[])
    write_new(stage/'kernel-metadata.json',meta)
    folder=HERE/'generation_recovery'/('r'+str(revision))
    proof=dict(utc=now(),slug=meta['id'],owner='davideferrante11',stage=str(stage),private=True,
        code=pin(stage/'run.py'),params=pin(stage/'extended_params.json'),metadata=pin(stage/'kernel-metadata.json'),
        protocol=pin(protocol),prediction=pin(prediction),fit_receipt=pin(fit_path),
        new_fit=False,changes=('correct stage45 manifest filename; lossless '+('LZF' if revision==4 else 'uncompressed')+' intermediate CSR with final zstd; salvage intermediates on failure; no scientific change' if revision in (3,4) else 'repeat --effects per context; explicit Linux data/artifact roots; reuse exact frozen T3 effects; no scientific change'),
        code_bytes=len(code),source_job=source,new_compute_started=False)
    write_new(folder/'prepared.json',proof);write_new(folder/'params.json',params)
    print(json.dumps({k:proof[k] for k in ('slug','code_bytes','new_fit','changes')}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,default=1,choices=(1,2,3,4));args=parser.parse_args()
    try:main(args.revision)
    except Exception as exc:
        print('T3 generation recovery preparation failed: '+type(exc).__name__);raise SystemExit(1)
