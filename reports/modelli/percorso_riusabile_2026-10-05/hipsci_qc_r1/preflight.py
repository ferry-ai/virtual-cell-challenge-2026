"""Bounded parallel metadata preflight; no cloud push or local data processing."""
import csv,io,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from pipeline_state import CONFIG


def call(owner,args):
    env={k:v for k,v in os.environ.items() if k not in
         ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    r=subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')),*args],env=env,
                     capture_output=True,text=True,timeout=90)
    return r.returncode,(r.stdout+r.stderr).strip()


def listing(owner):
    rc,body=call(owner,['kernels','list','--mine','--page-size','20','--sort-by','dateRun','--csv'])
    if rc:raise RuntimeError('account listing failed: '+owner)
    return owner,[r['ref'] for r in csv.DictReader(io.StringIO(body)) if r.get('ref')]


def status(pair):
    owner,job=pair;rc,body=call(owner,['kernels','status',job])
    return {'owner':owner,'job':job,'returncode':rc,'status':body}


def main():
    out=Path(sys.argv[1])
    if out.exists():raise ValueError('new snapshot required')
    with ThreadPoolExecutor(3) as pool:listed=list(pool.map(listing,CONFIG))
    pairs={(owner,ref) for owner,refs in listed for ref in refs}
    terminal={'davideferrante11/vcc-derivatives-rlab-k562-gwps-r3',
              'davideferrante11/vcc-generate-t28-frozen-bank-r1',
              'davideferante/vcc-derivatives-hipsci-targeted19-r1',
              'davideferante/vcc-effects-hipsci-targeted19-countsum-r1'}
    pairs={p for p in pairs if p[1] not in terminal}
    with ThreadPoolExecutor(5) as pool:observed=list(pool.map(status,sorted(pairs)))
    active=Counter(r['owner'] for r in observed if r['returncode'] or
                   any(s in r['status'] for s in ('RUNNING','QUEUED')))
    result={'utc':datetime.now(timezone.utc).isoformat(),'scope':'20 latest dateRun per account; known terminal bank/candidate omitted',
            'known_terminal_not_polled':sorted(terminal),
            'observed':observed,'active':dict(active),'quota_remaining':'not exposed by this check'}
    out.open('x').write(json.dumps(result,indent=1))
    print(json.dumps({'active':dict(active),'queries':len(observed)}))


if __name__=='__main__':main()
