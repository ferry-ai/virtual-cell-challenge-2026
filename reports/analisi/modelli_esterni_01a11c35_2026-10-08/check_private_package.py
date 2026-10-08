"""Read-only static package audit, including POSIX paths; never print payloads."""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile


def check(prepared_path):
    prepared=json.loads(Path(prepared_path).read_text())
    source=(Path(prepared['stage'])/'run.py').read_bytes()
    if hashlib.sha256(source).hexdigest()!=prepared['code_sha256']:
        raise ValueError('code changed')
    tree=ast.parse(source)
    assignments={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    root=ast.literal_eval(assignments['root'].args[0])
    if not PurePosixPath(root).is_absolute() or '\\' in root or not root.startswith('/kaggle/temp/'):
        raise ValueError('bundle must be absolute POSIX scratch path')
    payload=ast.literal_eval(assignments['payload'])
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(payload))) as archive:
        contract=json.loads(archive.read('preflight.json'))
        for item in contract['inputs']:
            path=item['paths']['runtime']
            if '\\' in path or PurePosixPath(path).parent != PurePosixPath(root):
                raise ValueError('runtime input path differs from extraction')
            data=archive.read(PurePosixPath(path).name)
            if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
                raise ValueError('packed input hash or size differs')
        for item in contract['outputs']:
            path=item['paths']['runtime']
            if not path.startswith('/kaggle/working/') or '\\' in path or not item['must_be_absent']:
                raise ValueError('invalid output path')
        for name in archive.namelist():
            if name.endswith('.py'):compile(archive.read(name),name,'exec')
        config=json.loads(archive.read('job_config.json'))
        if len(config['queries'])!=prepared['queries']:
            raise ValueError('query count differs')
    result=dict(status='PASS',job_id=prepared['job_id'],source_sha256=prepared['code_sha256'],
                inputs=len(contract['inputs']),all_runtime_paths_posix=True,
                inputs_read='package only; no response arrays or network',payload_printed=False)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();result=check(a.prepared)
    with Path(a.out).open('x',encoding='utf-8') as f:json.dump(result,f,indent=1)
    print(json.dumps(result))
