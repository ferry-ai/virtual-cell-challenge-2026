"""Push one frozen prepared package only after fresh preflight and ready private inputs."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[3];S=R/'reports/modelli/percorso_riusabile_2026-10-05'
sys.path.insert(0,str(S));from preflight_slots_fast_v1 import call
def main():
    ready=Path(sys.argv[1]);out=Path(sys.argv[2]);pre=Path(sys.argv[3]);out.mkdir(exist_ok=False)
    p=json.loads(pre.read_text());assert (datetime.now(timezone.utc)-datetime.fromisoformat(p['utc'])).total_seconds()<900
    assert p['active'].get('davideferrante11',0)<5
    r=json.loads(ready.read_text());pkg=Path(r['package']);metadata=r['metadata'];job=metadata['id']
    assert hashlib.sha256((pkg/'run.py').read_bytes()).hexdigest()==r['code_sha256']
    for ref in metadata['dataset_sources']:
        rc,body=call('davideferrante11',['datasets','status',ref]);(out/(ref.split('/')[-1]+'_status.json')).write_text(json.dumps({'returncode':rc,'text':body}))
        if rc or 'ready' not in body.lower():raise SystemExit('input readiness not confirmed: '+ref)
    (out/'intent.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'slug':job,'code_sha256':r['code_sha256']}))
    rc,body=call('davideferrante11',['kernels','push','-p',str(pkg)])
    (out/'launch.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'slug':job,'accepted':rc==0,'returncode':rc,'text':body,'code_sha256':r['code_sha256'],'params_sha256':r['params_sha256'],'supersedes_failed':r.get('supersedes_failed')},indent=2))
    print(json.dumps({'accepted':rc==0,'slug':job}))
    if rc:raise SystemExit('push not confirmed; inspect receipt, no blind retry')
if __name__=='__main__':main()
