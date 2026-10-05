"""Reuse the tested bank producer on verified full HCT116/HEK293T archives."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
from pipeline_state import HERE,REPO,sha


def payload(source):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
    return ast.literal_eval(node.value)


def main():
    p=argparse.ArgumentParser();p.add_argument('--line',choices=['HCT116','HEK293T'],required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    origin=REPO/'reports/sorgenti/ingestione_completa_2026-10-03'
    folder=origin/'orion'/('esito_verifica_'+a.line.lower()+'_r1')
    receipt_path=folder/'line_complete.json';receipt=json.loads(receipt_path.read_text())
    retrieval=json.loads((folder/'fetch_receipt.json').read_text())
    if sha(receipt_path)!=retrieval['fetched']['line_complete.json']['sha256']:
        raise ValueError('source receipt differs from recovered original')
    if receipt['partial'] or not receipt['ok'] or not all(receipt['verdict'].values()) or receipt['totals']['cells']!=receipt['expected']['cells']:
        raise ValueError('source archive incomplete')
    axis=json.loads((HERE/'axis_binding_r1.json').read_text())['axis_sha256']
    ledger=list(map(json.loads,(origin/'kaggle_cpu/lancio_orion_r2.jsonl').read_text().splitlines()))
    proofs=[];parts=[];jobs=[];unit='orion_'+a.line.lower()
    for part in receipt['parts']:
        job='davideferrante11/'+part['job'].replace('_','-');jobs.append(job)
        records=[r for r in ledger if r['slug']==job and r.get('accepted')]
        if len(records)!=1:
            raise ValueError('ambiguous raw producer')
        record=records[0];f=Path(record['stage'])/'run.py';s=f.read_text(encoding='utf-8')
        if record['run_sha256'] not in {sha(f),hashlib.sha256(s.encode()).hexdigest()}:
            raise ValueError('raw producer changed')
        node=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
        params=json.loads(ast.literal_eval(node.value.args[0]))
        if params['axis_sha256']!=axis:
            raise ValueError('raw axis differs')
        proofs.append({'kernel':job,'run_sha256':record['run_sha256'],'axis_sha256':axis})
        parts.append({**part,'unit':unit})
    frozen_stage=HERE/'kolf_bank_stage_r1';frozen=json.loads((frozen_stage/'prepared.json').read_text())
    source=(frozen_stage/'run.py').read_text(encoding='utf-8')
    if hashlib.sha256(source.encode()).hexdigest()!=frozen['code_sha256']:
        raise ValueError('tested bank code changed')
    modules=payload(source)
    for name in ('bank.py','preparation.py'):
        if hashlib.sha256(base64.b64decode(modules[name]['data'])).hexdigest()!=modules[name]['sha256']:
            raise ValueError('bank payload changed')
    spec={'name':unit,'line_group':a.line,'expected_contexts':[a.line],
          'cells':receipt['totals']['cells'],'receipt_sha256':sha(receipt_path),'parts':parts}
    raw=json.dumps({'units':[spec]}).encode();modules['params.json']={'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    code='import os,sys,base64,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(modules)+'\n'
    code+='for n,v in P.items():\n b=base64.b64decode(v["data"]);assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
    code+='runpy.run_path("bank.py",run_name="__main__")\n';compile(code,'run.py','exec')
    slug='davideferrante11/vcc-bank-orion-'+a.line.lower()+'-r1'
    meta={'id':slug,'title':slug.split('/')[1],'code_file':'run.py','language':'python','kernel_type':'script',
          'is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':False,'dataset_sources':[],
          'kernel_sources':jobs,'competition_sources':[]}
    (a.out/'run.py').write_text(code,encoding='utf-8');(a.out/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
    (a.out/'prepared.json').write_text(json.dumps({'code_sha256':hashlib.sha256(code.encode()).hexdigest(),
        'metadata_sha256':sha(a.out/'kernel-metadata.json'),'source_receipt':str(receipt_path.relative_to(REPO)),
        'source_receipt_sha256':sha(receipt_path),'producer_axes':proofs,
        'payload_hashes':{n:v['sha256'] for n,v in modules.items()},'spec':spec},indent=1))
    print(json.dumps({'prepared':slug,'cells':spec['cells'],'parts':len(parts),'launched':False}))


if __name__=='__main__':
    main()
