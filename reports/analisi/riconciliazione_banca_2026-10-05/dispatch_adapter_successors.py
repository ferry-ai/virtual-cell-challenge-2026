"""Dispatch frozen adapter successors with owner-aware slots and launch intents."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[3];S=R/'reports/modelli/percorso_riusabile_2026-10-05'
sys.path.insert(0,str(S));from preflight_slots_fast_v1 import call
def main():
 pre=Path(sys.argv[1]);root=S/'adapter_successors_r1';p=json.loads(pre.read_text())
 assert (datetime.now(timezone.utc)-datetime.fromisoformat(p['utc'])).total_seconds()<900
 active=dict(p['active']);launched=[]
 for r in json.loads((root/'ready.json').read_text()):
  pkg=Path(r['package']);out=pkg/'dispatch';owner=r['owner']
  if out.exists():continue
  if active.get(owner,0)>=5:continue
  assert hashlib.sha256((pkg/'run.py').read_bytes()).hexdigest()==r['code_sha256']
  assert hashlib.sha256((pkg/'params.json').read_bytes()).hexdigest()==r['params_sha256']
  out.mkdir()
  for ref in r['metadata']['dataset_sources']:
   rc,body=call(owner,['datasets','status',ref]);(out/(ref.split('/')[-1]+'_status.json')).write_text(json.dumps({'returncode':rc,'text':body}))
   assert rc==0 and 'ready' in body.lower(),ref
  intent={'utc':datetime.now(timezone.utc).isoformat(),'slug':r['slug'],'owner':owner,'code_sha256':r['code_sha256']}
  (out/'intent.json').write_text(json.dumps(intent,indent=2))
  rc,body=call(owner,['kernels','push','-p',str(pkg)])
  receipt={**intent,'accepted':rc==0,'returncode':rc,'text':body,'params_sha256':r['params_sha256'],'production_only':True}
  (out/'launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
  if rc:raise SystemExit('unconfirmed push; inspect intent before any retry')
  active[owner]=active.get(owner,0)+1;launched.append(r['slug'])
 print(json.dumps({'launched':launched,'remaining_unlaunched':[r['slug'] for r in json.loads((root/'ready.json').read_text()) if not (Path(r['package'])/'dispatch').exists()]}))
if __name__=='__main__':main()
