"""Lossless larger-dictionary compression for metadata-heavy cells packages."""
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
from compact_ammi_package_v1 import pin


def compact(prepared_path, out, receipt):
    prepared = json.loads(Path(prepared_path).read_text())
    source = checked(prepared['code']).read_text()
    metadata = checked(prepared['metadata'])
    out = Path(out)
    if out.exists() or Path(receipt).exists():
        raise FileExistsError('fresh package and receipt required')
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(source).body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ('PAYLOAD', 'DIGEST', 'BUNDLE', 'TEMPLATE', 'MODE', 'OUTPUT')}
    old = base64.b64decode(values['PAYLOAD'])
    if hashlib.sha256(old).hexdigest() != values['DIGEST']:
        raise ValueError('original archive differs')
    with zipfile.ZipFile(io.BytesIO(old)) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    raw = buffer.getvalue()
    # The 32 MiB dictionary sees duplicate manifests beyond the v1 8 MiB window.
    packed = lzma.compress(raw, preset=8)
    with zipfile.ZipFile(io.BytesIO(lzma.decompress(packed))) as archive:
        if set(archive.namelist()) != set(members):
            raise ValueError('repacked members differ')
        for name, body in members.items():
            if archive.read(name) != body:
                raise ValueError('repacked member changed')
    values['PAYLOAD'] = base64.b64encode(packed).decode()
    values['DIGEST'] = hashlib.sha256(raw).hexdigest()
    body = source[source.index('import base64,hashlib,io,json,sys,zipfile'):]
    body = body.replace('import base64,hashlib,io,json,sys,zipfile',
                        'import base64,hashlib,io,json,sys,zipfile,lzma', 1)
    body = body.replace('raw=base64.b64decode(PAYLOAD)',
                        'raw=lzma.decompress(base64.b64decode(PAYLOAD))', 1)
    code = '\n'.join(k+'='+repr(v) for k, v in values.items())+'\n'+body
    compile(code, 'run.py', 'exec')
    if len(code.encode()) >= 1_000_000:
        raise ValueError('source still exceeds conservative 1MB bound; bytes='+str(len(code.encode())))
    out.mkdir(parents=True)
    (out/'run.py').write_text(code, encoding='utf-8')
    (out/'kernel-metadata.json').write_bytes(metadata.read_bytes())
    report = dict(prepared, stage=str(out), code=pin(out/'run.py'),
                  metadata=pin(out/'kernel-metadata.json'), original_prepared=pin(Path(prepared_path)),
                  lossless_repack=dict(members=len(members), extracted_bytes_identical=True,
                                       unpacked_archive_bytes=len(raw), compressed_bytes=len(packed),
                                       lzma_preset=8, dictionary_bytes=33554432))
    write(receipt, report)
    print(json.dumps(dict(slug=report['slug'], code_bytes=report['code']['bytes'],
                          members_verified=len(members))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for key in ('prepared', 'out', 'receipt'):
        parser.add_argument('--'+key, required=True)
    args = parser.parse_args()
    compact(args.prepared, args.out, args.receipt)
