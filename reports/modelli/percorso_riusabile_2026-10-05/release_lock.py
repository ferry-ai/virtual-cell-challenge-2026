"""Pin an explicit bank release; never fall back to legacy mounts or 'latest'."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from pipeline_state import REPO,sha


def resolve(lock_path, expected_lock_sha256, unit, kind, mounted_root):
    if sha(lock_path)!=expected_lock_sha256:
        raise ValueError('release lock changed')
    lock=json.loads(Path(lock_path).read_text())
    item=lock['units'][unit][kind]
    if item['state']!='remote_complete_manifest_checked':
        raise ValueError('release artifact pending: no legacy fallback')
    root=Path(mounted_root).resolve()
    # The caller supplies one explicit mount, not a search across Kaggle inputs.
    receipt=root/'complete.json'
    if sha(receipt)!=item['receipt_sha256']:
        raise ValueError('mounted artifact is not the pinned release')
    return root


def main():
    p=argparse.ArgumentParser();p.add_argument('--banks',type=Path,required=True)
    p.add_argument('--samples',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();banks=json.loads(a.banks.read_text());samples=json.loads(a.samples.read_text())
    units={}
    for unit,info in banks['units'].items():
        raw=info['raw']
        if sha(REPO/raw['receipt'])!=raw['sha256']:
            raise ValueError('raw ingestion receipt changed')
        entry={'raw':raw,'derivation_key':info['derivation_key'],'bank':info['bank'],
               'samples':samples['units'].get(unit,{'state':'pending'})}
        for kind in ('bank','samples'):
            item=entry[kind]
            if item['state']=='remote_complete_manifest_checked':
                if sha(REPO/item['receipt'])!=item['receipt_sha256'] or not item['saved_version'].get('version_ref'):
                    raise ValueError('unverified persisted artifact')
        units[unit]=entry
    result={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'CD4 ingestion and donor-bank branch; NOT the complete training corpus',
        'training_ready':False,'fallback_to_legacy':False,
        'sources':[{'path':str(f.resolve().relative_to(REPO)).replace('\\','/'),'sha256':sha(f)} for f in (a.banks,a.samples)],
        'legacy_classification':{'davideferrante11/rlead-bench-cube-r2':
            'aggregate pilot input only; not a replacement for the donor bank'},
        'other_sources':'Unreconciled historical datasets require explicit role, provenance and version before inclusion; no age-based exclusion.',
        'units':units}
    with a.out.open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(result,indent=1)+'\n')
    print(json.dumps({'path':str(a.out),'sha256':sha(a.out),'units':len(units),'training_ready':False}))


if __name__=='__main__':
    main()
