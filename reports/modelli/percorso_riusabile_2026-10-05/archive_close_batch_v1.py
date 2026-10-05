"""Recover newly complete immutable outputs, metadata only, never matrices."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pipeline_state import HERE


def main():
    out = HERE/'archive_completion_batch_r1'; out.mkdir(exist_ok=False)
    observed = {}
    for filename in ('archive_jobs_progress_r3.json','remaining_archives_progress_r2.json'):
        observed.update(json.loads((HERE/filename).read_text())['jobs'])
    records = []
    for filename in ('archive_launches_r2.jsonl','remaining_archives_r1/launches.jsonl'):
        records += [r for r in map(json.loads,(HERE/filename).read_text().splitlines()) if r['accepted']]
    def close(r):
        job = r['slug']
        if 'COMPLETE' not in observed[job]['status'] or 'hepg2' in job: return {'job': job, 'state': 'not_new_complete'}
        dest = out/job.split('/')[1]
        p = subprocess.run([sys.executable,str(HERE/'archive_completion.py'),'--job',job,
             '--stage',r['stage'],'--out',str(dest)],capture_output=True,encoding='utf-8',errors='replace',timeout=360)
        return {'job': job, 'state': 'verified' if not p.returncode else 'verification_error',
                'output': (p.stdout+p.stderr)[-1000:], 'receipt': str(dest/'state.json')}
    with ThreadPoolExecutor(3) as pool: result=list(pool.map(close,records))
    (out/'state.json').write_text(json.dumps(result,indent=1))
    print(json.dumps(result))


if __name__ == '__main__': main()
