"""Recover pre-computation CLI failure; preserve every recipe and data pin."""
import json
from percorso import HERE,read,pin,write_new,now
from build_ammi_runtime_contract import payload
from prepare_neural_inputs_cloud import save_job
old=read(HERE/'production_anchors_prepared_r1.json')['jobs'][0]
members=payload(old);members['panel_anchor_worker.py']=(HERE/'panel_anchor_worker.py').read_bytes()
meta=read(old['metadata']['path'])
mounts=[dict(kind=kind,ref=r) for kind,key in [('kernel','kernel_sources'),('dataset','dataset_sources')] for r in meta[key]]
job=save_job('davideferrante11/dt-ammi-production-01a11c34-r2',members,'panel_anchor_worker.py',mounts,'production_r2',True)
prepared=HERE/'production_anchors_prepared_r2.json'
write_new(prepared,dict(utc=now(),jobs=[job],contract=pin(HERE/'panel_anchor_requests_production_r1.json'),
    recovery_of=old['slug'],cause='stage100 requires --contexts equal full original recipe A,B,C; failed before producing any anchor',
    unchanged_recipes=True,change='pass all exact recipe context keys instead of request output id'))
auth=read(HERE/'production_anchors_authorization_r1.json')
auth.update(recorded_utc=now(),jobs=[job['slug']],prepared=pin(prepared),scope_note='same authorized production anchor task; CLI recovery before any completed unit')
write_new(HERE/'production_anchors_authorization_r2.json',auth)
print(job['slug'])
