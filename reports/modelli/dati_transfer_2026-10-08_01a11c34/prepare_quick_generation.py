"""Freeze a private T1 emission job, reusing the verified t36 runtime snapshot."""
import ast
import base64
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile
import zlib
from percorso import DATA,HERE,ROOT,pin,read,sha,write_new,now


def prepare():
    original=ROOT/'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package'
    if sha(original/'run.py')!='4a49bc7880dc9b877d71a9dd3b3bfc01ea4e584214ea0355fc98fd3c1293b021':
        raise ValueError('frozen t36 runtime changed')
    prediction_path=ROOT/'reports/invii/prediction_t37_2026-10-08/prediction.json'
    prediction=read(prediction_path)
    candidate_path=HERE/'candidate_t1_r1.json'; candidate=read(candidate_path)
    candidate_sha='28f15de7418fdab741bd0bc61049d6f4c8e843cafd016027101697e11c28a6f5'
    if prediction['candidate']['effect_sha256_each_context']!=candidate_sha:
        raise ValueError('pre-registered candidate differs')
    expected_emission=dict(stage=45,trial='trial-ext-profile',generator_seed=20260912,
        effects_scale=1.5,gene_dispersion=True,gene_dispersion_scale=1,depth_bins=False,
        contexts=['A','B','C'],targets_per_context=300,cells_per_target=400,response_genes=18533,
        controls_included_in_submission=False)
    if any(prediction['generator'].get(k)!=v for k,v in expected_emission.items()):
        raise ValueError('pre-registered emission differs')
    source=(original/'run.py').read_text()
    match=re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)",source)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as z:
        members={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
    old_params=json.loads(members['params.json'])
    for name,digest in old_params['embedded_sha256'].items():
        if hashlib.sha256(members[name]).hexdigest()!=digest:
            raise ValueError('frozen t36 embedded module changed')
    support_source=members.pop('driver.py')
    members['emission_support.py']=support_source
    members['driver.py']=(HERE/'quick_generation_driver.py').read_bytes()
    recipe_path=DATA/'processed/dati_transfer_2026-10-08_01a11c34/t1_r1/recipe_release.json'
    receipt=read(HERE/'fit/dt1-01a11c34-r1/consumo.json')
    if sha(recipe_path)!=receipt['recipe_sha256']:
        raise ValueError('frozen T1 recipe changed')
    members['recipe_t1.json']=recipe_path.read_bytes()
    members['prediction_registered.json']=prediction_path.read_bytes()
    members['candidate_t1.json']=candidate_path.read_bytes()
    members.pop('params.json')
    if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts or '\\' in n for n in members):
        raise ValueError('bundle contains unsafe or non-POSIX paths')
    # Local numerical preflight reads only the existing 18.8 MB candidate arrays.
    # No sampling, biological fitting, generation or training happens locally.
    import numpy as np
    with (DATA/'raw/controls/pert_counts.csv').open() as f:
        panel=[r['target_gene'] for r in csv.DictReader(f)]
    with (DATA/'raw/controls/gene_names.csv').open() as f:
        genes=[r[0] for r in list(csv.reader(f))[1:]]
    checked=[]
    for c,spec in candidate['production_effects'].items():
        if spec['sha256']!=candidate_sha or sha(spec['path'])!=candidate_sha:
            raise ValueError('candidate effect hash changed')
        if not checked:
            with np.load(spec['path'],allow_pickle=False) as z:
                if z['targets'].astype(str).tolist()!=panel or z['genes'].astype(str).tolist()!=genes:
                    raise ValueError('candidate axis differs')
                e,m=z['lfc'],z['observed']
                if e.dtype!=np.float32 or e.shape!=(300,18533) or m.dtype!=bool or m.shape!=e.shape:
                    raise ValueError('candidate dtype/shape differs')
                if not np.isfinite(e).all() or np.any(e[~m]!=0):
                    raise ValueError('candidate numeric contract differs')
        checked.append(c)
    params=dict(job_id='dt-gen-t1-01a11c34-r1',product='prediction_t37_T1.vcc',
        candidate=pin(candidate_path),recipe=pin(recipe_path),prediction=pin(prediction_path),
        original_runtime=pin(original/'run.py'),effects=candidate['production_effects'],
        controls=copy.deepcopy(old_params['controls']),axis=old_params['axis'],
        emission=expected_emission,
        incident_ids=['E-20260929-003','E-20260929-004','E-20260929-005'],
        authorization=dict(thread_id='01a11c05-970e-7af2-a07e-3860bd74acbd',
            human_message_id='01a11d78-c711-7cb1-9f28-fdcf26fbffa2',
            human_text='ok in caso cerchiamo un percorso rapido per buttare sul sito il refit prima delle 2, non servono troppi check post triaing',
            scope='generate/package T1; Lead is the sole submitter; preserve ESM2 jobs'),
        embedded_sha256={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
    params['controls']['note']='Existing owner-private davideferrante11/vcc-official-controls-r1, bytes and hashes checked before generation.'
    members['params.json']=(json.dumps(params,indent=1)+'\n').encode()
    packed=io.BytesIO()
    with zipfile.ZipFile(packed,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,payload in sorted(members.items()): z.writestr(name,payload)
    encoded=base64.b64encode(packed.getvalue()).decode()
    code='import base64,io,os,zipfile,runpy,sys,hashlib\nfrom pathlib import Path,PurePosixPath\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\n'
    code+='archive=base64.b64decode('+repr(encoded)+')\n'
    code+='assert hashlib.sha256(archive).hexdigest()=='+repr(hashlib.sha256(packed.getvalue()).hexdigest())+'\n'
    code+='with zipfile.ZipFile(io.BytesIO(archive)) as z:\n for n in z.namelist():\n  p=PurePosixPath(n);assert not p.is_absolute() and ".." not in p.parts and chr(92) not in n;q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(n))\n'
    # Same constrained dependency installation as the already successful t36 job.
    code+='import subprocess,importlib.metadata as md,json\ncore={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\n'
    code+='Path("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\n'
    code+='subprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0"])\nassert {n:md.version(n) for n in core}==core\n'
    code+='Path("runtime_versions.json").write_text(json.dumps({n:md.version(n) for n in (*core,"anndata","zstandard")},indent=2))\nrunpy.run_path("driver.py",run_name="__main__")\n'
    ast.parse(code)
    if len(code.encode())>=900000: raise ValueError('source exceeds safe provider size')
    for n,b in members.items():
        if n.endswith('.py'): ast.parse(b,filename=n)
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/quick_generation/r1/package'
    stage.mkdir(parents=True,exist_ok=False)
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    (stage/'params.json').write_bytes(members['params.json'])
    meta=dict(id='davideferrante11/'+params['job_id'],title=params['job_id'],code_file='run.py',
        language='python',kernel_type='script',is_private=True,enable_gpu=False,enable_tpu=False,
        enable_internet=True,dataset_sources=['davideferrante11/vcc-official-controls-r1'],
        kernel_sources=['davideferrante11/vcc-fit-banca-canonica-dt1-01a11c34-r1'],competition_sources=[])
    write_new(stage/'kernel-metadata.json',meta)
    report=dict(utc=now(),slug=meta['id'],owner='davideferrante11',private=True,stage=str(stage),
        code=pin(stage/'run.py'),params=pin(stage/'params.json'),metadata=pin(stage/'kernel-metadata.json'),
        prediction=pin(prediction_path),candidate=pin(candidate_path),recipe=pin(recipe_path),
        local_effects_verified=checked,stage45_48_and_scientific_modules_unchanged=True,
        unchanged_runtime_source=pin(original/'run.py'),new_compute_started=False,
        new_fit=False,submit=False,embedded_files=len(members),no_bearer_locators=True)
    write_new(HERE/'quick_generation/r1/prepared.json',report)
    write_new(HERE/'quick_generation/r1/params.json',params)
    print(json.dumps(dict(slug=meta['id'],code_bytes=len(code.encode()),embedded_files=len(members),
                         candidate_effects_verified=checked,new_compute_started=False)))


if __name__=='__main__': prepare()
