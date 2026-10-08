"""Prepare immutable CPU jobs from canonical metadata, without launching them.

The full Gencode GTF supplies exact single-gene names, including genes outside
the response axis. It does not decode guides or delimiters. All failures remain
named in the inventory. Partial identity mappings never claim full D-053 coverage.
"""
from __future__ import annotations
import argparse
import ast
import base64
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import zlib
import pandas as pd
from percorso import BANK, DATA, HERE, ROOT, now, pin, read, sha, write_new
from fold_bank import select_rows, validate_split


def canonical():
    spec=importlib.util.spec_from_file_location('old_bank',BANK/'percorso.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def gene_vocabulary():
    path=DATA/'external/annotation/gencode.v50.basic.annotation.gtf.gz'
    names=set()
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'): continue
            cols=line.rstrip('\n').split('\t')
            if len(cols)==9 and cols[2]=='gene':
                match=re.search(r'gene_name "([^"]+)"',cols[8])
                if match: names.add(match.group(1))
    if len(names)<20000:
        raise ValueError('annotation is not a full target vocabulary')
    return names,dict(**pin(path),policy='exact Gencode v50 gene_name, no guide or alias inference')


def prepare(split_path, revision, units=None):
    split=read(split_path); validate_split(split)
    old=canonical(); expected=old.expected_units()
    folder=HERE/'alltargets'/revision
    folder.mkdir(parents=True,exist_ok=False)
    vocabulary,evidence=gene_vocabulary()
    # Freeze the consumer once per campaign, before any per-unit packaging.
    frozen_sources={name:(HERE/name).read_bytes() for name in ('fold_bank.py','alltarget_runtime.py')}
    frozen_sources['estimator.py']=(BANK/'consumer/estimator.py').read_bytes()
    wanted=set(units or expected)
    if wanted-set(expected): raise ValueError('unknown bank unit')
    inventory={}
    axis=DATA/'raw/controls/gene_names.csv'
    for unit,record in sorted(expected.items()):
        if unit not in wanted:
            inventory[unit]=dict(state='outside_this_technical_batch',work_remains=True); continue
        if not record.get('bank',{}).get('files'):
            inventory[unit]=dict(state='blocked_partitioned_bank_requires_joint_merge',work_remains=True); continue
        rowparts=old.rows_of(unit)
        if len(rowparts)!=1:
            inventory[unit]=dict(state='blocked_multiple_bank_parts',parts=len(rowparts),work_remains=True); continue
        _,records=rowparts[0]
        rows=pd.DataFrame(records)
        rows['n']=pd.to_numeric(rows['n'])
        labels=sorted(set(rows.target)&vocabulary)
        mappings={name:dict(target=name,components=[name],evidence=evidence) for name in labels}
        frame,selection=select_rows(rows,mappings,split,unit)
        inventory[unit]=dict(state='planned',native_labels=len(set(rows.target)),exact_single_genes=len(labels),
            admission=selection['cells_by_role'],bank_cells=selection['bank_cells'],
            biological_strata=0 if frame.empty else len(frame.groupby(['study','line_group','context','donor_or_clone','condition','modality','chemistry'])),
            mapping_unresolved_is_open_gap=True)
        if frame.empty or not (frame.target!='non-targeting').any():
            inventory[unit]['state']='no_resolved_training_targets'; continue
        bank=old.unit_pins(unit,record)
        owner=bank['mount']['ref'].split('/')[0]
        job='dt-all-'+unit.lower().replace('_','-')+'-'+revision
        slug=owner+'/'+job
        stage=folder/unit/'package'; stage.mkdir(parents=True)
        sources=dict(frozen_sources)
        sources['gene_names.csv']=axis.read_bytes()
        params=dict(job_id=job,unit=unit,bank=bank,split=split,split_pin=pin(split_path),
            recipe=old.RECIPE,resolved_labels=labels,mapping_evidence=evidence,chunk_targets=128,
            embedded={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in sources.items()},
            input_registry_sha256=old.EXPECTED_SHA,claims_complete_corpus=False,
            incident_ids=['E-20260929-003','E-20260929-004','E-20260929-005'],
            guards=['incremental context receipts','full axis and input hashes','no latest fallback','split before statistics'])
        params_bytes=(json.dumps(params,separators=(',',':'))+'\n').encode()
        sources['params.json']=params_bytes
        payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest()) for n,b in sources.items()}
        code='import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
        code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n'
        code+='runpy.run_path("alltarget_runtime.py",run_name="__main__")\n'
        ast.parse(code)
        if len(code)>900000: raise ValueError('code payload too large')
        (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
        (stage/'params.json').write_bytes(params_bytes)
        mount=bank['mount']
        meta=dict(id=slug,title=job,code_file='run.py',language='python',kernel_type='script',
            is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=False,
            dataset_sources=[mount['ref']] if mount['kind']=='dataset' else [],
            kernel_sources=[mount['ref']] if mount['kind']=='kernel' else [],competition_sources=[])
        write_new(stage/'kernel-metadata.json',meta)
        proof=dict(utc=now(),slug=slug,owner=owner,stage=stage.relative_to(ROOT).as_posix(),
            code=pin(stage/'run.py'),params=pin(stage/'params.json'),metadata=pin(stage/'kernel-metadata.json'),
            scope='all eligible exact single-gene targets; split and per-context masks; no model fit',
            compute_started=False,public=False)
        write_new(folder/unit/'prepared.json',proof)
        inventory[unit].update(state='package_ready',slug=slug,package=proof['stage'])
    write_new(folder/'inventory.json',dict(utc=now(),split=split,split_pin=pin(split_path),mapping_evidence=evidence,
        vocabulary_genes=len(vocabulary),units=inventory,claims_complete_corpus=False,started_jobs=0))
    print(json.dumps(dict(packages=sum(v['state']=='package_ready' for v in inventory.values()),units=len(inventory),vocabulary_genes=len(vocabulary))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('split',type=Path);p.add_argument('revision');p.add_argument('--units',nargs='+')
    a=p.parse_args();prepare(a.split,a.revision,a.units)
