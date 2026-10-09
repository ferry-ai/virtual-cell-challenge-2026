"""Resolve a frozen AMMI package on cloud and enter the CUDA-only runner."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from ammi_resolve_v4 import Resolver
from pie_adapter import sha256

def execute(template,expected,mode,out,private_locator_path=None):
    bootstrap_started=time.perf_counter()
    bootstrap_utc=datetime.now(timezone.utc).isoformat()
    template=Path(template)
    if sha256(template)!=expected:raise ValueError('runtime template differs')
    spec=json.loads(template.read_text())
    for name,digest in spec['code'].items():
        if sha256(Path(__file__).with_name(name))!=digest:raise ValueError('code differs before resolution')
    root=Path(spec['staging_root']).parent
    if not str(root).startswith('/kaggle/temp/') or root.exists():raise ValueError('fresh cloud scratch required')
    root.mkdir(parents=True)
    locators={}
    if private_locator_path:
        raw=json.loads(Path(private_locator_path).read_text())
        # This package is built only after the specific transfer plan is authorized.
        if raw.get('status')!='authorized' or not raw.get('authorization'):
            raise ValueError('private input authorization missing')
        locators=raw['files']
    for item in spec.pop('public_assets').values():locators[item['sha256']]=item
    resolver=Resolver(['/kaggle/input',str(template.parent/'assets')],root/'downloads',locators)
    for key in ('protocol','authorization','phase_mandate','anchor_contract','view','panel_file',
                'anchor_completion','ntc_reader','metrics'):
        spec[key]=resolver.pin(spec[key])
    spec['anchors']={k:resolver.pin(v) for k,v in spec['anchors'].items()}
    spec['features']={k:resolver.pin(v) for k,v in spec['features'].items()}
    spec['ntc_parts']=resolver.stage_ntc(spec['ntc_parts'],root/'ntc_sources')
    if spec['mode']=='production':spec['production_readout']=resolver.pin(spec['production_readout'])
    else:
        guard=spec['guard']
        for k in ('axis','review_pin','routing_basis'):guard[k]=resolver.pin(guard[k])
        for route in guard['routes']:route['truth']=resolver.pin(route['truth'])
    resolved=root/'runtime.json';write(resolved,spec)
    write(Path(out).parent/'ammi_bootstrap_timing.json',dict(
        phase='bootstrap_resolution_and_input_hashing',status='COMPLETE',
        started_utc=bootstrap_utc,finished_utc=datetime.now(timezone.utc).isoformat(),
        seconds=time.perf_counter()-bootstrap_started,template_sha256=expected,
        runtime_manifest_sha256=sha256(resolved)))
    from run_ammi_v4 import run
    run(resolved,sha256(resolved),mode,17,out,runtime_resolver=resolver)

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('template','sha256','mode','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--private-locators');a=p.parse_args()
    execute(a.template,a.sha256,a.mode,a.out,a.private_locators)
