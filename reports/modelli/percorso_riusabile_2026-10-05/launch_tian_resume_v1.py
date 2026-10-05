"""Skip complete Norman, reuse saved iPSC bank, and compute only remaining Tian units."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,sha
from launch_samples_r2 import preflight
from launch_samples import call
from archive_partition_v1 import pack,zero_population_sample


def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);a=p.parse_args()
    out=HERE/'tian_resume_r1';out.mkdir(exist_ok=True)
    parent=json.loads((HERE/'tian_partial_r1/state.json').read_text())
    stage=HERE/'fallback_tian_r2'; params=json.loads((stage/'params.json').read_text())
    plan=[]; reused=[]
    for spec in params['units']:
        unit=spec['name']; old=parent['units'].get(unit,{})
        if old.get('samples',{}).get('state')=='remote_complete_manifest_checked':
            reused.append({'unit':unit,'proof':'tian_partial_r1/state.json'});continue
        dest=out/unit
        if not dest.exists():
            dest.mkdir(); p={**params,'units':[spec]}
            if 'bank' in old:p['resume_bank']=old['bank']
            files={n:(stage/n).read_bytes() for n in ('bank.py','preparation.py','raw_files.json','raw_complete.json')}
            files['materialize_samples.py']=zero_population_sample((stage/'materialize_samples.py').read_text()).encode()
            files['archive_runtime.py']=(HERE/'tian_resume_runtime_v1.py').read_bytes();files['params.json']=json.dumps(p).encode()
            for name,raw in files.items():(dest/name).write_bytes(raw)
            code=pack(files);(dest/'run.py').write_text(code,encoding='utf-8',newline='\n')
            slug='vcc-derivatives-'+unit.replace('_','-')+'-resume-r2'
            meta={'id':'davideferante/'+slug,'title':slug,'code_file':'run.py','language':'python','kernel_type':'script',
                  'is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
                  'dataset_sources':[params['dataset']], 'kernel_sources':[parent['kernel']] if 'bank' in old else [],
                  'competition_sources':[]}
            (dest/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
            (dest/'prepared.json').write_text(json.dumps({'code_sha256':sha(dest/'run.py'),
                'unit':unit,'reused_bank':old.get('bank'),'raw_files_sha256':params['source_files_sha256']},indent=1))
        meta=json.loads((dest/'kernel-metadata.json').read_text()); proof=json.loads((dest/'prepared.json').read_text())
        plan.append({'slug':meta['id'],'stage':str(dest.resolve()),**proof})
    if not (out/'plan.json').exists():(out/'plan.json').write_text(json.dumps({'jobs':plan,'reused':reused},indent=1))
    ledger=out/'launches.jsonl'; prior=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
    if any(not r['accepted'] for r in prior):raise ValueError('inspect unresolved push')
    active=preflight(out/('preflight_'+a.snapshot+'.json'))
    observed={r['job'] for r in json.loads((out/('preflight_'+a.snapshot+'.json')).read_text())['observed']}
    accepted={r['slug'] for r in prior}; new=[]
    for r in plan:
        if r['slug'] in accepted:continue
        if r['slug'] in observed:raise ValueError('unknown prior remote execution')
        if active.get('davideferante',0)>=5:break
        if sha(Path(r['stage'])/'run.py')!=r['code_sha256']:raise ValueError('frozen stage changed')
        rc,answer=call('davideferante',['kernels','push','-p',r['stage']])
        ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
        with ledger.open('a') as f:f.write(json.dumps({**r,'utc':datetime.now(timezone.utc).isoformat(),'accepted':ok,'answer':answer})+'\n')
        if not ok:raise RuntimeError('push failed, inspect outcome')
        new.append(r['slug']);active['davideferante']=active.get('davideferante',0)+1
    print(json.dumps({'accepted':new,'reused_units':reused}))


if __name__=='__main__':main()
