"""Assemble a private frozen T3 fit and generation job outside the public repo."""
import ast
import base64
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import re
import zipfile
from percorso import DATA,HERE,ROOT,pin,read,sha,write_new,now


def unpack(path):
    source=Path(path).read_text()
    match=re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)",source)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as archive:
        members={i.filename:archive.read(i) for i in archive.infolist() if not i.is_dir()}
    params=json.loads(members['params.json'])
    for name,digest in params['embedded_sha256'].items():
        if hashlib.sha256(members[name]).hexdigest()!=digest:raise ValueError('original embedded file changed')
    return members,params


def prepare():
    folder=HERE/'extended_transfer/r1'
    protocol=folder/'protocol.json';plan=read(protocol)
    if sha(protocol)!='ab0bf8946a3ed98d74bf9752af71073cf6c97eca87a9066bfe46ca9a0b780958':raise ValueError('protocol changed')
    prediction=ROOT/'reports/invii/prediction_t38_2026-10-09/prediction.json'
    if read(prediction)['protocol_sha256']!=sha(protocol):raise ValueError('prediction protocol differs')
    private=read(folder/'private_access_prepared.json')
    locator=Path(private['private_locators']['path'])
    if sha(locator)!=private['private_locators']['sha256']:raise ValueError('private locator file changed')
    auth=read(folder/'private_transfer_authorization.json')
    if auth['bytes']!=private['bytes'] or auth['chunks']!=private['chunks'] or not auth['human_answer']:
        raise ValueError('private access authorization differs')
    t1=HERE/'fit/dt1-01a11c34-r1/package'
    members,t1params=unpack(t1/'run.py')
    original=ROOT/'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package'
    if sha(original/'run.py')!='4a49bc7880dc9b877d71a9dd3b3bfc01ea4e584214ea0355fc98fd3c1293b021':
        raise ValueError('successful emission runtime changed')
    generation,gparams=unpack(original/'run.py')
    for name in ('generate_contract.py','repo/scripts/45_generate_prediction.py','repo/scripts/48_package_prediction.py'):
        if members[name]!=generation[name]:raise ValueError('fit/emission runtime versions differ')
    members['emission_support.py']=generation['driver.py']
    for filename in ('extended_generation_driver.py','extended_transfer_runtime.py','extended_transfer_core.py','quick_generation_driver.py'):
        members[filename]=(HERE/filename).read_bytes()
    helper=ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08/private_download_v2.py'
    members['private_download_v2.py']=helper.read_bytes()
    members['extended_protocol.json']=protocol.read_bytes()
    members['private_ko_locators.json']=locator.read_bytes()
    members['prediction_registered.json']=prediction.read_bytes()
    for name,payload in members.items():
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('non-POSIX/unsafe bundle path')
        if name.endswith('.py'):ast.parse(payload,filename=name)
    params=dict(job_id='dt-t3-fit-generate-01a11c34-r1',product='prediction_t38_T3.vcc',
        protocol=pin(protocol),prediction=pin(prediction),private_authorization=pin(folder/'private_transfer_authorization.json'),
        t1_effects=read(HERE/'candidate_t1_r1.json')['production_effects'],
        controls=gparams['controls'],axis=gparams['axis'],emission=read(prediction)['generator'],
        original_runtime=pin(original/'run.py'),transport_helper=pin(helper),
        embedded_sha256={n:hashlib.sha256(b).hexdigest() for n,b in members.items()},
        incident_ids=['E-20260929-003','E-20260929-004','E-20260929-005'],
        authorization=plan['authorization'],private_only=True,submit_in_kernel=False)
    members['extended_params.json']=(json.dumps(params,indent=1)+'\n').encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,payload in sorted(members.items()):z.writestr(name,payload)
    encoded=base64.b64encode(stream.getvalue()).decode()
    code='import os,sys,base64,hashlib,zipfile,io,runpy\nfrom pathlib import Path,PurePosixPath\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\n'
    code+='archive=base64.b64decode('+repr(encoded)+')\nassert hashlib.sha256(archive).hexdigest()=='+repr(hashlib.sha256(stream.getvalue()).hexdigest())+'\n'
    code+='with zipfile.ZipFile(io.BytesIO(archive)) as z:\n for n in z.namelist():\n  p=PurePosixPath(n);assert not p.is_absolute() and ".." not in p.parts and chr(92) not in n;q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(n))\n'
    code+='import subprocess,importlib.metadata as md,json\ncore={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\n'
    code+='Path("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\n'
    code+='subprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0"])\nassert {n:md.version(n) for n in core}==core\n'
    code+='Path("runtime_versions.json").write_text(json.dumps({n:md.version(n) for n in (*core,"anndata","zstandard")},indent=2))\nrunpy.run_path("extended_generation_driver.py",run_name="__main__")\n'
    ast.parse(code)
    if len(code.encode())>900000:raise ValueError('provider source length limit')
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/extended_transfer/r1/package'
    stage.mkdir(parents=True,exist_ok=False)
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    (stage/'extended_params.json').write_bytes(members['extended_params.json'])
    meta=read(t1/'kernel-metadata.json')
    access=read(folder/'native_access_r2.json')
    meta.update(id='davideferrante11/'+params['job_id'],title=params['job_id'],is_private=True,enable_internet=True,
        enable_gpu=False,enable_tpu=False,
        kernel_sources=sorted(set(meta['kernel_sources'])|{s['source'] for s in access['sources'] if s['native_admissible']}),
        dataset_sources=sorted(set(meta['dataset_sources'])|{'davideferrante11/vcc-official-controls-r1'}))
    write_new(stage/'kernel-metadata.json',meta)
    receipt=dict(utc=now(),slug=meta['id'],owner='davideferrante11',stage=str(stage),private=True,
        code=pin(stage/'run.py'),params=pin(stage/'extended_params.json'),metadata=pin(stage/'kernel-metadata.json'),
        protocol=pin(protocol),prediction=pin(prediction),transport_helper=pin(helper),
        private_locators_outside_git=True,private_rna_downloaded_locally=False,
        kernels=meta['kernel_sources'],datasets=meta['dataset_sources'],source_bytes=len(code.encode()),
        new_compute_started=False,submission_started=False,scientific_promotion=False)
    write_new(folder/'prepared.json',receipt)
    write_new(folder/'params.json',params)
    print(json.dumps({k:receipt[k] for k in ('slug','source_bytes','private','new_compute_started')}))


if __name__=='__main__':prepare()
