"""Refresh only unfinished jobs for closure checks; this is not a slot census."""
import json
from datetime import datetime, timezone
from pathlib import Path
from preflight_slots_fast_v1 import call
from pipeline_state import HERE

old = HERE / 'preflight_joint_progress_r5.json'
out = HERE / 'preflight_closedelta_r1.json'
assert not out.exists()
snapshot = json.loads(old.read_text())
stamp = datetime.now(timezone.utc).isoformat()
updated = []
for row in snapshot['observed']:
    if row['job'] in (
        'davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1',
        'davideferrante11/vcc-derivatives-rlab-k562-gwps-r3',
    ):
        row['returncode'], row['status'] = call(row['owner'], ['kernels', 'status', row['job']])
        row['observed_utc'] = stamp
        updated.append(row['job'])
    else:
        row['reused_observation_from'] = str(old)
snapshot.update(utc=stamp, scope='unfinished-job closure delta; NOT a fresh slot census',
                refreshed_jobs=updated, previous_snapshot=str(old))
snapshot.pop('active', None)
out.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
print(json.dumps({'out': str(out), 'refreshed_jobs': updated}))
