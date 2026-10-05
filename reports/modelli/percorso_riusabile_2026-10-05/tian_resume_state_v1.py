"""Verify resumed Tian units using their actual bank/sample producers, no arrays downloaded."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from pipeline_state import HERE,REPO,CONFIG,command,sha
from sample_state import validate


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--previous',type=Path)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False)
    old=json.loads(a.previous.read_text())['units'] if a.previous else {}
    original=json.loads((HERE/'tian_partial_r1/state.json').read_text())
    units={'norman2019':original['units']['norman2019']}
    records=[r for r in map(json.loads,(HERE/'tian_resume_r2/launches.jsonl').read_text().splitlines())
             if r['accepted'] and r['unit']!='tian2019_ipsc']
    ipsc=[r for r in map(json.loads,(HERE/'tian_ipsc_r4/launches.jsonl').read_text().splitlines()) if r['accepted']]
    records += [{**r,'unit':'tian2019_ipsc'} for r in ipsc]
    for r in records:
        unit=r['unit'];job=r['slug']
        if old.get(unit,{}).get('samples',{}).get('state')=='remote_complete_manifest_checked':
            value=old[unit]
            for obj in (value['bank'],value['samples']):
                if sha(REPO/obj['receipt'])!=obj['receipt_sha256']:raise ValueError('previous manifest changed')
            units[unit]=value;continue
        status=command(job,['status'])
        if status['returncode'] or 'COMPLETE' not in status['text']:
            units[unit]={'state':'not_complete','status':status,'kernel':job};continue
        dest=a.out/unit
        if unit!='tian2019_ipsc':
            q=subprocess.run([sys.executable,str(HERE/'archive_completion.py'),'--job',job,'--stage',r['stage'],
                               '--out',str(dest)],capture_output=True,text=True,timeout=360)
            if q.returncode:raise RuntimeError('Tian closure failed: '+unit+' '+q.stderr[-600:])
            units[unit]=json.loads((dest/'state.json').read_text())['units'][unit]
        else:
            dest.mkdir();b=original['units'][unit]['bank']
            q=subprocess.run([sys.executable,str(HERE/'sample_state.py'),'--fetch',job,str(dest)],
                env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG['davideferante'])},
                capture_output=True,text=True,timeout=180)
            if q.returncode:raise RuntimeError('iPSC sample receipt recovery failed')
            s=validate({'parameters':{'unit':unit,'bank_receipt_sha256':b['receipt_sha256']},
                        'slug':job,'code_sha256':r['code_sha256']},json.loads(q.stdout),{'bank':b})
            s['relative_path']='samples/'+unit
            units[unit]={'bank':b,'samples':s,'trainer':{'state':'not_integrated','training_used':False}}
    (a.out/'state.json').write_text(json.dumps({'units':units,'training_ready':False},indent=1))
    print(json.dumps({u:v.get('samples',{}).get('state',v.get('state')) for u,v in units.items()}))


if __name__=='__main__':main()
