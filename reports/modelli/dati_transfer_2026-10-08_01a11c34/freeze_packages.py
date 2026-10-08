"""Freeze one consumer snapshot over an already verified metadata plan.

Does not re-read matrices, choose targets, or launch jobs. The old packages are
retained; every new package keeps their pinned bank and target-label evidence.
"""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import zlib
from percorso import BANK,DATA,HERE,ROOT,now,pin,read,sha,write_new


def freeze(old_revision,new_revision,split_path=None,units=None):
    old=HERE/'alltargets'/old_revision; new=HERE/'alltargets'/new_revision
    new.mkdir(parents=True,exist_ok=False)
    inventory=read(old/'inventory.json')
    sources={n:(HERE/n).read_bytes() for n in ('fold_bank.py','alltarget_runtime.py')}
    sources['estimator.py']=(BANK/'consumer/estimator.py').read_bytes()
    if split_path:
        from fold_bank import select_rows,validate_split
        from prepare_alltargets import canonical
        import pandas as pd
        new_split=read(split_path);validate_split(new_split);bank_entry=canonical()
    for unit,entry in inventory['units'].items():
        if units is not None and unit not in units:
            entry.update(state='not_in_this_revision');continue
        if entry['state']!='package_ready': continue
        proof=read(old/unit/'prepared.json'); stage=ROOT/proof['stage']
        for key,name in [('code','run.py'),('params','params.json'),('metadata','kernel-metadata.json')]:
            if sha(stage/name)!=proof[key]['sha256']: raise ValueError('parent package changed')
        params=read(stage/'params.json'); meta=read(stage/'kernel-metadata.json')
        if split_path:
            rows=pd.DataFrame(bank_entry.rows_of(unit)[0][1]);rows['n']=pd.to_numeric(rows.n)
            mapping={t:dict(target=t,components=[t],evidence=params['mapping_evidence']) for t in params['resolved_labels']}
            frame,selection=select_rows(rows,mapping,new_split,unit)
            entry.update(admission=selection['cells_by_role'],bank_cells=selection['bank_cells'])
            params.update(split=new_split,split_pin=pin(split_path))
            if frame.empty or not (frame.target!='non-targeting').any():
                entry.update(state='no_training_targets_after_split');continue
        # The official axis was already embedded by the parent builder; read it from the pinned local file.
        axis=DATA/'raw/controls/gene_names.csv'
        if sha(axis)!=params['embedded']['gene_names.csv']['sha256']:raise ValueError('axis changed')
        members=dict(sources);members['gene_names.csv']=axis.read_bytes()
        job='dt-all-'+unit.lower().replace('_','-')+'-'+new_revision
        params.update(job_id=job,embedded={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()})
        members['params.json']=(json.dumps(params,separators=(',',':'))+'\n').encode()
        payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()}
        code='import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
        code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n'
        code+='runpy.run_path("alltarget_runtime.py",run_name="__main__")\n';ast.parse(code)
        dest=new/unit/'package';dest.mkdir(parents=True)
        (dest/'run.py').write_text(code,encoding='utf-8',newline='\n');(dest/'params.json').write_bytes(members['params.json'])
        meta.update(id=proof['owner']+'/'+job,title=job)
        write_new(dest/'kernel-metadata.json',meta)
        proof.update(utc=now(),slug=meta['id'],stage=dest.relative_to(ROOT).as_posix(),
            code=pin(dest/'run.py'),params=pin(dest/'params.json'),metadata=pin(dest/'kernel-metadata.json'),
            parent_prepared=pin(old/unit/'prepared.json'))
        write_new(new/unit/'prepared.json',proof)
        entry.update(slug=meta['id'],package=proof['stage'])
    inventory.update(utc=now(),parent_inventory=pin(old/'inventory.json'),
        consumer={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in sources.items()})
    if split_path:inventory.update(split=new_split,split_pin=pin(split_path))
    write_new(new/'inventory.json',inventory)
    print(json.dumps(dict(packages=sum(x['state']=='package_ready' for x in inventory['units'].values()),
        revision=new_revision,consumer=inventory['consumer'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('old');p.add_argument('new');p.add_argument('--split',type=Path);p.add_argument('--units',nargs='+')
    a=p.parse_args();freeze(a.old,a.new,a.split,a.units)
