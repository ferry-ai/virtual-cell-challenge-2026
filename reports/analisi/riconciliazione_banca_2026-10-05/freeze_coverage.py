"""Restore a historical ledger by exact digest; create a new coverage snapshot."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OLD=REPO/'reports/modelli/percorso_riusabile_2026-10-05/training_coverage_r1/expected.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.run(['git',*args],cwd=REPO,capture_output=True,check=True).stdout
def main():
    original=json.loads(OLD.read_text(encoding='utf-8'))
    target=next(x for x in original['additional_sources'] if x['path'].endswith('/other_sample_launches.jsonl'))
    history=git('log','--format=%H','--',target['path']).decode().splitlines()
    recovered=None
    for commit in history:
        raw=git('show',commit+':'+target['path'])
        for mode,blob in [('git_bytes',raw),('git_lf_restored_to_crlf',raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))]:
            if sha(blob)==target['sha256']:
                recovered=(blob,commit,mode);break
        if recovered:break
    if not recovered:raise SystemExit('Historical exact digest not found; do not reconstruct or weaken pin')
    dest=HERE/'frozen';dest.mkdir(exist_ok=False)
    snapshot=dest/'other_sample_launches_original.jsonl';snapshot.write_bytes(recovered[0])
    proof={'source':target['path'],'expected_sha256':target['sha256'],'restored_sha256':sha(snapshot.read_bytes()),
      'git_commit':recovered[1],'restoration':recovered[2],'note':'recovered bytes match the original expected digest exactly; live ledger preserved unchanged',
      'live_ledger_sha256':sha((REPO/target['path']).read_bytes())}
    target['historical_path']=target['path'];target['path']=snapshot.relative_to(REPO).as_posix()
    original['previous_coverage']={'path':OLD.relative_to(REPO).as_posix(),'sha256':sha(OLD.read_bytes())}
    original['utc']=datetime.now(timezone.utc).isoformat()
    original['scope']='coverage inventory, not fit admission or current producer liveness; old frozen ledger restored under distinct path'
    output=dest/'expected_r2.json';output.write_text(json.dumps(original,indent=2),encoding='utf-8')
    proof['new_coverage_sha256']=sha(output.read_bytes())
    (dest/'restoration.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps({'coverage':output.relative_to(REPO).as_posix(),'sha256':proof['new_coverage_sha256'],'recovered_from':proof['git_commit']}))
if __name__=='__main__':main()
