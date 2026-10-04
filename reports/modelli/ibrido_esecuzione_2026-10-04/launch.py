"""Freeze and launch private CPU bank jobs, or inspect their state."""
import argparse, base64, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CONFIG = {'davideferrante11': '.kaggle-davideferrante11', 'davidmaisterx': '.kaggle', 'davideferante': '.kaggle-codex'}

def call(owner, args):
    r = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), *args],
        env={**os.environ, 'KAGGLE_CONFIG_DIR': str(Path.home()/CONFIG[owner])}, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout+r.stderr).strip()

def push(owner, slug, params, kernels=(), datasets=(), mode='bank', gpu=False):
    stage = HERE/'stages'/slug; stage.mkdir(parents=True, exist_ok=False)
    sources = {'params.json': json.dumps(params).encode()}
    source_paths = {'bank.py': HERE/'bank.py', 'preparation.py': HERE.parent/'ibrido_pseudobulk_2026-10-04/preparation.py'}
    if mode != 'bank': source_paths = {mode+'.py': HERE/(mode+'.py'), 'hybrid.py': HERE.parent/'ibrido_pseudobulk_2026-10-04/hybrid.py'}
    for name, p in source_paths.items():
        sources[name] = p.read_bytes()
    payload = {k: {'base64': base64.b64encode(v).decode(), 'sha256': hashlib.sha256(v).hexdigest()} for k,v in sources.items()}
    code = 'import base64,hashlib,json,os,runpy,sys\nfrom pathlib import Path\nos.chdir("/kaggle/working"); sys.path.insert(0,"/kaggle/working")\n'
    code += 'P='+repr(payload)+'\n'
    code += 'for name,item in P.items():\n b=base64.b64decode(item["base64"]); assert hashlib.sha256(b).hexdigest()==item["sha256"]; Path(name).write_bytes(b)\n'
    code += f'runpy.run_path("{mode}.py",run_name="__main__")\n'
    compile(code, 'run.py', 'exec'); (stage/'run.py').write_text(code, encoding='utf-8')
    meta = dict(id=owner+'/'+slug,title=slug,code_file='run.py',language='python',kernel_type='script',is_private=True,
                enable_gpu=gpu,enable_tpu=False,enable_internet=False,dataset_sources=list(datasets),kernel_sources=list(kernels),competition_sources=[])
    (stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
    rc, answer = call(owner, ['kernels','push','-p',str(stage)])
    record = dict(utc=datetime.now(timezone.utc).isoformat(),owner=owner,slug=meta['id'],returncode=rc,answer=answer,
                  accepted=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer,
                  code_sha256=hashlib.sha256(code.encode()).hexdigest(),params=params,metadata=meta)
    with (HERE/'launches.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record)+'\n')
    print(json.dumps({k:record[k] for k in ('slug','accepted','answer')}),flush=True)
    if not record['accepted']: raise RuntimeError(answer)

def cd4():
    coverage=json.loads((REPO/'reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/copertura_cd4_r2.json').read_text())
    for owner, donors in [('davideferrante11',[1,2,3]),('davidmaisterx',[4])]:
        for state in ['Rest','Stim8hr','Stim48hr']:
            units=[]; inputs=[]
            for donor in donors:
                name=f'D{donor}_{state}'; evidence=coverage['units'][name]
                receipt=json.loads((REPO/evidence['receipt']).read_text())
                units.append(dict(name=name,cells=evidence['cells'],receipt_sha256=evidence['sha256'],parts=receipt['parts']))
                inputs.extend(owner+'/'+p['job'].replace('_','-') for p in receipt['parts'])
            push(owner,f'vcc-bank-cd4-{donors[0]}-{donors[-1]}-{state.lower()}-r2',{'units':units},kernels=inputs)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cd4','status']);a=p.parse_args()
    if a.action=='cd4': cd4()
    else:
        for line in (HERE/'launches.jsonl').read_text().splitlines():
            r=json.loads(line)
            if r['accepted']: print(r['slug'],call(r['owner'],['kernels','status',r['slug']]),flush=True)
