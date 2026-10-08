"""Refresh named unknown states; keep unidentifiable records reserved as active."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi


def main(source, destination, owner):
    if destination.exists():
        raise FileExistsError(destination)
    result = json.loads(source.read_text())
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(result['utc'])).total_seconds()
    if not 0 <= age <= 900:
        raise ValueError('inventory stale')
    api = KaggleApi()
    api.authenticate()
    changed = []
    for row in result['observed']:
        if row['owner'] != owner or not row.get('job') or not row['returncode']:
            continue
        try:
            row.update(status=str(api.kernels_status(row['job']).status).split('.')[-1], returncode=0)
            row.pop('error_type', None)
        except Exception as exc:
            row.update(error_type=type(exc).__name__)
        changed.append(row.copy())
    result['active'] = {account: sum(row.get('reserved_slots', 1) for row in result['observed']
        if row['owner'] == account and (row['returncode'] or row['status'] not in ('COMPLETE','ERROR','CANCELLED')))
        for account in result['active']}
    result['unknown_reserved_as_active'] = [r for r in result['observed'] if r['returncode']]
    result['refreshed_utc'] = datetime.now(timezone.utc).isoformat()
    result['refreshed_owner'] = owner
    result['source_snapshot'] = str(source)
    with destination.open('x') as stream:
        json.dump(result, stream, indent=1)
    print(json.dumps(dict(changed=changed,active=result['active'])))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--owner',required=True)
    a=p.parse_args()
    main(a.source,a.out,a.owner)
