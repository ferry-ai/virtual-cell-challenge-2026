"""Read account job states before dispatch; never launch or expose provider bodies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'reports/modelli/dati_transfer_2026-10-08_01a11c34'))
from cloud_campaign import call

OWNERS = ('davideferrante11', 'davidmaisterx', 'davideferante')


def snapshot(out):
    if out.exists():
        raise FileExistsError(out)
    refs = []
    def listing(owner):
        rc, body = call(owner, ['kernels', 'list', '--mine', '--page-size', '50', '--sort-by', 'dateRun', '--csv'])
        if rc:
            raise RuntimeError('account listing failed: ' + owner)
        rows = list(csv.DictReader(io.StringIO(body)))
        return [(owner, row['ref']) for row in rows if row.get('ref')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(listing, OWNERS):
            refs.extend(result)
    def status(pair):
        owner, slug = pair
        rc, body = call(owner, ['kernels', 'status', slug])
        state = next((s for s in ('RUNNING', 'QUEUED', 'COMPLETE', 'ERROR', 'CANCELLED')
                      if 'KernelWorkerStatus.' + s in body), 'UNKNOWN')
        return dict(owner=owner, job=slug, returncode=rc, status=state)
    with ThreadPoolExecutor(max_workers=6) as pool:
        observed = list(pool.map(status, refs))
    if any(r['returncode'] or r['status'] == 'UNKNOWN' for r in observed):
        raise RuntimeError('incomplete job status inventory; no launch permitted')
    active = {o: sum(r['owner'] == o and r['status'] in ('RUNNING', 'QUEUED')
                     for r in observed) for o in OWNERS}
    dispatcher = Path('G:/Il mio Drive/vcc2026/runs/jobs/dispatcher.log')
    colab = dict(path=str(dispatcher), accessible=dispatcher.is_file(), live_verified=False)
    if dispatcher.is_file():
        colab['file_mtime_utc'] = datetime.fromtimestamp(dispatcher.stat().st_mtime, timezone.utc).isoformat()
    result = dict(utc=datetime.now(timezone.utc).isoformat(),
                  scope='50 most recently run kernels per configured account',
                  observed=observed, active=active, slot_limit_per_account=5,
                  slot_policy='existing campaign ceiling; keep one slot free',
                  quota_remaining='not exposed by this check', colab=colab,
                  destination_constraint='df11 plus C-iPSC/davidmaisterx and J-iPSC/davideferante; explicit private-transfer approvals in MODELLI-ESTERNI chat')
    with out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=1)
    print(json.dumps({k:result[k] for k in ('utc','active','colab','quota_remaining')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    snapshot(p.parse_args().out)
