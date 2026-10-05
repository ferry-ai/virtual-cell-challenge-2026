"""Distinguish uncommitted drafts from background runs, without bypassing quota.

A version-zero draft with a 404 session status has no saved background execution.
Interactive occupancy is not asserted; Kaggle still admits/refuses the new job.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import launch_samples as original

base_preflight = original.preflight


def preflight(out):
    raw = out.with_name(out.stem+'_raw.json')
    if raw.exists():
        raise ValueError('use a new raw preflight receipt')
    active = base_preflight(raw)
    record = json.loads(raw.read_text())
    drafts = []
    for item in record['observed']:
        if not item['returncode'] or '404' not in item['status']:
            continue
        owner, slug = item['job'].split('/')
        script = '''import sys,json
from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest
a=KaggleApi();a.authenticate();q=ApiGetKernelRequest();q.user_name=sys.argv[1];q.kernel_slug=sys.argv[2]
with a.build_kaggle_client() as c:r=c.kernels.kernels_api_client.get_kernel(q)
print(json.dumps({'ref':r.metadata.ref,'version':r.metadata.current_version_number,'last_run':str(r.metadata.last_run_time)}))
'''
        result = subprocess.run([sys.executable,'-c',script,owner,slug],
            env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/original.state.CONFIG[owner])},
            capture_output=True,encoding='utf-8',errors='replace',timeout=30)
        if result.returncode:
            continue
        meta = json.loads(result.stdout)
        if meta['ref']==item['job'] and meta['version']==0:
            active[owner] -= 1
            drafts.append(meta)
    record['uncommitted_drafts'] = drafts
    record['active_committed_or_unknown'] = dict(active)
    record['interactive_capacity'] = 'not asserted; provider quota enforcement remains authoritative'
    out.write_text(json.dumps(record,indent=1))
    return active


if __name__=='__main__':
    original.preflight=preflight
    original.main()
