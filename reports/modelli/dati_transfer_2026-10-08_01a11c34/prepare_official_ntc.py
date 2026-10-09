"""Freeze anonymous destination controls, with native-source denominator policy."""
import csv
import hashlib
import json
from percorso import HERE,DATA,read,pin,sha,now,write_new
from prepare_neural_inputs_cloud import save_job

params=read(HERE/'quick_generation/r1/params.json')
base=read(read(HERE/'ntc_extraction_plans_r2.json')['plans'][0]['plan']['path'])
with (DATA/'raw/controls/gene_names.csv').open(newline='') as f:genes=[r[0] for r in list(csv.reader(f))[1:]]
plans=[]
for label in ('A','B','C'):
    name='context_'+label+'.h5ad'
    plan=dict(part_id='official_'+label,context_id=label,genes=genes,
        source=dict(file=name,bytes=params['controls']['bytes'][name],sha256=params['controls']['sha256'][name],cells=18400),
        seed=base['seed'],cells_per_stratum=64,
        identity=dict(study='VCC2026_official',context=label,donor_or_clone='MISSING',condition='MISSING',modality='MISSING',chemistry='MISSING'),
        part_role='destination',denominator_policy='full_provided_official_X_before_alignment',
        normalized_scale='log1p(counts * 10000 / native_depth)',
        unobserved_native_genes_limitation='No depth outside provided official feature axis is available; this does not replace training ingestion depth.')
    plan['plan_sha256']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    plans.append(plan)
contract=dict(utc=now(),plans=plans,source_dataset='davideferrante11/vcc-official-controls-r1',
    axis=pin(DATA/'raw/controls/gene_names.csv'),tests=pin(HERE/'official_ntc_tests_r1.txt'),
    schema_evidence=pin(HERE/'official_control_schema_r2.json'),metadata_evidence=pin(HERE/'official_control_metadata_r1.json'),
    ntc_expected_parts={p['part_id']:p['plan_sha256'] for p in plans},expected_cells_per_context=46*64,
    no_destination_cell_identity_deanonymization=True)
path=HERE/'official_ntc_contract_r1.json';write_new(path,contract)
members={n:(HERE/n).read_bytes() for n in ('official_ntc_worker.py','ntc_cells.py','run_ntc_extraction.py')}
members['official_contract.json']=json.dumps(contract).encode()
job=save_job('davideferrante11/dt-official-ntc-01a11c34-r1',members,'official_ntc_worker.py',
    [dict(kind='dataset',ref=contract['source_dataset'])],'official_r1')
prepared=HERE/'official_ntc_prepared_r1.json';write_new(prepared,dict(utc=now(),jobs=[job],contract=pin(path)))
auth=read(HERE/'production_anchors_authorization_r1.json')
auth.update(recorded_utc=now(),jobs=[job['slug']],prepared=pin(prepared),
    request_text='Lead production inputs and MODELLI explicit official A/B/C query controls contract',
    scope_note='Private CPU extraction of existing official NTC only; no generation, prediction submission or new acquisition')
write_new(HERE/'official_ntc_authorization_r1.json',auth)
print(json.dumps(dict(job=job['slug'],destination_contexts=3,expected_cells=8832)))
