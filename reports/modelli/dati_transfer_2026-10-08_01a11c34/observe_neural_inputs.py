"""Read remote status and optionally retrieve small terminal metadata, no RNA."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from cloud_campaign import call
from percorso import HERE, now, write_new

p=argparse.ArgumentParser(__doc__);p.add_argument('--out',required=True)
p.add_argument('--slug',action='append',required=True);p.add_argument('--metadata',action='store_true')
a=p.parse_args()
def check(slug):
    owner=slug.split('/')[0];rc,state=call(owner,['kernels','status',slug])
    result=dict(utc=now(),slug=slug,returncode=rc,answer=state)
    if a.metadata and rc==0 and any(t in state for t in ('COMPLETE','ERROR')):
        folder=HERE/'neural_launches'/'terminal_metadata'/slug.split('/')[0]/(slug.split('/')[1]+'_'+a.out)
        folder.mkdir(parents=True,exist_ok=False)
        rc,body=call(owner,['kernels','output',slug,'-p',str(folder),'--file-pattern',
            r'(^|/)(failure|campaign_complete|complete|initial_resources|progress|schema_preflight|restored_complete)\.json$'])
        result.update(metadata_returncode=rc,metadata_folder=str(folder),metadata_answer=body)
    print(json.dumps(dict(slug=slug,state=state,returncode=rc)),flush=True)
    return result
with ThreadPoolExecutor(max_workers=3) as pool:result=list(pool.map(check,a.slug))
write_new(HERE/('neural_inputs_status_'+a.out+'.json'),dict(utc=now(),jobs=result))
