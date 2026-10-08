"""Retrieve and independently hash one small common vector of our derived job."""
import argparse
from pathlib import Path
from cloud_campaign import call
from percorso import DATA,HERE,now,pin,read,sha,write_new


def main(kind,revision,unit,tag):
    folder=HERE/kind/revision/unit;proof=read(folder/'prepared.json')
    checks=list(folder.glob('completion_*/verification.json'))
    if len(checks)!=1:raise ValueError('one verified completion required')
    source=checks[0].with_name('common_receipt.json' if kind=='common_cd4' else 'effect_release.json')
    receipt=read(source)
    if sha(source)!=read(checks[0])['receipt']['sha256']:raise ValueError('receipt identity changed')
    if kind=='common_cd4':filename=receipt['output']['file'];expected=receipt['output']
    else:
        if len(receipt['contexts'])!=1:raise ValueError('explicit joint context required')
        filename='effects/'+receipt['contexts'][0]['common_file'];expected=receipt['outputs'][filename]
    dest=DATA/'processed/dati_transfer_2026-10-08_01a11c34/common_objects'/tag;dest.mkdir(parents=True,exist_ok=False)
    import re
    rc,body=call(proof['owner'],['kernels','output',proof['slug'],'-p',str(dest),'--file-pattern','^'+re.escape(filename)+'$'])
    path=dest/filename
    verification=path.is_file() and path.stat().st_size==expected['bytes'] and sha(path)==expected['sha256']
    out=HERE/'common_inputs';out.mkdir(exist_ok=True)
    write_new(out/(tag+'.json'),dict(utc=now(),producer=proof['slug'],source_receipt=pin(source),
        output=pin(path) if path.is_file() else None,expected=expected,sha256_verified=verification,
        retrieval=dict(returncode=rc,answer=body),regime=receipt['split']['regime'],split=receipt['split']))
    if rc or not verification:raise ValueError('common retrieval or hash failed')
    print(tag,expected['bytes'],'bytes; independently verified')


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('kind');parser.add_argument('revision');parser.add_argument('unit');parser.add_argument('tag')
    a=parser.parse_args();main(a.kind,a.revision,a.unit,a.tag)
