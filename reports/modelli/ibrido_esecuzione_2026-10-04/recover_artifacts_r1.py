"""Stream completed private artifacts; hash-check bank files, reuse verified local copies."""
import hashlib, json, os, sys, time
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/ferra/vcc2026-data/processed/ibrido_esecuzione_2026-10-04')
os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/'.kaggle')
from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''): h.update(b)
    return h.hexdigest()

def files(api, slug):
    token=None
    while True:
        req=ApiListKernelSessionOutputRequest();req.user_name='davidmaisterx';req.kernel_slug=slug;req.page_size=100
        if token:req.page_token=token
        with api.build_kaggle_client() as client:
            response=client.kernels.kernels_api_client.list_kernel_session_output(req)
        yield from response.files or []
        token=response.next_page_token
        if not token:break

def fetch(api,slug,dest,expected=None):
    dest.mkdir(parents=True,exist_ok=True);receipt_path=dest/'recovery.json'
    old=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'files':{}}
    result={'source':'davidmaisterx/'+slug,'files':{},'complete':False}
    for item in files(api,slug):
        name=item.file_name
        if expected is not None:
            if name not in expected:continue
            wanted=expected[name]
        else:
            if not (name.endswith('/model.pt') or name.endswith('/curve.csv') or name.endswith('/exposure.csv') or name.endswith('/complete.json') or name in ('training_done.json','training_started.json')):continue
            wanted=old['files'].get(name)
        path=dest/name
        if not path.resolve().is_relative_to(dest.resolve()):raise ValueError('unsafe output path')
        if path.exists():
            if wanted and path.stat().st_size==wanted['bytes'] and digest(path)==wanted['sha256']:
                result['files'][name]=wanted;continue
            raise ValueError('unverified existing artifact: '+str(path))
        path.parent.mkdir(parents=True,exist_ok=True);partial=path.with_name(path.name+'.partial')
        if partial.exists():raise ValueError('partial download retained; inspect before retry: '+str(partial))
        h=hashlib.sha256();size=0
        with requests.get(item.url,stream=True,timeout=(30,180)) as response:
            response.raise_for_status()
            with partial.open('xb') as out:
                for chunk in response.iter_content(8<<20):
                    if chunk:out.write(chunk);h.update(chunk);size+=len(chunk)
        record={'bytes':size,'sha256':h.hexdigest()}
        if wanted and any(record[k]!=wanted[k] for k in ('bytes','sha256')):raise ValueError('artifact hash mismatch: '+name)
        partial.rename(path);result['files'][name]=record
        receipt_path.write_text(json.dumps(result,indent=1))
        print(json.dumps({'job':slug,'file':name,'bytes':size,'verified_against_bank_manifest':expected is not None}),flush=True)
    if expected is not None and set(result['files'])!=set(expected):raise ValueError('missing bank files')
    if expected is None and sum(n.endswith('/model.pt') for n in result['files'])!=6:raise ValueError('six models required')
    result['complete']=True;receipt_path.write_text(json.dumps(result,indent=1));return result

def main():
    api=KaggleApi();api.authenticate();summary={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'banks':{},'trainings':{}}
    coverage=json.loads((HERE.parents[1]/'generatore_e_banchi/ripresa_banco_v2_2026-10-04/copertura_cd4_r2.json').read_text())
    for state in ('Rest','Stim8hr','Stim48hr'):
        unit='D4_'+state;local=HERE/('bank_d4'+state.lower()+'_completion')/'bank'/unit/'complete.json'
        evidence=json.loads(local.read_text())
        if not evidence['complete'] or evidence['cells_in']!=coverage['units'][unit]['cells']:raise ValueError('coverage mismatch '+unit)
        expected={'bank/'+unit+'/'+name:info for name,info in evidence['files'].items()}
        result=fetch(api,'vcc-bank-cd4-4-4-'+state.lower()+'-r2',ROOT/'recovered'/unit,expected)
        import pandas as pd
        rows=pd.read_csv(ROOT/'recovered'/unit/'bank'/unit/'rows.csv')
        if len(rows)!=evidence['rows'] or int(rows.n.sum())!=evidence['cells_used']:raise ValueError('row totals mismatch')
        if set(rows.donor_or_clone.astype(str))!={'D4'}:raise ValueError('donor mismatch')
        summary['banks'][unit]={'cells':evidence['cells_used'],'rows':len(rows),'files':result['files'],'verified':True}
        (HERE/'recovery_20261005_r1.json').write_text(json.dumps(summary,indent=1))
    for held in ('h1','hepg2','jurkat'):
        summary['trainings'][held]=fetch(api,'vcc-hybrid-train-'+held+'-r1',ROOT/'recovered'/('training_'+held))
        (HERE/'recovery_20261005_r1.json').write_text(json.dumps(summary,indent=1))
    print('RECOVERY COMPLETE',flush=True)

if __name__=='__main__':main()
