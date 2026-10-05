"""Bounded status/log inspection; never downloads matrices or stops cloud jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from pipeline_state import CONFIG


def inspect(record):
    job = record['slug']; owner = job.split('/')[0]
    env = {**os.environ, 'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])}
    cli = str(Path(sys.executable).with_name('kaggle.exe'))
    r = subprocess.run([cli,'kernels','status',job], env=env, capture_output=True,
                       encoding='utf-8',errors='replace',timeout=45)
    result = {'status':r.stdout.strip(),'returncode':r.returncode}
    try:
        r = subprocess.run([cli,'kernels','logs',job,'--follow'],env=env,capture_output=True,
                           encoding='utf-8',errors='replace',timeout=15)
        raw = r.stdout
    except subprocess.TimeoutExpired as e:
        raw = e.stdout or b''
        if isinstance(raw, bytes): raw = raw.decode('utf-8',errors='replace')
    # Retain scientific/environment JSON only, no provider URLs or authentication data.
    events = []
    for line in raw.splitlines():
        start = line.find('{')
        if start < 0: continue
        try: item = json.loads(line[start:])
        except ValueError: continue
        if isinstance(item,dict) and ('unit' in item or 'ram_available' in item): events.append(item)
    result['events'] = events[-4:]
    return job, result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--launches',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    if a.out.exists(): raise ValueError('new snapshot required')
    records = [r for r in map(json.loads,a.launches.read_text().splitlines()) if r['accepted']]
    with ThreadPoolExecutor(5) as pool: jobs = dict(pool.map(inspect,records))
    a.out.write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'jobs':jobs},indent=1))
    print(json.dumps({job:{'status':r['status'],'events':len(r['events'])} for job,r in jobs.items()}))
