"""Prepare read-only mount checks for known pilot inputs on the target account."""
from percorso import HERE,read,pin,write_new,now
refs={'kernel':{'davideferrante11/dt-ammi-anchors-01a11c34-r4','davideferrante11/dt-ntc-inputs-01a11c34-r5'},'dataset':set()}
for fold in ('C-K562','C-iPSC'):
    doc=read(HERE/('ammi_inner_truth_'+fold+'_r1.json'))
    for table in doc['tables'].values():refs[table['kind']].add(table['ref'])
metadata=HERE/'ammi_access_audit_metadata_r1.json'
write_new(metadata,dict(kernel_sources=sorted(refs['kernel']),dataset_sources=sorted(refs['dataset']),
    is_private=True,enable_gpu=False,enable_tpu=False,READ_ONLY_NOT_A_LAUNCH_PACKAGE=True))
write_new(HERE/'ammi_access_audit_prepared_r1.json',dict(utc=now(),jobs=[dict(
    slug='davidmaisterx/read-only-pilot-input-audit',metadata=pin(metadata))],
    scope='known NTC and pilot anchors / inner truth only; ESM/views await consumer manifest',
    launch_forbidden=True))
print('Prepared metadata-only access audit')
