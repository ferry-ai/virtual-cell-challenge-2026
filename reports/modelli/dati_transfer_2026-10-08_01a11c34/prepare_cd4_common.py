"""Prepare a pinned CD4 common-vector job from three verified condition receipts."""
import argparse
import ast
import base64
import hashlib
import json
import zlib
from percorso import DATA,HERE,ROOT,now,pin,read,sha,write_new


def prepare(regime):
    revision='01a11c34-j2'+('p' if regime=='production' else 't');conditions=[];producers=[];split=None
    for name in ('cd4_Rest','cd4_Stim8hr','cd4_Stim48hr'):
        folder=HERE/'joint'/revision/name
        verified=list(folder.glob('completion_*/verification.json'))
        if len(verified)!=1:raise ValueError('one verified completion required: '+name)
        receipt_path=verified[0].with_name('effect_release.json');r=read(receipt_path);v=read(verified[0]);proof=read(folder/'prepared.json')
        if sha(receipt_path)!=v['receipt']['sha256'] or len(r['contexts'])!=1 or r['contexts'][0]['status']!='derived':raise ValueError('invalid condition receipt')
        if split is not None and split!=r['split']:raise ValueError('split differs')
        split=r['split'];c=r['contexts'][0]
        chunks=[dict(r['outputs']['effects/'+x['file']],producer_file='effects/'+x['file']) for x in c['chunks']]
        conditions.append(dict(name=name,split=split,identity=c['identity'],chunks=chunks,receipt=pin(receipt_path),targets=len(c['targets_derived'])))
        producers.append(proof['slug'])
    members={n:(HERE/n).read_bytes() for n in ('common_stream.py','cd4_common_runtime.py')}
    members['gene_names.csv']=(DATA/'raw/controls/gene_names.csv').read_bytes()
    slug='davideferrante11/dt-common-cd4-'+regime.lower()+'-01a11c34-r1'
    params=dict(split=split,conditions=conditions,recipe='mix per target/gene at reliability=100, then equal target mean',
        embedded={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()})
    members['params.json']=(json.dumps(params,separators=(',',':'))+'\n').encode()
    payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()}
    code='import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
    code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n'
    code+='runpy.run_path("cd4_common_runtime.py",run_name="__main__")\n';ast.parse(code)
    stage=HERE/'common_cd4/01a11c34-r1'/regime/'package';stage.mkdir(parents=True,exist_ok=False)
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n');(stage/'params.json').write_bytes(members['params.json'])
    write_new(stage/'kernel-metadata.json',dict(id=slug,title=slug.split('/')[1],code_file='run.py',language='python',kernel_type='script',
        is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=False,kernel_sources=sorted(producers),dataset_sources=[],competition_sources=[]))
    write_new(stage.parent/'prepared.json',dict(utc=now(),slug=slug,owner=slug.split('/')[0],regime=regime,stage=stage.relative_to(ROOT).as_posix(),
        code=pin(stage/'run.py'),params=pin(stage/'params.json'),metadata=pin(stage/'kernel-metadata.json'),
        sources=conditions,compute_authorized=False,started=False))
    print(json.dumps(dict(slug=slug,code_bytes=len(code),condition_targets=[c['targets'] for c in conditions])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('regime',choices=['production','T']);prepare(p.parse_args().regime)
