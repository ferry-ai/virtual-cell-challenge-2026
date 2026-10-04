"""Launch independent private CPU consumers of verified bank/raw notebook outputs."""
import argparse
import ast
import base64
import concurrent.futures
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
from collections import Counter
import pipeline_state as state

sys.path.insert(0,str(state.CAMPAIGN))
from launch import call
HERE = Path(__file__).resolve().parent


def preflight(out):
    refs = []
    for owner in state.CONFIG:
        rc, text = call(owner,['kernels','list','--mine','--page-size','20','--sort-by','dateRun','--csv'])
        if rc:
            raise RuntimeError(text)
        refs.extend((owner,r['ref']) for r in csv.DictReader(io.StringIO(text)) if r.get('ref'))
    def status(pair):
        owner, job = pair
        rc, text = call(owner,['kernels','status',job])
        return {'owner':owner,'job':job,'status':text,'returncode':rc}
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        observed = list(pool.map(status,refs))
    # An inaccessible/draft status is not proof of an idle slot: reserve one.
    active = Counter(r['owner'] for r in observed if r['returncode'] or any(s in r['status'] for s in ('RUNNING','QUEUED')))
    record = {'utc':datetime.now(timezone.utc).isoformat(),'scope':'20 most recently run notebooks per account',
              'observed':observed,'active':dict(active),
              'placement':'Use owners of existing private inputs. Third-account input sharing is not verified; no bulk replication.',
              'runtime_resources':'CPU/RAM/disk checked on each consumer before computation; no GPU requested.'}
    out.write_text(json.dumps(record,indent=1))
    return active


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--launch',action='store_true')
    parser.add_argument('--state',type=Path,required=True);parser.add_argument('--preflight-out',type=Path,required=True)
    a = parser.parse_args()
    if a.preflight_out.exists():
        raise ValueError('use a new preflight receipt')
    active = preflight(a.preflight_out)
    corpus = json.loads(a.state.read_text())
    old_launches = [json.loads(x) for x in (state.CAMPAIGN/'launches.jsonl').read_text().splitlines()]
    log = HERE/'sample_launches.jsonl'
    accepted = {r['slug'] for r in map(json.loads,log.read_text().splitlines()) if r['accepted']} if log.exists() else set()
    for unit, info in corpus['units'].items():
        bank = info['bank']
        if bank['state'] != 'remote_complete_manifest_checked':
            continue
        source_launch = next(r for r in old_launches if r['slug']==bank['kernel'] and r['accepted'])
        owner = source_launch['owner'];slug = 'vcc-samples-cd4-'+unit.lower().replace('_','-')+'-r1'
        if owner+'/'+slug in accepted:
            continue
        if active[owner] >= 5:
            print(json.dumps({'deferred':unit,'reason':'five observed active sessions','owner':owner}),flush=True)
            continue
        spec = next(s for s in source_launch['params']['units'] if s['name']==unit)
        stage = HERE/'sample_stages'/slug
        if stage.exists():
            raise ValueError('unconfirmed existing stage; inspect before retry: '+str(stage))
        params = {'unit':unit,'spec':spec,'bank_receipt_sha256':bank['receipt_sha256'],
                  'bank_saved_version':bank['saved_version'],'max_output_bytes':18<<30,
                  'raw_parent_key':info['derivation_key']}
        original_source = (state.CAMPAIGN/'stages'/source_launch['slug'].split('/')[1]/'run.py').read_text()
        if hashlib.sha256(original_source.encode()).hexdigest() != source_launch['code_sha256']:
            raise ValueError('producer code changed')
        node = next(n for n in ast.parse(original_source).body if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
        frozen = ast.literal_eval(node.value)
        payload = {k:frozen[k] for k in ('bank.py','preparation.py')}
        for k,b in {'materialize_samples.py':(HERE/'materialize_samples.py').read_bytes(),
                    'params.json':json.dumps(params).encode()}.items():
            payload[k] = {'base64':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
        code = 'import base64,hashlib,os,runpy,sys\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
        code += 'for n,v in P.items():\n b=base64.b64decode(v["base64"]);assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
        code += 'runpy.run_path("materialize_samples.py",run_name="__main__")\n'
        compile(code,'run.py','exec')
        meta = {'id':owner+'/'+slug,'title':slug,'code_file':'run.py','language':'python',
                'kernel_type':'script','is_private':True,'enable_gpu':False,'enable_tpu':False,
                'enable_internet':False,'dataset_sources':[],
                'kernel_sources':[bank['kernel'],*info['raw']['kernel_sources']],'competition_sources':[]}
        if not a.launch:
            print(json.dumps({'prepared':unit,'inputs':meta['kernel_sources']}),flush=True)
            continue
        stage.mkdir(parents=True)
        (stage/'run.py').write_text(code,encoding='utf-8')
        (stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
        rc, answer = call(owner,['kernels','push','-p',str(stage)])
        ok = rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
        record = {'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'accepted':ok,
                  'answer':answer,'parameters':params,'metadata':meta,
                  'code_sha256':hashlib.sha256(code.encode()).hexdigest()}
        with log.open('a',encoding='utf-8') as f:
            f.write(json.dumps(record)+'\n')
        print(json.dumps({'slug':meta['id'],'accepted':ok,'answer':answer}),flush=True)
        if not ok:
            raise RuntimeError(answer)
        active[owner] += 1


if __name__ == '__main__':
    main()
