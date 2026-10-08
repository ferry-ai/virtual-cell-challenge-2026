"""Check the private package's full inventory and compatible helper signatures."""
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from percorso import HERE,read,sha,write_new,now,pin


def main():
    folder=HERE/'extended_transfer/r1';proof=read(folder/'prepared.json')
    path=Path(proof['code']['path'])
    if sha(path)!=proof['code']['sha256']:raise ValueError('package changed')
    encoded=re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)",path.read_text()).group(1)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as z:
        members={n:z.read(n) for n in z.namelist()}
    params=json.loads(members['extended_params.json']);original=json.loads(members['params.json'])
    for pins in (params['embedded_sha256'],original['embedded_sha256']):
        for name,digest in pins.items():
            if hashlib.sha256(members[name]).hexdigest()!=digest:raise ValueError('embedded identity differs')
    funcs={node.name:len(node.args.args) for node in ast.parse(members['emission_support.py']).body if isinstance(node,ast.FunctionDef)}
    required={'_verify_embedded':1,'_check_axis':1,'_guard_resources':0,'_run_script':2,'_compact':1}
    if any(funcs.get(name)!=n for name,n in required.items()):raise ValueError('emission helper signatures differ')
    loc=json.loads(members['private_ko_locators.json'])['files'];plan=json.loads(members['extended_protocol.json'])
    if len(loc)!=7 or sum(v['bytes'] for v in loc.values())!=12911661:raise ValueError('private scope differs')
    for key,item in loc.items():
        if any(item[k]!=plan['chunks'][key][k] for k in ('bytes','sha256')):raise ValueError('private pins differ')
    for name,value in members.items():
        if name.endswith('.py'):ast.parse(value,filename=name)
    report=dict(utc=now(),status='PASS',prepared=pin(folder/'prepared.json'),embedded_members=len(members),
        original_T1_files_unchanged=True,emission_helper_signatures=required,private_scope_verified=True,
        private_values_logged=False,all_python_syntax_checked=True,new_compute=False)
    write_new(folder/'bundle_check.json',report);print(json.dumps(report))


if __name__=='__main__':main()
