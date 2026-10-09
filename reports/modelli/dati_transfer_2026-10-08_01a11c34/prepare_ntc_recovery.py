"""Prepare one renamed recovery only after own-account lookup shows no saved job."""
import csv
import io
from pathlib import Path
import shutil
from cloud_campaign import call
from percorso import HERE, DATA, read, write_new, now, pin

old=read(HERE/'neural_inputs_cloud_prepared_r4.json')
job=next(j for j in old['jobs'] if j['slug']=='davideferrante11/dt-ntc-inputs-01a11c34-r4')
rc,body=call('davideferrante11',['kernels','list','--mine','--search','dt-ntc-inputs-01a11c34-r4','--csv'])
rows=list(csv.DictReader(io.StringIO(body))) if rc==0 else []
write_new(HERE/'neural_inputs_r4_failed_save_lookup_r2.json',dict(utc=now(),returncode=rc,answer=body))
if rc or not (body.startswith('ref,') or body.strip()=='Not found') or any(r.get('ref')==job['slug'] for r in rows):
    raise RuntimeError('cannot prove prior job absent; no recovery prepared')
new_slug='davideferrante11/dt-ntc-inputs-01a11c34-r5'
stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/neural_inputs_cloud_r5'/new_slug
shutil.copytree(job['stage'],stage)
meta=read(stage/'kernel-metadata.json');meta.update(id=new_slug,title=new_slug.split('/')[1])
(stage/'kernel-metadata.json').write_text(__import__('json').dumps(meta,indent=2)+'\n',encoding='utf-8')
new_job={**job,'slug':new_slug,'stage':str(stage),'code':pin(stage/'run.py'),
         'metadata':pin(stage/'kernel-metadata.json')}
prepared=HERE/'neural_inputs_cloud_prepared_r5.json'
write_new(prepared,dict(utc=now(),jobs=[new_job],recovery_of=job['slug'],
    original=pin(HERE/'neural_inputs_cloud_prepared_r4.json'),source_and_scientific_code_unchanged=True,
    cause='TLS EOF during SaveKernel, followed by own-account exact list showing no saved kernel',
    visibility='private CPU; no new data or context selection',cloud_jobs_launched=0))
authorization=read(HERE/'neural_inputs_launch_authorization_r1.json')
authorization.update(recorded_utc=now(),jobs=[new_slug],prepared=pin(prepared),
    previous=pin(HERE/'neural_inputs_launch_authorization_r1.json'),
    scope_note='same extraction requested through direct human delegation; one recovery of failed transport, no duplicate fit')
write_new(HERE/'neural_inputs_launch_authorization_r2.json',authorization)
print(new_slug+' prepared; no launch')
