"""Preflight and launch an immutable prepared private CPU bank, without duplicates."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from launch_samples_r2 import preflight
from launch_samples import call
from pipeline_state import sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    frozen=json.loads((a.stage/'prepared.json').read_text());meta=json.loads((a.stage/'kernel-metadata.json').read_text())
    if sha(a.stage/'kernel-metadata.json')!=frozen['metadata_sha256'] or hashlib.sha256((a.stage/'run.py').read_text(encoding='utf-8').encode()).hexdigest()!=frozen['code_sha256']:
        raise ValueError('prepared inputs changed')
    owner=meta['id'].split('/')[0];active=preflight(a.out/'preflight.json')
    observed=json.loads((a.out/'preflight.json').read_text())['observed']
    if any(r['job']==meta['id'] for r in observed) or active[owner]>=5:
        raise ValueError('existing bank or no CPU slot')
    if not meta['is_private'] or meta['enable_gpu']:
        raise ValueError('expected private CPU bank')
    rc,answer=call(owner,['kernels','push','-p',str(a.stage)])
    ok=rc==0 and 'successfully pushed' in answer and 'not valid' not in answer
    record={'utc':datetime.now(timezone.utc).isoformat(),'slug':meta['id'],'accepted':ok,'answer':answer,
            'stage':str(a.stage),'code_sha256':frozen['code_sha256'],'spec':frozen['spec'],'metadata':meta}
    (a.out/'launch.json').write_text(json.dumps(record,indent=1));print(json.dumps({'slug':meta['id'],'accepted':ok,'answer':answer}))
    if not ok:
        raise RuntimeError('bank launch not accepted')


if __name__=='__main__':
    main()
