"""Prepare a pinned KOLF bank from verified existing shards; no ingestion or launch."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
from pipeline_state import HERE, REPO, CAMPAIGN, sha


def generalize(source):
    changes={
        "rows['line_group'] = 'CD4T'":"rows['line_group'] = spec['line_group']",
        "started = time.time(); files = []; seen = set()":
            "started = time.time(); files = []; seen = set()\n    if not spec.get('line_group') or not spec.get('expected_contexts'): raise ValueError('explicit biological identity required')",
        "if f.stat().st_size != s['bytes']: raise ValueError('changed verified shard size')":
            "if f.stat().st_size != s['bytes'] or sha(f) != s['sha256']: raise ValueError('changed verified raw shard')",
        "if len(obs) != expected: raise ValueError('cell count mismatch')":
            "if len(obs) != expected: raise ValueError('cell count mismatch')\n        if not set(obs.context).issubset(spec['expected_contexts']): raise ValueError('unexpected biological context')",
        "need = N*G*28":
            "need = N*G*28\n    import shutil\n    if shutil.disk_usage(out).free < N*G*21 + (2 << 30): raise OSError('insufficient output capacity')",
        "# Each source CD4 shard belongs to exactly one biological context.":
            "# This adapter requires homogeneous shards; never pool or discard mixed contexts."
    }
    for old,new in changes.items():
        if source.count(old)!=1:
            raise ValueError('frozen bank structure differs')
        source=source.replace(old,new)
    compile(source,'bank.py','exec')
    return source


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    receipt_path=REPO/'reports/sorgenti/ingestione_completa_2026-10-03/kolf/esito_verifica_r1/source_complete.json'
    receipt=json.loads(receipt_path.read_text())
    if not receipt['ok'] or not all(receipt['verdict'].values()) or receipt['units']['kolf_pan_genome']['cells']!=2659209:
        raise ValueError('KOLF source not reconciled')
    parent=next(r for r in map(json.loads,(CAMPAIGN/'launches.jsonl').read_text().splitlines())
                if r['slug']=='davideferrante11/vcc-bank-cd4-1-3-rest-r2' and r['accepted'])
    source=(CAMPAIGN/'stages'/parent['slug'].split('/')[1]/'run.py').read_text(encoding='utf-8')
    if hashlib.sha256(source.encode()).hexdigest()!=parent['code_sha256']:
        raise ValueError('parent launch changed')
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
    frozen=ast.literal_eval(node.value);files={}
    for name in ('bank.py','preparation.py'):
        raw=base64.b64decode(frozen[name]['base64'])
        if hashlib.sha256(raw).hexdigest()!=frozen[name]['sha256']:
            raise ValueError('frozen module changed')
        files[name]=raw
    files['bank.py']=generalize(files['bank.py'].decode()).encode()
    spec={'name':'kolf_pan_genome','line_group':'iPSC','expected_contexts':['KOLF2.1J iPSC'],
          'cells':2659209,'receipt_sha256':sha(receipt_path),'parts':receipt['parts']}
    files['params.json']=json.dumps({'units':[spec]}).encode()
    payload={n:{'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()}
    code='import os,sys,base64,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
    code+='for n,v in P.items():\n b=base64.b64decode(v["data"]);assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
    code+='runpy.run_path("bank.py",run_name="__main__")\n'
    slug='davideferrante11/vcc-bank-kolf-pan-r1'
    metadata={'id':slug,'title':slug.split('/')[1],'code_file':'run.py','language':'python','kernel_type':'script',
        'is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':False,'dataset_sources':[],
        'kernel_sources':['davideferrante11/'+r['job'].replace('_','-') for r in receipt['parts']], 'competition_sources':[]}
    (out/'run.py').write_text(code,encoding='utf-8');(out/'kernel-metadata.json').write_text(json.dumps(metadata,indent=1))
    (out/'prepared.json').write_text(json.dumps({'parent_code_sha256':parent['code_sha256'],'source_receipt':str(receipt_path.relative_to(REPO)),
        'source_receipt_sha256':sha(receipt_path),'code_sha256':hashlib.sha256(code.encode()).hexdigest(),
        'metadata_sha256':sha(out/'kernel-metadata.json'),'payload_hashes':{n:v['sha256'] for n,v in payload.items()},'spec':spec},indent=1))
    print(json.dumps({'prepared':slug,'cells':spec['cells'],'raw_parts':len(spec['parts']),'launched':False}))


if __name__=='__main__':
    main()
