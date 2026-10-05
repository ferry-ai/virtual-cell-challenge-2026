"""Use a verified private sample-input dataset instead of the unmountable failed notebook."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from launch_samples_r2 import preflight
from launch_samples import call
from archive_partition_v1 import pack


def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);a=p.parse_args()
    out=HERE/'tian_resume_r2';out.mkdir(exist_ok=True)
    ref=json.loads((HERE/'tian_rehouse_r1.json').read_text())['dataset']
    rc,status=call('davideferante',['datasets','status',ref])
    if rc or status.strip()!='ready':raise ValueError('private sample input not ready')
    rc,status=call('davideferante',['kernels','status','davideferante/vcc-derivatives-tian2019-ipsc-resume-r2'])
    if rc or 'ERROR' not in status:raise ValueError('original source-rejected attempt not terminated')
    plan=[]
    for old in json.loads((HERE/'tian_resume_r1/plan.json').read_text())['jobs']:
        unit=old['unit']; src=Path(old['stage']);dest=out/unit
        if not dest.exists():
            dest.mkdir()
            files={n:(src/n).read_bytes() for n in ('bank.py','preparation.py','materialize_samples.py','params.json','raw_files.json','raw_complete.json')}
            runtime=(src/'archive_runtime.py').read_text()
            runtime=runtime.replace("if x.parent.name==spec['name'] and x.parent.parent.name=='bank'\n               and sha(x)==expected['receipt_sha256']", "if sha(x)==expected['receipt_sha256']")
            if "x.parent.name==spec['name']" in runtime:raise ValueError('runtime patch failed')
            files['archive_runtime.py']=runtime.encode()
            for name,raw in files.items():(dest/name).write_bytes(raw)
            code=pack(files);(dest/'run.py').write_text(code,encoding='utf-8',newline='\n')
            meta=json.loads((src/'kernel-metadata.json').read_text())
            slug=meta['id'].split('/')[1].replace('-r2','-r3')
            meta.update(id='davideferante/'+slug,title=slug,kernel_sources=[])
            if old['reused_bank']:meta['dataset_sources'].append(ref)
            (dest/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
            proof={**old,'slug':meta['id'],'stage':str(dest.resolve()),'code_sha256':sha(dest/'run.py'),
                  'private_sample_input':ref if old['reused_bank'] else None}
            (dest/'prepared.json').write_text(json.dumps(proof,indent=1))
        plan.append(json.loads((dest/'prepared.json').read_text()))
    if not (out/'plan.json').exists():(out/'plan.json').write_text(json.dumps(plan,indent=1))
    ledger=out/'launches.jsonl'; prior=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
    if any(not r['accepted'] for r in prior):raise ValueError('inspect rejected push before retry')
    accepted={r['slug'] for r in prior};snap=out/('preflight_'+a.snapshot+'.json');active=preflight(snap)
    observed={r['job'] for r in json.loads(snap.read_text())['observed']}; new=[]
    for r in plan:
        if r['slug'] in accepted:continue
        if r['slug'] in observed:raise ValueError('unresolved remote identity')
        if active.get('davideferante',0)>=5:break
        rc,answer=call('davideferante',['kernels','push','-p',r['stage']])
        ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
        with ledger.open('a') as f:f.write(json.dumps({**r,'utc':datetime.now(timezone.utc).isoformat(),'accepted':ok,'answer':answer})+'\n')
        if not ok:raise RuntimeError('inspect rejected push')
        new.append(r['slug']);active['davideferante']=active.get('davideferante',0)+1
    print(json.dumps({'accepted':new,'norman':'reused, no new job'}))


if __name__=='__main__':main()
