"""Issue private KO routes for the explicitly requested full-source refit.

No response arrays are downloaded locally. Locators and runnable private bundle
stay outside Git; only aggregate pins and counts are printed.
"""
from collections import defaultdict
import json
import subprocess
import sys
from percorso import DATA,HERE,read,write_new,pin,now


def main():
    protocol=HERE/'extended_transfer/r1/protocol.json';plan=read(protocol)
    access=read(HERE/'extended_transfer/r1/native_access_r2.json')
    private={r['source'] for r in access['sources'] if not r['native_admissible']}
    files=defaultdict(dict)
    for c in plan['chunks'].values():
        if c['producer'] in private:
            files[c['producer']][c['file']]={k:c[k] for k in ('sha256','bytes')}
    if len(private)!=4 or set(files)!=private: raise ValueError('unexpected private producer set')
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/extended_transfer/r1/access'
    stage.mkdir(parents=True,exist_ok=False)
    issued={}
    for producer,required in sorted(files.items()):
        prefix=producer.replace('/','__')
        request=stage/(prefix+'.request.json');output=stage/(prefix+'.private.json')
        write_new(request,required)
        result=subprocess.run([sys.executable,str(HERE/'prepare_runtime_access.py'),'issue',
            'davideferante',producer,str(request),str(output)],capture_output=True,text=True,timeout=240)
        if result.returncode: raise RuntimeError('private output listing failed')
        doc=read(output)
        if doc['producer']!=producer or set(doc['files'])!=set(required): raise ValueError('inventory differs')
        for name,value in doc['files'].items():
            if any(value[k]!=required[name][k] for k in ('bytes','sha256')): raise ValueError('pin differs')
            issued[producer+'/'+name]=value
    locator=stage/'private_locators.json'
    write_new(locator,dict(files=issued,private=True,never_log_or_commit=True,destination='davideferrante11',
        protocol=pin(protocol),utc=now()))
    receipt=dict(utc=now(),protocol=pin(protocol),private_locators=pin(locator),destination='davideferrante11',
        chunks=len(issued),bytes=sum(x['bytes'] for x in issued.values()),
        source_visibility_changed=False,local_rna_downloaded_bytes=0,new_compute=False)
    write_new(HERE/'extended_transfer/r1/private_access_prepared.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('Private KO access preparation failed: '+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
