"""Validate that SDK blank-reference rows are not kernels, using the CLI inventory."""
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
from percorso import HERE, read, write_new, now
from cloud_campaign import call

source=read(HERE/'fast_recovery_slots_r2.json')
owners=list(source['active'])
def listing(owner):
    rc,body=call(owner,['kernels','list','--mine','--page-size','50','--sort-by','dateRun','--csv'])
    if rc:raise ValueError('named kernel listing unavailable')
    return owner,{row['ref'] for row in csv.DictReader(io.StringIO(body)) if row.get('ref')}
with ThreadPoolExecutor(max_workers=3) as pool: actual=dict(pool.map(listing,owners))
observed=[r for r in source['observed'] if r.get('job')]
for owner in owners:
    expected={r['job'] for r in observed if r['owner']==owner}
    if actual[owner]!=expected:raise ValueError('named inventory changed; a fresh status scan is needed')
if any(r['returncode'] or r['status'] not in ('COMPLETE','ERROR','CANCELLED','RUNNING','QUEUED') for r in observed):
    raise ValueError('real unknown job remains')
report=dict(source,utc=now(),observed=observed,unknown_reserved_as_active=[],
    active={o:sum(r['owner']==o and r['status'] in ('RUNNING','QUEUED') for r in observed) for o in owners},
    source_status_utc=source['utc'],blank_non_kernel_rows=len(source['observed'])-len(observed),
    correction='SDK returned empty refs; current CLI named inventory exactly matches all nonempty SDK records')
write_new(HERE/'fast_recovery_slots_r3.json',report)
print(json.dumps({k:report[k] for k in ('utc','active','blank_non_kernel_rows')}))
