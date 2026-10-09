"""Verify official NTC producer identity, frozen selection and metadata receipts."""
import hashlib
import json
import subprocess
import sys
from build_ammi_runtime_contract import payload
from percorso import HERE,read,pin,write_new,now
job=read(HERE/'official_ntc_prepared_r1.json')['jobs'][0]
remote=subprocess.run([sys.executable,str(HERE/'remote_identity.py'),'davideferrante11',job['slug']],capture_output=True,text=True,timeout=120)
if remote.returncode:raise ValueError('remote code lookup failed')
identity=json.loads(remote.stdout)
if identity!={'source_sha256':job['code']['sha256'],'version':1,'is_private':True}:raise ValueError('official producer changed')
members=payload(job);contract=json.loads(members['official_contract.json'])
root=HERE/'neural_launches/terminal_metadata/davideferrante11/dt-official-ntc-01a11c34-r1_r10'
campaign=read(root/'campaign_complete.json');parts={}
if campaign['status']!='COMPLETE' or {x['part_id'] for x in campaign['parts']}!=set(contract['ntc_expected_parts']):
    raise ValueError('official context coverage differs')
for plan in contract['plans']:
    ident=plan['part_id'];path=root/'ntc'/ident/'complete.json';doc=read(path)
    if doc['status']!='COMPLETE' or doc['part_id']!=ident or doc['plan_sha256']!=plan['plan_sha256']:raise ValueError('official plan differs')
    if doc['code']!={n:hashlib.sha256(members[n]).hexdigest() for n in ('official_ntc_worker.py','ntc_cells.py')}:raise ValueError('reader differs')
    if doc['NTC_cells_read']!=2944 or doc['arrays_shape']!=[2944,18533] or doc['contexts']!={plan['context_id']:2944}:
        raise ValueError('official cell counts differ')
    if doc['perturbed_RNA_rows_read'] or doc['cells_consumed_by_trainer']:raise ValueError('unexpected consumption')
    if doc['part_role']!='destination' or doc['denominator_policy']!=plan['denominator_policy']:raise ValueError('denominator/role differs')
    if doc['raw_sizes_measured']!={plan['source']['sha256']:plan['source']['bytes']}:raise ValueError('official source differs')
    if set(doc['files'])!={'counts.npz','cells.json','axes_depth_mask.npz'}:raise ValueError('official files differ')
    parts[ident]=dict(completion=pin(path),plan_sha256=plan['plan_sha256'],producer_code=doc['code'],
        part_role=doc['part_role'],denominator_policy=doc['denominator_policy'],contexts=doc['contexts'],
        files={name:{**spec,'remote_path':'ntc/'+ident+'/'+name} for name,spec in doc['files'].items()})
write_new(HERE/'official_ntc_verified_r1.json',dict(utc=now(),status='PASS_METADATA_AND_CODE',
    slug=job['slug'],remote_identity=identity,parts=parts,cells=8832,
    ntc_expected_parts=contract['ntc_expected_parts'],axis=contract['axis'],
    normalized_scale='log1p(counts * 10000 / native_depth)',
    full_provided_axis_limitation=True,runtime_consumer_must_verify_output_hashes=True,
    raw_RNA_downloaded=False,numeric_output_arrays_independently_rehashed=False))
print('PASS: official A/B/C, 8832 NTC, producer and all receipt pins')
