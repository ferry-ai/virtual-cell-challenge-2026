"""Track prepared non-CD4 banks, recovering only manifests from completed jobs."""
import argparse
import concurrent.futures
from datetime import datetime,timezone
import json
from pathlib import Path
from pipeline_state import command
from pipeline_state_r2 import isolated_receipts


def main():
    p=argparse.ArgumentParser();p.add_argument('--launches',nargs='+',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    launches=[json.loads(f.read_text()) for f in a.launches]
    if not all(r['accepted'] for r in launches) or len({r['slug'] for r in launches})!=len(launches):
        raise ValueError('ambiguous/unaccepted launches')
    statuses=list(concurrent.futures.ThreadPoolExecutor(3).map(lambda r:command(r['slug'],['status']),launches))
    units={}
    for launch,status in zip(launches,statuses):
        spec=launch['spec'];name=spec['name'];job=launch['slug']
        item={'kernel':job,'state':'not_complete','status':status,'line_group':spec['line_group'],
              'expected_cells':spec['cells'],'spec':spec,'consumer_hashes_verified':False}
        if status['returncode']==0 and 'KernelWorkerStatus.COMPLETE' in status['text']:
            receipts,files,version=isolated_receipts(job.split('/')[0],job,a.out/'receipts')
            if version['saved_source_sha256']!=launch['code_sha256'] or set(receipts)!={name}:
                raise ValueError('saved bank source/unit mismatch')
            receipt,path,digest=receipts[name]
            if (not receipt['complete'] or receipt['source_verification']!=spec['receipt_sha256']
                or receipt['cells_in']!=spec['cells'] or receipt['cells_used']+receipt['zero_depth_excluded']!=spec['cells']
                or not all('bank/'+name+'/'+n in files for n in receipt['files'])):
                raise ValueError('bank lineage/files/coverage mismatch')
            item.update(state='remote_complete_manifest_checked',receipt=path,receipt_sha256=digest,
                        saved_version=version,files=receipt['files'],cells_used=receipt['cells_used'])
        units[name]=item
    result={'utc':datetime.now(timezone.utc).isoformat(),'units':units,'extended_training_ready':False}
    (a.out/'state.json').write_text(json.dumps(result,indent=1));print(json.dumps({k:v['state'] for k,v in units.items()}))


if __name__=='__main__':
    main()
