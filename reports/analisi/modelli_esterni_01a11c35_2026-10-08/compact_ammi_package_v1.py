"""Losslessly repack existing private metadata/code below a conservative source bound."""
import argparse
import ast
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path
import zipfile
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256


def pin(path):return dict(path=str(path),bytes=path.stat().st_size,sha256=sha256(path))


def compact(prepared_path,out,receipt):
    prepared=json.loads(Path(prepared_path).read_text());source=checked(prepared['code']).read_text()
    checked(prepared['metadata']);out=Path(out)
    if out.exists():raise FileExistsError(out)
    values={node.targets[0].id:ast.literal_eval(node.value) for node in ast.parse(source).body
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
            and node.targets[0].id in ('PAYLOAD','DIGEST','BUNDLE','TEMPLATE','MODE','OUTPUT')}
    old=base64.b64decode(values['PAYLOAD'])
    if hashlib.sha256(old).hexdigest()!=values['DIGEST']:raise ValueError('original archive differs')
    with zipfile.ZipFile(io.BytesIO(old)) as archive:
        members={name:archive.read(name) for name in archive.namelist()}
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,body in members.items():archive.writestr(name,body)
    raw=buffer.getvalue();packed=lzma.compress(raw,preset=6)
    with zipfile.ZipFile(io.BytesIO(lzma.decompress(packed))) as archive:
        if set(archive.namelist())!=set(members):raise ValueError('repacked members differ')
        for name,body in members.items():
            if archive.read(name)!=body:raise ValueError('repacked member changed')
    values['PAYLOAD']=base64.b64encode(packed).decode();values['DIGEST']=hashlib.sha256(raw).hexdigest()
    body=source[source.index('import base64,hashlib,io,json,sys,zipfile'):]
    body=body.replace('import base64,hashlib,io,json,sys,zipfile','import base64,hashlib,io,json,sys,zipfile,lzma',1)
    body=body.replace('raw=base64.b64decode(PAYLOAD)','raw=lzma.decompress(base64.b64decode(PAYLOAD))',1)
    code='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+body
    compile(code,'run.py','exec')
    if len(code.encode())>=1_000_000:raise ValueError('source still exceeds conservative 1MB bound')
    out.mkdir(parents=True);(out/'run.py').write_text(code,encoding='utf-8')
    (out/'kernel-metadata.json').write_bytes(checked(prepared['metadata']).read_bytes())
    report=dict(prepared,stage=str(out),code=pin(out/'run.py'),metadata=pin(out/'kernel-metadata.json'),
        original_prepared=pin(Path(prepared_path)),lossless_repack=dict(members=len(members),
            extracted_bytes_identical=True,unpacked_archive_bytes=len(raw),compressed_bytes=len(packed)))
    write(receipt,report)
    print(json.dumps(dict(slug=report['slug'],code_bytes=report['code']['bytes'],members_verified=len(members))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for key in ('prepared','out','receipt'):p.add_argument('--'+key,required=True)
    a=p.parse_args();compact(a.prepared,a.out,a.receipt)
