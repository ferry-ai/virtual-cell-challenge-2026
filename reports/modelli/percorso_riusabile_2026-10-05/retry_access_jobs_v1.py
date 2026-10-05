"""Two targeted retries: pre-runtime CD4 failure and missing mounted axis only."""
import ast,base64,hashlib,json,shutil,sys
from datetime import datetime,timezone
from pipeline_state import HERE,sha
from preflight_slots_fast_v1 import call

def main():
    prepath=HERE/sys.argv[1];pre=json.loads(prepath.read_text())
    if (datetime.now(timezone.utc)-datetime.fromisoformat(pre['utc'])).total_seconds()>900:raise ValueError('stale census')
    active=dict(pre['active'])
    # Account for the accepted KOLFstrong launch after this census.
    strong=HERE/'sourcefits_launch_r1/vcc-effects-kolf-strong-r4.json'
    if strong.exists() and json.loads(strong.read_text()).get('accepted'):active['davideferrante11']=active.get('davideferrante11',0)+1
    configs=[('cd4_joint_launch_r1','vcc-effects-cd4-stim8hr-joint-r5','vcc-effects-cd4-stim8hr-joint-r5-retry1','davideferrante11','ERROR'),('sourcefits_launch_r1','vcc-effects-kolf-pan-genome-r4','vcc-effects-kolf-pan-genome-r4-access1','davidmaisterx','COMPLETE')]
    for folder,old,new,owner,expected in configs:
        dest=HERE/folder;ledger=dest/(new+'.json')
        if ledger.exists():continue
        previous=json.loads((dest/(old+'.json')).read_text())
        rc,status=call(owner,['kernels','status',previous['slug']])
        if rc or expected not in status:raise ValueError('original job not in verified failed state')
        if active.get(owner,0)>=5:raise ValueError('account full')
        if folder=='cd4_joint_launch_r1':
            proof=json.loads((HERE/'cd4_joint_status_r1/verification.json').read_text())
            r=next(r for r in proof['jobs'] if r['job']==previous['slug'])
            assert not r.get('scientific_status') and not r.get('resources') and r['saved_code_matches']
        else:
            r=json.loads((HERE/'sourcefits_status_r6/davidmaisterx__vcc-effects-kolf-pan-genome-r4/job_status.json').read_text())[0]
            assert r['status']=='blocked' and r['error']=='gene_names.csv under vcc-ingest-code-cd4-r1: found 0'
        source_stage=__import__('pathlib').Path(previous['stage']);stage=dest/new;stage.mkdir(exist_ok=False)
        source=(source_stage/'run.py').read_text(encoding='utf-8');assert sha(source_stage/'run.py')==previous['code_sha256']
        params=json.loads((source_stage/'params.json').read_text());meta=json.loads((source_stage/'kernel-metadata.json').read_text());meta['id']=owner+'/'+new;meta['title']=new
        if folder=='sourcefits_launch_r1':
            known=json.loads((dest/'vcc-effects-k562-essential-r4/params.json').read_text())['axis']
            assert known['dataset']=='davidmaisterx/vcc-ingest-code-cd4-r1' and known['sha256']==params['axis']['sha256'] and known['bytes']==params['axis']['bytes']
            params['axis']['dataset']=known['dataset'];meta['dataset_sources']=[known['dataset']]
            tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets));payload=ast.literal_eval(node.value)
            body=json.dumps(params).encode();payload['params.json']={'base64':base64.b64encode(body).decode(),'sha256':hashlib.sha256(body).hexdigest()}
            lines=source.splitlines(keepends=True);source=''.join(lines[:node.lineno-1])+'P = '+repr(payload)+'\n'+''.join(lines[node.end_lineno:])
        (stage/'run.py').write_text(source,encoding='utf-8');(stage/'params.json').write_text(json.dumps(params),encoding='utf-8');(stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
        receipt={**{k:v for k,v in previous.items() if k not in ('answer','remote_status','remote_status_returncode','returncode')},'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'owner':owner,'stage':str(stage),'code_sha256':sha(stage/'run.py'),'params_sha256':sha(stage/'params.json'),'supersedes_failed':previous['slug'],'retry_reason':'pre-runtime failure; no scientific output or resource log' if folder=='cd4_joint_launch_r1' else 'axis mount inaccessible: bind same-hash axis from verified consumer-owned dataset','preflight_sha256':sha(prepath),'accepted':False,'state':'intent','full_training':False}
        ledger.open('x').write(json.dumps(receipt,indent=1))
        rc,answer=call(owner,['kernels','push','-p',str(stage)]);receipt.update(returncode=rc,answer=answer,accepted=rc==0 and 'successfully pushed' in answer,state='push_returned')
        if receipt['accepted']:
            rc,status=call(owner,['kernels','status',meta['id']]);receipt.update(remote_status=status,remote_status_returncode=rc);active[owner]=active.get(owner,0)+1
        ledger.write_text(json.dumps(receipt,indent=1));print(json.dumps({k:receipt.get(k) for k in ('slug','accepted','remote_status')}),flush=True)
        if not receipt['accepted']:raise RuntimeError('retry push rejected; inspect receipt before retry')
if __name__=='__main__':main()
