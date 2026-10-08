"""Prepare the private final T2 fit after every common input has a receipt.

The runnable package contains private numerical vectors and is stored outside
the public repository. Only code, parameters without arrays, and pins go here.
"""
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
import zlib
import numpy as np
from percorso import DATA,HERE,ROOT,now,pin,read,sha,write_new


def one_receipt(kind,revision,unit):
    folder=HERE/kind/revision/unit;hits=list(folder.glob('completion_*/verification.json'))
    if len(hits)!=1:raise ValueError('one verified completion required: '+unit)
    filename='common_receipt.json' if kind=='common_cd4' else 'effect_release.json'
    path=hits[0].with_name(filename);receipt=read(path)
    if sha(path)!=read(hits[0])['receipt']['sha256']:raise ValueError('changed receipt')
    if receipt['split']['regime']!='production':raise ValueError('production common required')
    if kind=='common_cd4':item=receipt['output']
    else:
        if len(receipt['contexts'])!=1:raise ValueError('single biological context required')
        item=receipt['outputs']['effects/'+receipt['contexts'][0]['common_file']]
    return dict(file={k:item[k] for k in ('bytes','sha256')},source_receipt=pin(path)),read(folder/'prepared.json')['slug']


def prepare():
    t1=HERE/'fit/dt1-01a11c34-r1/package';stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/t2_fit_r1/package'
    # Verify all dependencies before creating any output.
    sources={};kernels=set()
    for name in ('hepg2_nadig','jurkat_nadig','rpe1','k562_essential','kolf_chromatin','kolf_metabolic','kolf_pan_genome','kolf_strong','orion_hct116','orion_hek293t'):
        sources[name],producer=one_receipt('alltargets','01a11c34-r3',name);kernels.add(producer)
    sources['h1'],producer=one_receipt('joint','01a11c34-j2p','h1');kernels.add(producer)
    sources['cd4_mix'],producer=one_receipt('common_cd4','01a11c34-r1','production');kernels.add(producer)
    members={'final_t2_driver.py':(HERE/'final_t2_driver.py').read_bytes()}
    local={'k562':read(HERE/'k562_bulk_common_r1.json')['outputs']['production']['file']}
    for name,tag in [('hipsci_targeted_19','hipsci_production_r1'),('xu2023','xu2023_production_r1'),('tian2021_crispri','tian2021_crispri_production_r1')]:
        evidence=read(HERE/'common_inputs'/(tag+'.json'))
        if not evidence['sha256_verified']:raise ValueError('local common unverified')
        local[name]=evidence['output']
    import pandas as pd
    genes=pd.read_csv(DATA/'raw/controls/gene_names.csv').iloc[:,0].astype(str).tolist()
    for name,evidence in local.items():
        path=Path(evidence['path'])
        if sha(path)!=evidence['sha256']:raise ValueError('local common changed')
        with np.load(path,allow_pickle=False) as z:
            if z['genes'].astype(str).tolist()!=genes:raise ValueError('local common axis changed')
            arrays={k:z[k] for k in ('common','mask','contributing_targets')}
        buffer=io.BytesIO();np.savez_compressed(buffer,**arrays)
        filename='embedded_common/'+name+'.npz';members[filename]=buffer.getvalue()
        sources[name]=dict(embedded_file=filename,file=dict(bytes=len(buffer.getvalue()),sha256=hashlib.sha256(buffer.getvalue()).hexdigest()),
            original_npz=evidence,serialization='same array values and dtypes; duplicate gene strings omitted after exact axis verification')
    if set(sources)!=set(read(HERE/'release_t1_r1.json')['voted']):raise ValueError('incomplete T2 common sources')
    code=(t1/'run.py').read_text();match=re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)",code)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as z:
        original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
    original_params=json.loads(original['params.json'])
    for name,digest in original_params['embedded_sha256'].items():
        if hashlib.sha256(original[name]).hexdigest()!=digest:raise ValueError('T1 package changed')
    needed=set(original_params['embedded_sha256'])|{'params.json','release.json'}
    inventory=set(read(HERE/'t1_output_inventory_r1.json')['files'])
    if needed-inventory:raise ValueError('T1 mount omits needed files: '+str(sorted(needed-inventory)))
    restore={n:dict(bytes=len(original[n]),sha256=hashlib.sha256(original[n]).hexdigest()) for n in needed}
    assembly=dict(t1_params_sha256=sha(t1/'params.json'),common_sources=sources,
        t1_effects={c:read(HERE/'fit/dt1-01a11c34-r1/verification.json')['effects'][c]['sha256'] for c in ('A','B','C')},
        t1_release=pin(HERE/'release_t1_r1.json'),protocol=pin(HERE/'PROTOCOLLO.md'),
        source_restore=restore,claims_complete_corpus=False)
    members['assembly_params.json']=(json.dumps(assembly,indent=1)+'\n').encode()
    payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()}
    bootstrap='import os,sys,base64,zlib,hashlib,runpy,json,subprocess,importlib.metadata as md\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\n'
    bootstrap+='P='+repr(payload)+'\n'
    bootstrap+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)\n'
    bootstrap+='a=json.loads(Path("assembly_params.json").read_text())\n'
    bootstrap+='for n,p in a["source_restore"].items():\n hits=[q for q in Path("/kaggle/input").rglob(Path(n).name) if q.is_file() and q.stat().st_size==p["bytes"] and hashlib.sha256(q.read_bytes()).hexdigest()==p["sha256"]];assert hits,n;q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(hits[0].read_bytes())\n'
    bootstrap+='core={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\nPath("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\n'
    bootstrap+='subprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0"])\nassert {n:md.version(n) for n in core}==core\n'
    bootstrap+='runpy.run_path("final_t2_driver.py",run_name="__main__")\n';ast.parse(bootstrap)
    if len(bootstrap.encode())>900000:raise ValueError('runnable package exceeds conservative source limit')
    stage.mkdir(parents=True,exist_ok=False);(stage/'run.py').write_text(bootstrap,encoding='utf-8',newline='\n')
    (stage/'assembly_params.json').write_bytes(members['assembly_params.json'])
    metadata=read(t1/'kernel-metadata.json');kernels.update(metadata['kernel_sources']);kernels.add('davideferrante11/vcc-fit-banca-canonica-dt1-01a11c34-r1')
    slug='davideferrante11/dt-final-t2-01a11c34-r1'
    metadata.update(id=slug,title=slug.split('/')[1],is_private=True,kernel_sources=sorted(kernels))
    write_new(stage/'kernel-metadata.json',metadata)
    folder=HERE/'final_t2/r1';folder.mkdir(parents=True,exist_ok=False)
    write_new(folder/'prepared.json',dict(utc=now(),slug=slug,owner='davideferrante11',stage=str(stage),
        code=pin(stage/'run.py'),params=pin(stage/'assembly_params.json'),metadata=pin(stage/'kernel-metadata.json'),
        common_sources=sources,kernels=len(kernels),datasets=len(metadata['dataset_sources']),
        validation='syntax and dependency pins; real run must reproduce T1 byte hashes before T2',
        compute_authorized=False,private_vectors_remain_outside_public_repository=True))
    print(json.dumps(dict(slug=slug,code_bytes=len(bootstrap),kernels=len(kernels),datasets=len(metadata['dataset_sources']))))


if __name__=='__main__':prepare()
